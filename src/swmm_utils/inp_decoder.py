"""SWMM input file decoder - decode .inp files into Python dicts."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Union


# [AQUIFERS] columns after the name, in reference-manual order.
AQUIFER_FIELDS = (
    "por", "wp", "fc", "ks", "kslope", "tslope",
    "etu", "ets", "seep", "ebot", "egw", "umc",
)

# The words SWMM 5.2 reads as a row's own method at the end of an
# [INFILTRATION] row (infil.c, InfilModelWords).
INFILTRATION_METHODS = frozenset({
    "HORTON", "MODIFIED_HORTON", "GREEN_AMPT",
    "MODIFIED_GREEN_AMPT", "CURVE_NUMBER",
})

# SWMM 5.2's per-subcatchment [ADJUSTMENTS] rows: ``Type Subcatch Pattern``.
SUBCATCHMENT_ADJUSTMENTS = frozenset({"N-PERV", "DSTORE", "INFIL"})

# How many values each [STORAGE] shape takes after its keyword (node.c):
# a curve name, A1 A2 A0, or L W Z. The engine's keyword for the
# paraboloid is PARABOLIC (text.h defines w_PARABOLOID as "PARABOLIC");
# the 5.2 manual spells it PARABOLOID, so a row written from the manual is
# split the same way. The shape is written back as read.
STORAGE_SHAPE_PARAMS = {
    "TABULAR": 1, "FUNCTIONAL": 3, "CYLINDRICAL": 3,
    "CONICAL": 3, "PARABOLIC": 3, "PARABOLOID": 3, "PYRAMIDAL": 3,
}


def _keep_extra(entry: Dict[str, Any], parts: List[str], used: int) -> None:
    """Keep the tokens after a row's last known column under ``extra``.

    Engines add columns (OpenSWMM's rain and snow scale factors after a
    subcatchment's snow pack, for one); the encoder writes ``extra`` back
    after the known columns, so the row survives a round trip as read.
    """
    if len(parts) > used:
        entry["extra"] = parts[used:]


class SwmmInputDecoder:
    """Decode SWMM input (.inp) files into Python dict structures."""

    def __init__(self):
        """Initialize the decoder."""
        self.current_section = None
        self.line_number = 0

    def decode_file(self, filepath: str) -> Dict[str, Any]:
        """Decode a SWMM .inp file.

        Args:
            filepath: Path to the .inp file

        Returns:
            Dict containing the parsed SWMM model data
        """
        # Try UTF-8 first; fall back to Latin-1 (which accepts every byte)
        # Many SWMM .inp files from older software use Windows-1252/Latin-1
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return self.decode(f)
        except UnicodeDecodeError:
            with open(filepath, "r", encoding="latin-1") as f:
                return self.decode(f)

    def decode(self, file: TextIO) -> Dict[str, Any]:
        """Decode SWMM input from a file object.

        Args:
            file: File object to read from

        Returns:
            Dict containing the parsed SWMM model data
        """
        # Parse to dict
        model_dict = self._parse_to_dict(file)
        return model_dict

    def decode_json(self, json_input: Union[str, TextIO]) -> Dict[str, Any]:
        """Decode SWMM model from JSON format.

        Args:
            json_input: JSON file path, JSON string, or file object

        Returns:
            Dict containing the SWMM model data
        """
        if isinstance(json_input, str):
            # Check if it's a file path
            path = Path(json_input)
            if path.exists() and path.is_file():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            # Parse as JSON string
            return json.loads(json_input)
        # Assume file object
        return json.load(json_input)

    def decode_parquet(self, path: str) -> Dict[str, Any]:
        """Decode SWMM model from Parquet format.

        Args:
            path: Path to a parquet file (single-file mode) or directory containing
                 .parquet files (multi-file mode). Auto-detects which format.

        Returns:
            Dict containing the SWMM model data
        """
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise ImportError(
                "pyarrow is required for Parquet support. "
                "Install with: pip install pyarrow"
            ) from exc

        file_path = Path(path)

        # Check if it's a file or directory
        if file_path.is_file():
            # Single file mode: read file with section_name and section_data columns
            table = pq.read_table(str(file_path))
            data = table.to_pylist()

            model = {}
            for row in data:
                section_name = row["section_name"]
                section_data = row["section_data"]

                # Accumulate list sections
                if section_name not in model:
                    model[section_name] = []
                model[section_name].append(section_data)

            # Post-process: convert single-item lists with "value" key to strings
            for section_name, section_list in list(model.items()):
                if (
                    len(section_list) == 1
                    and isinstance(section_list[0], dict)
                    and list(section_list[0].keys()) == ["value"]
                ):
                    model[section_name] = section_list[0]["value"]

            return model

        if file_path.is_dir():
            # Multi-file mode: read each parquet file as a section
            model = {}

            for parquet_file in sorted(file_path.glob("*.parquet")):
                section_name = parquet_file.stem  # filename without extension

                table = pq.read_table(str(parquet_file))
                data = table.to_pylist()

                # Handle special case for string sections like "title"
                if len(data) == 1 and "value" in data[0]:
                    model[section_name] = data[0]["value"]
                else:
                    model[section_name] = data

            return model

        raise FileNotFoundError(f"Path not found: {path}")

    # Backwards compatibility aliases
    def parse_file(self, filepath: str) -> Dict[str, Any]:
        """Alias for decode_file (backwards compatibility)."""
        return self.decode_file(filepath)

    def parse(self, file: TextIO) -> Dict[str, Any]:
        """Alias for decode (backwards compatibility)."""
        return self.decode(file)

    def _parse_to_dict(self, file: TextIO) -> Dict:
        """Parse SWMM input file to dictionary format.

        Description capture:
          - Standalone ``;`` lines preceding a data row become that
            row's ``description`` field. Multiple consecutive ``;`` lines
            are joined with newlines.
          - Inline ``; comment`` after data on the same line is captured
            as the row's ``description`` if no preceding standalone
            ``;`` line exists.
          - ``;;`` (double-semicolon) column-header / divider lines are
            ignored — they're never per-row descriptions.
          - A blank line clears any pending description.
        """
        model: Dict[str, Any] = {}
        self.current_section = None
        self.line_number = 0
        section_data: List[str] = []
        section_desc: List[str] = []
        section_raw: List[str] = []
        pending_desc: List[str] = []

        for raw in file:
            self.line_number += 1
            stripped_full = raw.strip()

            # A section this decoder has no handler for keeps its lines as
            # written, comments included, so encoding writes it back whole.
            if not re.match(r"^\[[A-Za-z0-9_]+\]$", stripped_full):
                section_raw.append(raw.rstrip("\r\n"))

            # Blank line → clears pending description (so a description
            # block doesn't bleed across element rows separated by spacing).
            if not stripped_full:
                pending_desc = []
                continue

            # Column-header / divider lines (`;;`).
            if stripped_full.startswith(";;"):
                continue

            # Standalone description line (`;<text>`).
            if stripped_full.startswith(";"):
                pending_desc.append(stripped_full[1:].strip())
                continue

            # Section header. Real .inp files in the wild mix case
            # ([POLYGONS] vs [Polygons] vs [polygons]) — the SWMM engine
            # accepts any, so we do too. Normalize to UPPERCASE so the
            # dispatch table stays simple. Names may start with a digit
            # (OpenSWMM's [2D_OPTIONS], [2D_VERTICES], ...).
            section_match = re.match(r"^\[([A-Za-z0-9_]+)\]$", stripped_full)
            if section_match:
                if self.current_section:
                    self._close_section(
                        model, section_data, section_desc, section_raw
                    )
                self.current_section = section_match.group(1).upper()
                section_data = []
                section_desc = []
                section_raw = []
                pending_desc = []
                continue

            # Data row (possibly with a trailing `; comment`).
            data_part, inline_desc = self._split_inline_comment(stripped_full)
            if not data_part:
                # Whole row was just an inline-comment after stripped text —
                # treat as a description for the next data row.
                if inline_desc:
                    pending_desc.append(inline_desc)
                continue

            # Preceding `;` lines win over inline comments. Most authors
            # use one or the other; if both are present the standalone
            # text is usually the more deliberate description.
            desc = "\n".join(pending_desc) if pending_desc else inline_desc
            pending_desc = []

            if self.current_section:
                section_data.append(data_part)
                section_desc.append(desc)

        if self.current_section:
            self._close_section(model, section_data, section_desc, section_raw)

        return model

    def _close_section(
        self,
        model: dict,
        data: List[str],
        descriptions: List[str],
        raw_lines: List[str],
    ):
        """Hand a finished section to its handler, or keep it verbatim.

        A section with no handler (OpenSWMM's ``[2D_*]``, ``[PLUGINS]``,
        ``[USER_FLAGS]``, ...) is stored under ``unknown_sections`` as
        ``{name: [line, ...]}``, its lines as written with the blank lines
        at either end trimmed; the encoder writes it back unchanged.
        """
        section = self.current_section
        if getattr(self, f"_parse_{section.lower()}", None) is None:
            while raw_lines and not raw_lines[-1].strip():
                raw_lines.pop()
            while raw_lines and not raw_lines[0].strip():
                raw_lines.pop(0)
            if raw_lines:
                unknown = model.setdefault("unknown_sections", {})
                unknown.setdefault(section, []).extend(raw_lines)
            return
        if data:
            self._process_section(model, section, data, descriptions)

    def _preprocess_line(self, line: str) -> str:
        """Preprocess a line by removing comments and whitespace.

        Kept for backward compatibility with any external callers; the
        main parse path now calls ``_split_inline_comment`` so that
        descriptions can be captured rather than discarded.
        """
        if ";" in line:
            line = line[: line.index(";")]
        return line.strip()

    @staticmethod
    def _split_inline_comment(line: str) -> "tuple[str, str]":
        """Split a single line into (data, inline_comment).

        The first ``;`` separates the engine-relevant data from a
        description — neither side is processed further here, just
        stripped of surrounding whitespace.
        """
        if ";" not in line:
            return line.strip(), ""
        idx = line.index(";")
        return line[:idx].strip(), line[idx + 1:].strip()

    def _process_section(
        self,
        model: dict,
        section: str,
        data: List[str],
        descriptions: Optional[List[str]] = None,
    ):
        """Process a section and add to model.

        After the section handler runs, if it emitted a ``list[dict]`` of
        the same length as ``descriptions`` and any description is
        non-empty, attach it to the corresponding row's ``description``
        field. Sections that emit dicts (options, times, report) drop
        descriptions silently — they don't have per-row semantics.
        """
        handler_name = f"_parse_{section.lower()}"
        handler = getattr(self, handler_name, None)

        if handler is None:
            print(f"Warning: No handler for section [{section}]")
            return

        keys_before = set(model.keys())
        handler(model, data)  # type: ignore  # pylint: disable=not-callable

        if not descriptions or not any(descriptions):
            return

        # Find the key(s) the handler wrote. Most write a single new key
        # under the section name (or its plural, e.g. infiltration ->
        # infiltrations). Track set diff so we don't depend on the
        # naming convention.
        new_keys = set(model.keys()) - keys_before
        if not new_keys and section.lower() in model:
            new_keys = {section.lower()}
        for key in new_keys:
            value = model[key]
            if isinstance(value, list) and len(value) == len(descriptions):
                for i, row in enumerate(value):
                    if isinstance(row, dict) and descriptions[i]:
                        row["description"] = descriptions[i]

    # Section-specific parsers

    def _parse_title(self, model: dict, data: List[str]):
        """Parse [TITLE] section."""
        model["title"] = "\n".join(data)

    def _parse_options(self, model: dict, data: List[str]):
        """Parse [OPTIONS] section."""
        options = {}
        for line in data:
            parts = line.split(None, 1)
            if parts:
                # Every key is kept, the engine's or not (OpenSWMM's
                # NODE_CONTINUITY, FV_*, CRS, ...), in the order written.
                options[parts[0]] = parts[1] if len(parts) == 2 else ""
        model["options"] = options

    def _parse_evaporation(self, model: dict, data: List[str]):
        """Parse [EVAPORATION] section.

        SWMM allows multiple line types in one [EVAPORATION] block — e.g.
        ``CONSTANT 0.0`` followed by ``DRY_ONLY NO`` and an optional
        ``RECOVERY some_pat``. Each first token is unique, so we store
        them as a dict keyed by the lowercased first token; the
        remainder of the line is space-joined as the value (numeric
        coercion happens at the editor / encoder boundary). For
        ``MONTHLY`` and ``FILE`` the value is the 12 monthly figures
        space-separated.
        """
        evaporation: Dict[str, Any] = {}
        for line in data:
            parts = line.split()
            if not parts:
                continue
            key = parts[0].lower()
            value = " ".join(parts[1:]) if len(parts) > 1 else ""
            evaporation[key] = value
        model["evaporation"] = evaporation

    def _parse_temperature(self, model: dict, data: List[str]):
        """Parse [TEMPERATURE] section.

        Multi-line block whose first token names the parameter:
          TIMESERIES name
          FILE filename startdate
          WINDSPEED MONTHLY v1 ... v12   |   WINDSPEED FILE
          SNOWMELT divtemp ATIwt rnmratio elev lat dtgmt
          ADC IMPERVIOUS f1 f2 ... f10
          ADC PERVIOUS   f1 f2 ... f10

        ADC has two flavors that share a key — split them into
        ``adc_impervious`` / ``adc_pervious`` so both round-trip
        instead of one clobbering the other.
        """
        temperature: Dict[str, Any] = {}
        for line in data:
            parts = line.split()
            if not parts:
                continue
            head = parts[0].upper()
            rest = parts[1:]
            if head == "ADC" and rest:
                flavor = rest[0].upper()
                values = " ".join(rest[1:])
                if flavor == "IMPERVIOUS":
                    temperature["adc_impervious"] = values
                elif flavor == "PERVIOUS":
                    temperature["adc_pervious"] = values
                else:
                    # Unknown ADC flavor — preserve as a generic key so
                    # the data round-trips even if we don't understand it.
                    temperature[f"adc_{flavor.lower()}"] = values
            else:
                temperature[head.lower()] = " ".join(rest)
        model["temperature"] = temperature

    def _parse_adjustments(self, model: dict, data: List[str]):
        """Parse [ADJUSTMENTS] section.

        TEMPERATURE / EVAPORATION / RAINFALL / CONDUCTIVITY rows hold 12
        monthly values, stored keyed by the lowercased word with the
        values space-joined. SWMM 5.2's ``N-PERV``, ``DSTORE`` and
        ``INFIL`` rows name a subcatchment and a pattern, and a model has
        one per subcatchment, so they go in order under
        ``subcatchment_patterns`` as ``{type, subcatchment, pattern}``.
        Keyed by their word, all but the last of each were lost.
        """
        adjustments: Dict[str, Any] = {}
        patterns: List[Dict[str, Any]] = []
        for line in data:
            parts = line.split()
            if not parts:
                continue
            if parts[0].upper() in SUBCATCHMENT_ADJUSTMENTS and len(parts) >= 3:
                row = {
                    "type": parts[0].upper(),
                    "subcatchment": parts[1],
                    "pattern": parts[2],
                }
                _keep_extra(row, parts, 3)
                patterns.append(row)
                continue
            adjustments[parts[0].lower()] = " ".join(parts[1:])
        if patterns:
            adjustments["subcatchment_patterns"] = patterns
        model["adjustments"] = adjustments

    def _parse_gwf(self, model: dict, data: List[str]):
        """Parse [GWF] section (custom groundwater flow equations).

        Row: ``Subcatchment  LATERAL|DEEP  <expression>``. The expression
        is free text with spaces, so everything after the flow type is
        kept verbatim.
        """
        gwf = []
        for line in data:
            parts = line.split(None, 2)
            if len(parts) >= 3:
                gwf.append({"subcatchment": parts[0], "type": parts[1].upper(), "expression": parts[2].strip()})
        model["gwf"] = gwf

    def _parse_loadings(self, model: dict, data: List[str]):
        """Parse [LOADINGS] section (initial pollutant buildup).

        Row: ``Subcatchment  Pollutant  InitBuildup [Pollutant InitBuildup ...]``;
        one entry is stored per (subcatchment, pollutant) pair.
        """
        loadings = []
        for line in data:
            parts = line.split()
            for i in range(1, len(parts) - 1, 2):
                loadings.append({"subcatchment": parts[0], "pollutant": parts[i], "buildup": parts[i + 1]})
        model["loadings"] = loadings

    def _parse_events(self, model: dict, data: List[str]):
        """Parse [EVENTS] section (SWMM 5.2).

        Each row is a period the engine restricts routing to:
          Start_Date  Start_Time  End_Date  End_Time
        Stored as ``{"start": "MM/DD/YYYY HH:MM", "end": ...}`` per row.
        A file whose events are dropped silently routes the whole
        simulation period instead, so the section has to survive.
        """
        events = []
        for line in data:
            parts = line.split()
            if len(parts) >= 4:
                events.append({"start": f"{parts[0]} {parts[1]}", "end": f"{parts[2]} {parts[3]}"})
        model["events"] = events

    def _parse_aquifers(self, model: dict, data: List[str]):
        """Parse [AQUIFERS] section.

        SWMM 5.1+ row, twelve numbers after the name and an optional
        evaporation pattern:

          Name  Por  WP  FC  Ks  Kslp  Tslp  ETu  ETs  Seep  Ebot  Egw  Umc  [Epat]

        Stored under the reference-manual names (``AQUIFER_FIELDS``). An
        earlier version of this handler stopped at ten numbers and
        mislabelled the tail, so a re-encoded file lost ``Umc`` and the
        engine refused it with "too few items".
        """
        aquifers = []
        for line in data:
            parts = line.split()
            if len(parts) < 2:
                continue
            aq: Dict[str, Any] = {"name": parts[0]}
            for key, value in zip(AQUIFER_FIELDS, parts[1:]):
                aq[key] = value
            if len(parts) > 1 + len(AQUIFER_FIELDS):
                aq["epat"] = parts[1 + len(AQUIFER_FIELDS)]
            aquifers.append(aq)
        model["aquifers"] = aquifers

    def _parse_snowpacks(self, model: dict, data: List[str]):
        """Parse [SNOWPACKS] section.

        Multi-row per pack. Column 2 selects the row flavor:
          name PLOWABLE   Cmin Cmax Tbase FWF SD0 FW0 SNN0
          name IMPERVIOUS Cmin Cmax Tbase FWF SD0 FW0 SNN0
          name PERVIOUS   Cmin Cmax Tbase FWF SD0 FW0 SNN0
          name REMOVAL    SDplow Fout Fimperv Fperv Fimm Fsubcatch [subcatch]

        Stored as ``dict[name -> dict[flavor_lowered -> param_list]]``
        so all four rows for one pack stay grouped.
        """
        snowpacks: Dict[str, Dict[str, List[str]]] = {}
        for line in data:
            parts = line.split()
            if len(parts) < 3:
                continue
            name = parts[0]
            flavor = parts[1].lower()
            values = parts[2:]
            snowpacks.setdefault(name, {})[flavor] = values
        model["snowpacks"] = snowpacks

    def _parse_raingages(self, model: dict, data: List[str]):
        """Parse [RAINGAGES] section.

        The trailing portion of the row depends on the source:

          ... TIMESERIES <series> [SCF]
          ... FILE <"filename"> <station> <units> [Start] [SCF]

        ``file_or_station`` keeps everything after the source as written,
        and the encoder writes it back, so a row round-trips whatever its
        columns. The parts are also surfaced on their own: ``data_param``
        (the series or file name, quotes stripped), ``station``, ``units``,
        ``start`` (the date the file's data is read from; ``*`` means from
        the start of the file) and ``scale_factor`` (a multiplier on the
        gage's rainfall).

        EPA SWMM 5.2.4 reads ``start`` but not ``scale_factor``; OpenSWMM 6
        (and the 5.3 engine it bundles) applies both.
        """
        raingages = []
        for line in data:
            # A quoted file name may contain spaces.
            parts = re.findall(r'"[^"]*"|\S+', line)
            if len(parts) < 6:
                continue
            gage = {
                "name": parts[0],
                "format": parts[1],
                "interval": parts[2],
                "scf": parts[3],
                "source": parts[4],
                "file_or_station": " ".join(parts[5:]),
            }
            source_upper = parts[4].upper()
            if source_upper == "FILE" and len(parts) >= 8:
                gage["data_param"] = parts[5].strip('"')
                gage["station"] = parts[6]
                gage["units"] = parts[7]
                if len(parts) > 8:
                    gage["start"] = parts[8]
                if len(parts) > 9:
                    gage["scale_factor"] = parts[9]
            elif source_upper == "TIMESERIES":
                gage["data_param"] = parts[5]
                if len(parts) > 6:
                    gage["scale_factor"] = parts[6]
            raingages.append(gage)
        model["raingages"] = raingages

    def _parse_subcatchments(self, model: dict, data: List[str]):
        """Parse [SUBCATCHMENTS] section."""
        subcatchments = []
        for line in data:
            parts = line.split()
            if len(parts) >= 8:
                sub = {
                    "name": parts[0],
                    "raingage": parts[1],
                    "outlet": parts[2],
                    "area": parts[3],
                    "imperv": parts[4],
                    "width": parts[5],
                    "slope": parts[6],
                    "curb_length": parts[7],
                }
                if len(parts) > 8:
                    sub["snowpack"] = parts[8]
                _keep_extra(sub, parts, 9)
                subcatchments.append(sub)
        model["subcatchments"] = subcatchments

    def _parse_subareas(self, model: dict, data: List[str]):
        """Parse [SUBAREAS] section."""
        subareas = []
        for line in data:
            parts = line.split()
            if len(parts) >= 7:
                subarea = {
                    "subcatchment": parts[0],
                    "n_imperv": parts[1],
                    "n_perv": parts[2],
                    "s_imperv": parts[3],
                    "s_perv": parts[4],
                    "pct_zero": parts[5],
                    "route_to": parts[6],
                }
                if len(parts) > 7:
                    subarea["pct_routed"] = parts[7]
                _keep_extra(subarea, parts, 8)
                subareas.append(subarea)
        model["subareas"] = subareas

    def _parse_infiltration(self, model: dict, data: List[str]):
        """Parse [INFILTRATION] section.

        SWMM 5.2 row: ``Subcatch P1 P2 P3 [P4 P5] [Method]``. A method word
        as the last column (after at least three parameters, as infil.c
        reads it) is the row's own method, kept as ``method``; without
        one the row uses [OPTIONS] INFILTRATION.
        """
        infiltrations = []
        for line in data:
            parts = line.split()
            if len(parts) >= 4:
                method = None
                if len(parts) >= 5 and parts[-1].upper() in INFILTRATION_METHODS:
                    method = parts[-1]
                    parts = parts[:-1]
                infil = {
                    "subcatchment": parts[0],
                    "param1": parts[1],
                    "param2": parts[2],
                    "param3": parts[3],
                }
                if len(parts) > 4:
                    infil["param4"] = parts[4]
                if len(parts) > 5:
                    infil["param5"] = parts[5]
                _keep_extra(infil, parts, 6)
                if method is not None:
                    infil["method"] = method
                infiltrations.append(infil)
        model["infiltrations"] = infiltrations

    def _parse_junctions(self, model: dict, data: List[str]):
        """Parse [JUNCTIONS] section."""
        junctions = []
        for line in data:
            parts = line.split()
            if len(parts) >= 3:
                junction = {
                    "name": parts[0],
                    "elevation": parts[1],
                    "max_depth": parts[2],
                }
                if len(parts) > 3:
                    junction["init_depth"] = parts[3]
                if len(parts) > 4:
                    junction["surcharge_depth"] = parts[4]
                if len(parts) > 5:
                    junction["ponded_area"] = parts[5]
                _keep_extra(junction, parts, 6)
                junctions.append(junction)
        model["junctions"] = junctions

    def _parse_outfalls(self, model: dict, data: List[str]):
        """Parse [OUTFALLS] section.

        SWMM 5.2 column layout is type-dependent. The ``Stage Data``
        column only exists for FIXED / TIDAL / TIMESERIES boundary
        types — for FREE and NORMAL it is omitted entirely, so
        whitespace-tokenizing the row would otherwise mis-shift
        ``gated`` and ``route_to`` one column to the left.

        Layouts:
          FREE | NORMAL              : name elev type           gated route_to
          FIXED | TIDAL | TIMESERIES : name elev type stage_data gated route_to
        """
        outfalls = []
        types_with_stage = {"FIXED", "TIDAL", "TIMESERIES"}
        for line in data:
            parts = line.split()
            if len(parts) < 3:
                continue
            outfall_type = parts[2].upper()
            outfall = {"name": parts[0], "elevation": parts[1], "type": parts[2]}
            if outfall_type in types_with_stage:
                if len(parts) > 3:
                    outfall["stage_data"] = parts[3]
                if len(parts) > 4:
                    outfall["gated"] = parts[4]
                if len(parts) > 5:
                    outfall["route_to"] = parts[5]
                _keep_extra(outfall, parts, 6)
            else:
                # FREE / NORMAL / unknown — no stage_data column.
                if len(parts) > 3:
                    outfall["gated"] = parts[3]
                if len(parts) > 4:
                    outfall["route_to"] = parts[4]
                _keep_extra(outfall, parts, 5)
            outfalls.append(outfall)
        model["outfalls"] = outfalls

    def _parse_storage(self, model: dict, data: List[str]):
        """Parse [STORAGE] section.

        SWMM 5.2 row: ``Name Elev MaxDepth InitDepth Shape {Curve | A1 A2
        A0 | L W Z} [SurDepth [Fevap [Psi Ksat IMD | Ksat]]]``.
        ``curve_params`` holds the shape's own values; the columns after
        them are ``surcharge_depth``, ``evap_factor`` and the seepage
        loss ``seepage_suction``, ``seepage_ksat``, ``seepage_imd`` (a
        single value there is Ksat alone, as exfil.c reads it). SWMM 5.1
        has the ponded area where 5.2 has SurDepth; 5.2 reads that column
        as the surcharge depth, so it is kept under that name. A shape
        the decoder doesn't know keeps every column in ``curve_params``.
        """
        storage_nodes = []
        for line in data:
            parts = line.split()
            if len(parts) >= 6:
                storage = {
                    "name": parts[0],
                    "elevation": parts[1],
                    "max_depth": parts[2],
                    "init_depth": parts[3],
                    "curve_type": parts[4],
                }
                count = STORAGE_SHAPE_PARAMS.get(parts[4].upper())
                if count is None:
                    storage["curve_params"] = parts[5:]
                    storage_nodes.append(storage)
                    continue
                end = 5 + count
                storage["curve_params"] = parts[5:end]
                rest = parts[end:]
                if rest:
                    storage["surcharge_depth"] = rest.pop(0)
                if rest:
                    storage["evap_factor"] = rest.pop(0)
                if len(rest) == 1:
                    storage["seepage_ksat"] = rest.pop(0)
                elif len(rest) >= 3:
                    storage["seepage_suction"] = rest.pop(0)
                    storage["seepage_ksat"] = rest.pop(0)
                    storage["seepage_imd"] = rest.pop(0)
                if rest:
                    storage["extra"] = rest
                storage_nodes.append(storage)
        model["storage"] = storage_nodes

    def _parse_dividers(self, model: dict, data: List[str]):
        """Parse [DIVIDERS] section.

        SWMM 5.2 row:
          ``name elevation diverted_link type [args] max_depth init_depth surcharge_depth ponded_area``

        ``type`` is one of CUTOFF / OVERFLOW / TABULAR / WEIR. Each
        type has different number of `args`:
          CUTOFF   <Q_min>
          OVERFLOW                  (no args)
          TABULAR  <curve_name>
          WEIR     <Q_min> <h_max> <coefficient>

        We only normalize the canonical fields (name / elevation /
        diverted_link / type) and pass the type-specific args through
        in a generic ``params`` list. Trailing depth / aponded columns
        live AFTER the args, so we anchor them by counting from the
        right rather than positional indexing.
        """
        dividers = []
        for line in data:
            parts = line.split()
            if len(parts) < 4:
                continue
            entry: Dict[str, Any] = {
                "name": parts[0],
                "elevation": parts[1],
                "diverted_link": parts[2],
                "type": parts[3].upper(),
            }
            # Per-type arg count (per SWMM 5.2 [DIVIDERS] spec):
            arg_counts = {"CUTOFF": 1, "OVERFLOW": 0, "TABULAR": 1, "WEIR": 3}
            n_args = arg_counts.get(entry["type"], 0)
            args_end = 4 + n_args
            entry["params"] = parts[4:args_end]
            tail = parts[args_end:]
            # Trailing common-node columns (max_depth / init_depth /
            # surcharge_depth / ponded_area). All optional; pad rather
            # than guess so unknown columns aren't misnamed.
            tail_keys = ("max_depth", "init_depth", "surcharge_depth", "ponded_area")
            for i, key in enumerate(tail_keys):
                if i < len(tail):
                    entry[key] = tail[i]
            _keep_extra(entry, parts, args_end + len(tail_keys))
            dividers.append(entry)
        model["dividers"] = dividers

    def _parse_conduits(self, model: dict, data: List[str]):
        """Parse [CONDUITS] section."""
        conduits = []
        for line in data:
            parts = line.split()
            if len(parts) >= 6:
                conduit = {
                    "name": parts[0],
                    "from_node": parts[1],
                    "to_node": parts[2],
                    "length": parts[3],
                    "roughness": parts[4],
                    "in_offset": parts[5],
                }
                if len(parts) > 6:
                    conduit["out_offset"] = parts[6]
                if len(parts) > 7:
                    conduit["init_flow"] = parts[7]
                if len(parts) > 8:
                    conduit["max_flow"] = parts[8]
                _keep_extra(conduit, parts, 9)
                conduits.append(conduit)
        model["conduits"] = conduits

    def _parse_pumps(self, model: dict, data: List[str]):
        """Parse [PUMPS] section."""
        pumps = []
        for line in data:
            parts = line.split()
            if len(parts) >= 4:
                pump = {
                    "name": parts[0],
                    "from_node": parts[1],
                    "to_node": parts[2],
                    "curve": parts[3],
                }
                if len(parts) > 4:
                    pump["status"] = parts[4]
                if len(parts) > 5:
                    pump["startup"] = parts[5]
                if len(parts) > 6:
                    pump["shutoff"] = parts[6]
                _keep_extra(pump, parts, 7)
                pumps.append(pump)
        model["pumps"] = pumps

    def _parse_orifices(self, model: dict, data: List[str]):
        """Parse [ORIFICES] section."""
        orifices = []
        for line in data:
            parts = line.split()
            if len(parts) >= 6:
                orifice = {
                    "name": parts[0],
                    "from_node": parts[1],
                    "to_node": parts[2],
                    "type": parts[3],
                    "offset": parts[4],
                    "discharge_coeff": parts[5],
                }
                if len(parts) > 6:
                    orifice["gated"] = parts[6]
                if len(parts) > 7:
                    orifice["close_time"] = parts[7]
                _keep_extra(orifice, parts, 8)
                orifices.append(orifice)
        model["orifices"] = orifices

    def _parse_weirs(self, model: dict, data: List[str]):
        """Parse [WEIRS] section."""
        weirs = []
        for line in data:
            parts = line.split()
            if len(parts) >= 6:
                weir = {
                    "name": parts[0],
                    "from_node": parts[1],
                    "to_node": parts[2],
                    "type": parts[3],
                    "crest_height": parts[4],
                    "discharge_coeff": parts[5],
                }
                if len(parts) > 6:
                    weir["gated"] = parts[6]
                if len(parts) > 7:
                    weir["end_con"] = parts[7]
                if len(parts) > 8:
                    weir["end_coeff"] = parts[8]
                if len(parts) > 9:
                    weir["surcharge"] = parts[9]
                if len(parts) > 10:
                    weir["road_width"] = parts[10]
                if len(parts) > 11:
                    weir["road_surf"] = parts[11]
                if len(parts) > 12:
                    weir["coeff_curve"] = parts[12]
                _keep_extra(weir, parts, 13)
                weirs.append(weir)
        model["weirs"] = weirs

    def _parse_xsections(self, model: dict, data: List[str]):
        """Parse [XSECTIONS] section."""
        xsections = []
        for line in data:
            parts = line.split()
            if len(parts) >= 3:
                xsection = {"link": parts[0], "shape": parts[1], "geom1": parts[2]}
                if len(parts) > 3:
                    xsection["geom2"] = parts[3]
                if len(parts) > 4:
                    xsection["geom3"] = parts[4]
                if len(parts) > 5:
                    xsection["geom4"] = parts[5]
                if len(parts) > 6:
                    xsection["barrels"] = parts[6]
                if len(parts) > 7:
                    xsection["culvert"] = parts[7]
                _keep_extra(xsection, parts, 8)
                xsections.append(xsection)
        model["xsections"] = xsections

    def _parse_losses(self, model: dict, data: List[str]):
        """Parse [LOSSES] section."""
        losses = []
        for line in data:
            parts = line.split()
            if len(parts) >= 4:
                loss = {
                    "link": parts[0],
                    "inlet": parts[1],
                    "outlet": parts[2],
                    "average": parts[3],
                }
                if len(parts) > 4:
                    loss["flap_gate"] = parts[4]
                if len(parts) > 5:
                    loss["seepage"] = parts[5]
                _keep_extra(loss, parts, 6)
                losses.append(loss)
        model["losses"] = losses

    def _parse_controls(self, model: dict, data: List[str]):
        """Parse [CONTROLS] section."""
        # Controls are complex rule-based logic
        model["controls"] = "\n".join(data)

    def _parse_timeseries(self, model: dict, data: List[str]):
        """Parse [TIMESERIES] section.

        Format: Name Date Time Value
        Example: TIMESERI-3  08/03/2006 18:05  0.500000
        """
        timeseries = {}

        for line in data:
            parts = line.split()
            if len(parts) >= 3:
                # Format: Name Date Time Value
                # If 4 parts: Name Date Time Value
                # If 3 parts: Name Time Value (no date)
                # If 2 parts: Name Value (continuation or simple format)

                name = parts[0]
                if name not in timeseries:
                    timeseries[name] = []

                if len(parts) >= 4:
                    # Standard format: Name Date Time Value
                    timeseries[name].append(
                        {"date": parts[1], "time": parts[2], "value": parts[3]}
                    )
                elif len(parts) == 3:
                    # Name Time Value (no date)
                    timeseries[name].append(
                        {"date": "", "time": parts[1], "value": parts[2]}
                    )
                elif len(parts) == 2:
                    # Name Value (simple format)
                    timeseries[name].append({"date": "", "time": "", "value": parts[1]})

        model["timeseries"] = timeseries

    def _parse_patterns(self, model: dict, data: List[str]):
        """Parse [PATTERNS] section."""
        patterns = {}

        for line in data:
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                if name not in patterns:
                    patterns[name] = []
                patterns[name].extend(parts[1:])

        model["patterns"] = patterns

    def _parse_curves(self, model: dict, data: List[str]):
        """Parse [CURVES] section.

        SWMM 5.2 row layouts:
          First row of a curve  : ``Name Type X Y [X Y ...]``
          Continuation rows     : ``Name X Y [X Y ...]``

        The type keyword only appears on the first row of each curve.
        We detect "is this the first row?" by looking up parts[1]
        against the set of known curve-type keywords (case-insensitive).
        Anything else is treated as a continuation row.
        """
        curves: Dict[str, Any] = {}
        # Curve types defined by SWMM 5.2 spec. Anything else in
        # parts[1] means we're on a continuation row, so parts[1] is
        # an x-value not a type.
        type_keywords = {
            "STORAGE", "TIDAL", "RATING", "SHAPE", "CONTROL",
            "DIVERSION", "WEIR",
            "PUMP1", "PUMP2", "PUMP3", "PUMP4", "PUMP5",
        }

        for line in data:
            parts = line.split()
            if len(parts) < 3:
                continue
            name = parts[0]
            data_start = 1
            if parts[1].upper() in type_keywords:
                # First row of this curve — capture the type and
                # start point pairs at parts[2].
                if name not in curves:
                    curves[name] = {"type": parts[1], "points": []}
                else:
                    # Curve already started but a duplicate first-row
                    # is suspicious; tolerate by overwriting type.
                    curves[name]["type"] = parts[1]
                data_start = 2
            else:
                # Continuation row — type was set on a prior line.
                if name not in curves:
                    # No prior first-row seen → unknown type, leave
                    # blank so the encoder falls through to its
                    # default. Better than mis-reading parts[1] as a
                    # type keyword.
                    curves[name] = {"type": "", "points": []}
                data_start = 1

            for i in range(data_start, len(parts), 2):
                if i + 1 < len(parts):
                    curves[name]["points"].append(
                        {"x": parts[i], "y": parts[i + 1]}
                    )

        model["curves"] = curves

    def _parse_curve(self, model: dict, data: List[str]):
        """Parse [CURVE] section (alternate name for CURVES)."""
        self._parse_curves(model, data)

    def _parse_coordinates(self, model: dict, data: List[str]):
        """Parse [COORDINATES] section."""
        coordinates = []
        for line in data:
            parts = line.split()
            if len(parts) >= 3:
                coord = {"node": parts[0], "x": parts[1], "y": parts[2]}
                coordinates.append(coord)
        model["coordinates"] = coordinates

    def _parse_vertices(self, model: dict, data: List[str]):
        """Parse [VERTICES] section."""
        vertices = []
        for line in data:
            parts = line.split()
            if len(parts) >= 3:
                vertex = {"link": parts[0], "x": parts[1], "y": parts[2]}
                vertices.append(vertex)
        model["vertices"] = vertices

    def _parse_polygons(self, model: dict, data: List[str]):
        """Parse [POLYGONS] section."""
        polygons = []
        for line in data:
            parts = line.split()
            if len(parts) >= 3:
                polygon = {"subcatchment": parts[0], "x": parts[1], "y": parts[2]}
                polygons.append(polygon)
        model["polygons"] = polygons

    def _parse_symbols(self, model: dict, data: List[str]):
        """Parse [SYMBOLS] section."""
        symbols = []
        for line in data:
            parts = line.split()
            if len(parts) >= 3:
                symbol = {"gage": parts[0], "x": parts[1], "y": parts[2]}
                symbols.append(symbol)
        model["symbols"] = symbols

    def _parse_labels(self, model: dict, data: List[str]):
        """Parse [LABELS] section."""
        labels = []
        for line in data:
            parts = line.split(None, 3)
            if len(parts) >= 3:
                label = {"x": parts[0], "y": parts[1], "text": parts[2]}
                if len(parts) > 3:
                    label["anchor"] = parts[3]
                labels.append(label)
        model["labels"] = labels

    def _parse_tags(self, model: dict, data: List[str]):
        """Parse [TAGS] section."""
        tags = []
        for line in data:
            parts = line.split(None, 2)
            if len(parts) >= 3:
                tag = {"type": parts[0], "name": parts[1], "tag": parts[2]}
                tags.append(tag)
        model["tags"] = tags

    def _parse_outlets(self, model: dict, data: List[str]):
        """Parse [OUTLETS] section."""
        outlets = []
        for line in data:
            parts = line.split()
            if len(parts) >= 5:
                outlet = {
                    "name": parts[0],
                    "from_node": parts[1],
                    "to_node": parts[2],
                    "offset": parts[3],
                    "type": parts[4],
                }
                # FUNCTIONAL/* rows carry a coefficient and an exponent
                # before the gate flag; TABULAR/* rows carry a curve name.
                # Reading both shapes as "curve, gated" put the exponent in
                # the gate column and lost the flag itself.
                if parts[4].upper().startswith("FUNCTIONAL"):
                    if len(parts) > 5:
                        outlet["qcoeff"] = parts[5]
                    if len(parts) > 6:
                        outlet["qexpon"] = parts[6]
                    if len(parts) > 7:
                        outlet["gated"] = parts[7]
                    _keep_extra(outlet, parts, 8)
                else:
                    if len(parts) > 5:
                        outlet["curve_name"] = parts[5]
                    if len(parts) > 6:
                        outlet["gated"] = parts[6]
                    _keep_extra(outlet, parts, 7)
                outlets.append(outlet)
        model["outlets"] = outlets

    def _parse_transects(self, model: dict, data: List[str]):
        """Parse [TRANSECTS] section."""
        # Transects are complex multi-line structures
        model["transects"] = "\n".join(data)

    def _parse_report(self, model: dict, data: List[str]):
        """Parse [REPORT] section."""
        report = {}
        for line in data:
            parts = line.split(None, 1)
            if len(parts) == 2:
                key, value = parts
                report[key] = value
        model["report"] = report

    def _parse_map(self, model: dict, data: List[str]):
        """Parse [MAP] section."""
        map_data = {}
        for line in data:
            parts = line.split(None, 1)
            if len(parts) == 2:
                key, value = parts
                map_data[key] = value
        model["map"] = map_data

    def _parse_backdrop(self, model: dict, data: List[str]):
        """Parse [BACKDROP] section."""
        backdrop = {}
        for line in data:
            parts = line.split(None, 1)
            if len(parts) == 2:
                key, value = parts
                backdrop[key] = value
        model["backdrop"] = backdrop

    def _parse_profiles(self, model: dict, data: List[str]):
        """Parse [PROFILES] section."""
        profiles = []
        for line in data:
            parts = line.split()
            if len(parts) >= 2:
                profile = {"name": parts[0], "links": parts[1:]}
                profiles.append(profile)
        model["profiles"] = profiles

    def _parse_inflows(self, model: dict, data: List[str]):
        """Parse [INFLOWS] section."""
        inflows = []
        for line in data:
            parts = line.split()
            # Node, constituent and time series make a complete row; the
            # engine defaults everything after. A row of three (the common
            # "node FLOW series") used to be dropped.
            if len(parts) >= 3:
                inflow = {
                    "node": parts[0],
                    "constituent": parts[1],
                    "timeseries": parts[2],
                }
                if len(parts) > 3:
                    inflow["type"] = parts[3]
                if len(parts) > 4:
                    inflow["mfactor"] = parts[4]
                if len(parts) > 5:
                    inflow["sfactor"] = parts[5]
                if len(parts) > 6:
                    inflow["baseline"] = parts[6]
                if len(parts) > 7:
                    inflow["pattern"] = parts[7]
                _keep_extra(inflow, parts, 8)
                inflows.append(inflow)
        model["inflows"] = inflows

    def _parse_dwf(self, model: dict, data: List[str]):
        """Parse [DWF] section."""
        dwf = []
        for line in data:
            parts = line.split()
            if len(parts) >= 3:
                entry: Dict[str, Any] = {
                    "node": parts[0],
                    "constituent": parts[1],
                    "baseline": parts[2],
                }
                if len(parts) > 3:
                    entry["patterns"] = parts[3:]
                dwf.append(entry)
        model["dwf"] = dwf

    def _parse_pollutants(self, model: dict, data: List[str]):
        """Parse [POLLUTANTS] section."""
        pollutants = []
        for line in data:
            parts = line.split()
            if len(parts) >= 1:
                pollutant = {"name": parts[0]}
                if len(parts) > 1:
                    pollutant["units"] = parts[1]
                if len(parts) > 2:
                    pollutant["crain"] = parts[2]
                if len(parts) > 3:
                    pollutant["cgw"] = parts[3]
                if len(parts) > 4:
                    pollutant["crdii"] = parts[4]
                if len(parts) > 5:
                    pollutant["kdecay"] = parts[5]
                if len(parts) > 6:
                    pollutant["snow_only"] = parts[6]
                # Co-pollutant, its fraction, the dry-weather and initial
                # concentrations: optional to the engine (it defaults them
                # to none/0), so dropping them silently changed the run.
                for key, idx in (("co_pollutant", 7), ("co_fraction", 8), ("cdwf", 9), ("cinit", 10)):
                    if len(parts) > idx:
                        pollutant[key] = parts[idx]
                pollutants.append(pollutant)
        model["pollutants"] = pollutants

    def _parse_landuses(self, model: dict, data: List[str]):
        """
        Parse [LANDUSES] section.

        SWMM's row is ``Name (SweepInterval Availability LastSweep)`` —
        street-sweeping days between sweeps, the fraction of buildup a
        sweep removes, and days since the last sweep. An earlier reading
        took the second column for a percent-impervious figure, a field
        this section has never had, and wrote it back as one column: the
        engine refused the rendered file with ERROR 203 (too few items).
        """
        landuses = []
        for line in data:
            parts = line.split()
            if len(parts) >= 1:
                landuse = {"name": parts[0]}
                # The engine accepts a name alone or all four columns, and
                # nothing in between; a row that gives the interval is read
                # with the other two defaulted so it writes back whole.
                if len(parts) > 1:
                    landuse["sweep_interval"] = parts[1]
                    landuse["availability"] = parts[2] if len(parts) > 2 else "0"
                    landuse["last_swept"] = parts[3] if len(parts) > 3 else "0"
                landuses.append(landuse)
        model["landuses"] = landuses

    def _parse_coverages(self, model: dict, data: List[str]):
        """Parse [COVERAGES] section."""
        coverages = []
        for line in data:
            parts = line.split()
            if len(parts) >= 3:
                coverage = {
                    "subcatchment": parts[0],
                    "landuse": parts[1],
                    "percent": parts[2],
                }
                coverages.append(coverage)
        model["coverages"] = coverages

    def _parse_buildup(self, model: dict, data: List[str]):
        """Parse [BUILDUP] section."""
        buildup = []
        for line in data:
            parts = line.split()
            if len(parts) >= 4:
                entry: Dict[str, Any] = {
                    "landuse": parts[0],
                    "pollutant": parts[1],
                    "function": parts[2],
                    "coeff1": parts[3],
                }
                if len(parts) > 4:
                    entry["coeff2"] = parts[4]
                if len(parts) > 5:
                    entry["coeff3"] = parts[5]
                if len(parts) > 6:
                    # AREA or CURB: what the buildup is normalised by.
                    # SWMM 5.1+ requires it; a row without it is rejected.
                    entry["per_unit"] = parts[6]
                buildup.append(entry)
        model["buildup"] = buildup

    def _parse_washoff(self, model: dict, data: List[str]):
        """Parse [WASHOFF] section."""
        washoff = []
        for line in data:
            parts = line.split()
            if len(parts) >= 4:
                entry: Dict[str, Any] = {
                    "landuse": parts[0],
                    "pollutant": parts[1],
                    "function": parts[2],
                    "coeff1": parts[3],
                }
                if len(parts) > 4:
                    entry["coeff2"] = parts[4]
                if len(parts) > 5:
                    entry["coeff3"] = parts[5]
                if len(parts) > 6:
                    entry["sweeping"] = parts[6]
                washoff.append(entry)
        model["washoff"] = washoff

    def _parse_lid_controls(self, model: dict, data: List[str]):
        """Parse [LID_CONTROLS] section."""
        lid_controls = []
        for line in data:
            parts = line.split()
            if len(parts) >= 2:
                entry: Dict[str, Any] = {
                    "name": parts[0],
                    "type": parts[1],
                }
                if len(parts) > 2:
                    entry["params"] = " ".join(parts[2:])
                lid_controls.append(entry)
        model["lid_controls"] = lid_controls

    def _parse_lid_usage(self, model: dict, data: List[str]):
        """Parse [LID_USAGE] section."""
        lid_usage = []
        for line in data:
            parts = line.split()
            if len(parts) >= 3:
                entry: Dict[str, Any] = {
                    "subcatchment": parts[0],
                    "lid_control": parts[1],
                    "number": parts[2],
                }
                if len(parts) > 3:
                    entry["area"] = parts[3]
                if len(parts) > 4:
                    entry["width"] = parts[4]
                if len(parts) > 5:
                    entry["init_saturation"] = parts[5]
                if len(parts) > 6:
                    entry["from_impervious"] = parts[6]
                if len(parts) > 7:
                    entry["to_pervious"] = parts[7]
                # Optional tail: RptFile ("*" for none), DrainTo, FromPerv.
                for key, idx in (("rpt_file", 8), ("drain_to", 9), ("from_pervious", 10)):
                    if len(parts) > idx:
                        entry[key] = parts[idx]
                lid_usage.append(entry)
        model["lid_usage"] = lid_usage

    def _parse_files(self, model: dict, data: List[str]):
        """Parse [FILES] section.

        Each line is ``USE|SAVE <TYPE> <path>`` — ``USE HOTSTART "warm.hsf"``,
        ``SAVE OUTFLOWS out.txt``. The key is the verb and the type together:
        keyed on the verb alone, a model that both uses a hotstart and uses
        a rainfall file kept only one of them.
        """
        files = {}
        for line in data:
            parts = line.split(None, 2)
            if len(parts) == 3 and parts[0].upper() in ("USE", "SAVE"):
                files[f"{parts[0].upper()} {parts[1].upper()}"] = parts[2]
            elif len(parts) >= 2:
                files[parts[0]] = line.split(None, 1)[1]
        model["files"] = files

    def _parse_hydrographs(self, model: dict, data: List[str]):
        """Parse [HYDROGRAPHS] section (RDII unit hydrographs).

        Two row shapes share the section under one Name:
          - Header row:    ``Name Raingage`` (2 tokens) — names the rain
            gage feeding this hydrograph group.
          - Response row:  ``Name Month Response R T K [Dmax Drecov Dinit]``
            (6+ tokens) where Month is ``ALL`` or ``JAN``..``DEC`` and
            Response is ``SHORT``/``MEDIUM``/``LONG``.

        Emitted structure (round-trips via the encoder):

            {
              "HG1": {
                "raingage": "RG1",
                "responses": [
                  {"month": "ALL", "response": "SHORT",
                   "r": "0.033", "t": "1.5", "k": "2.0"},
                  ...
                ],
              }
            }

        Numeric fields are kept as strings so values authored with
        engine-specific precision round-trip without floating-point
        reformatting.
        """
        hydrographs: Dict[str, Any] = {}
        for line in data:
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            entry = hydrographs.setdefault(
                name, {"raingage": "", "responses": []}
            )
            if len(parts) == 2:
                # Header row — names the rain gage.
                entry["raingage"] = parts[1]
            elif len(parts) >= 5:
                # Response row. SWMM's reference format places Month then
                # Response (SHORT/MEDIUM/LONG) before the R/T/K triple;
                # accept the legacy ordering (Response then Month) as a
                # fallback so .inp files saved by older tools round-trip.
                tok1 = parts[1]
                tok2 = parts[2]
                month_set = {
                    "ALL", "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
                }
                if tok1.upper() in month_set:
                    month, response = tok1, tok2
                elif tok2.upper() in month_set:
                    response, month = tok1, tok2
                else:
                    month, response = tok1, tok2
                resp: Dict[str, Any] = {
                    "month": month,
                    "response": response,
                }
                tail_keys = ("r", "t", "k", "dmax", "drecov", "dinit")
                for key, value in zip(tail_keys, parts[3:]):
                    resp[key] = value
                entry["responses"].append(resp)
        model["hydrographs"] = hydrographs

    def _parse_treatment(self, model: dict, data: List[str]):
        """Parse [TREATMENT] section.

        One row per (node, pollutant) with a free-form function string.
        Format: ``Node  Pollutant  Function``. The function may contain
        spaces and operators — we capture the entire remainder of the
        line verbatim so engine-side parsing stays correct.
        """
        treatment = []
        for line in data:
            parts = line.split(None, 2)
            if len(parts) >= 3:
                treatment.append({
                    "node": parts[0],
                    "pollutant": parts[1],
                    "function": parts[2],
                })
        model["treatment"] = treatment

    def _parse_groundwater(self, model: dict, data: List[str]):
        """Parse [GROUNDWATER] section.

        SWMM 5.2 row: ``Subcat Aquifer Node Esurf A1 B1 A2 B2 A3 Dsw
        Egwt Ebot Wgr Umc``. Older versions truncate after ``A3``.
        Trailing optional columns are emitted only when present so the
        round-trip preserves the source's column count.
        """
        groundwater = []
        for line in data:
            parts = line.split()
            if len(parts) < 5:
                continue
            entry: Dict[str, Any] = {
                "subcatchment": parts[0],
                "aquifer": parts[1],
                "node": parts[2],
                "surface_elev": parts[3],
                "a1": parts[4],
            }
            optional = (
                "b1", "a2", "b2", "a3",
                "dsw", "egwt", "ebot", "wgr", "umc",
            )
            for i, key in enumerate(optional, start=5):
                if len(parts) > i:
                    entry[key] = parts[i]
            groundwater.append(entry)
        model["groundwater"] = groundwater

    def _parse_streets(self, model: dict, data: List[str]):
        """Parse [STREETS] section (SWMM 5.2).

        Row: ``Name Tcrown Hcurb Sx nRoad Hdep Wdep Sides [Tback Sback nBack]``.
        Stored as ``dict[name -> params]`` so consumers can look up by
        street name (matches the convention used for curves / patterns).
        """
        streets: Dict[str, Dict[str, Any]] = {}
        for line in data:
            parts = line.split()
            if len(parts) < 8:
                continue
            entry: Dict[str, Any] = {
                "tcrown": parts[1],
                "hcurb": parts[2],
                "sx": parts[3],
                "n_road": parts[4],
                "h_dep": parts[5],
                "w_dep": parts[6],
                "sides": parts[7],
            }
            if len(parts) > 8:
                entry["t_back"] = parts[8]
            if len(parts) > 9:
                entry["s_back"] = parts[9]
            if len(parts) > 10:
                entry["n_back"] = parts[10]
            streets[parts[0]] = entry
        model["streets"] = streets

    def _parse_inlets(self, model: dict, data: List[str]):
        """Parse [INLETS] section (SWMM 5.2).

        Multi-line per inlet — first column is the inlet name, second
        is the type token (``GRATE`` / ``CURB`` / ``SLOTTED`` /
        ``CUSTOM`` / ``DROP_GRATE`` / ``DROP_CURB``), remainder is
        type-dependent params. We collect rows as ``dict[name ->
        list[{type, params}]]`` so a user-defined inlet that combines
        e.g. a GRATE + a CURB row stays grouped under one name.
        """
        inlets: Dict[str, List[Dict[str, Any]]] = {}
        for line in data:
            parts = line.split()
            if len(parts) < 2:
                continue
            name = parts[0]
            kind = parts[1].upper()
            params = parts[2:]
            inlets.setdefault(name, []).append({
                "type": kind,
                "params": params,
            })
        model["inlets"] = inlets

    def _parse_inlet_usage(self, model: dict, data: List[str]):
        """Parse [INLET_USAGE] section (SWMM 5.2).

        SWMM 5.2 row layout (column order matters — the previous
        version of this handler skipped the ``Number`` column and
        shifted every following field by one slot):

          Conduit  Inlet  Node  Number  Pct_Clogged  Max_Flow
                 hgt_Dstore  wdth_Dstore  Placement

        Stored as a list keyed by conduit so consumers can join onto
        link features. Optional trailing columns are emitted only
        when present.
        """
        usage = []
        for line in data:
            parts = line.split()
            if len(parts) < 3:
                continue
            entry: Dict[str, Any] = {
                "conduit": parts[0],
                "inlet": parts[1],
                "node": parts[2],
            }
            optional = (
                "number", "pct_clogged", "max_flow",
                "h_dstore", "w_dstore", "placement",
            )
            for i, key in enumerate(optional, start=3):
                if len(parts) > i:
                    entry[key] = parts[i]
            usage.append(entry)
        model["inlet_usage"] = usage

    def _parse_rdii(self, model: dict, data: List[str]):
        """Parse [RDII] section.

        SWMM 5.2 row: ``Node UnitHydrograph Sewer_Area [Factor]``.
        ``Factor`` is optional and defaults to 1.0 per the engine — we
        require only 3 columns and surface ``factor`` only when the
        author wrote it. Real-world models routinely omit it (e.g.
        Raytown), and the previous ``>= 4`` gate silently dropped
        every row.
        """
        rdii = []
        for line in data:
            parts = line.split()
            if len(parts) < 3:
                continue
            entry: Dict[str, Any] = {
                "node": parts[0],
                "unithydrograph": parts[1],
                "sewer_area": parts[2],
            }
            if len(parts) > 3:
                entry["factor"] = parts[3]
            rdii.append(entry)
        model["rdii"] = rdii
