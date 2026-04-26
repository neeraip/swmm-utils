"""SWMM input file decoder - decode .inp files into Python dicts."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Union


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
        pending_desc: List[str] = []

        for raw in file:
            self.line_number += 1
            stripped_full = raw.strip()

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
            # dispatch table stays simple.
            section_match = re.match(r"^\[([A-Za-z_]+)\]$", stripped_full)
            if section_match:
                if self.current_section and section_data:
                    self._process_section(
                        model, self.current_section, section_data, section_desc
                    )
                self.current_section = section_match.group(1).upper()
                section_data = []
                section_desc = []
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

        if self.current_section and section_data:
            self._process_section(
                model, self.current_section, section_data, section_desc
            )

        return model

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
        handler(model, data)  # type: ignore

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
            if len(parts) == 2:
                key, value = parts
                options[key] = value
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

        Each line is one of TEMPERATURE / EVAPORATION / RAINFALL /
        CONDUCTIVITY followed by 12 monthly values. Stored as a dict
        keyed by lowercased token with the values space-joined.
        """
        adjustments: Dict[str, Any] = {}
        for line in data:
            parts = line.split()
            if not parts:
                continue
            adjustments[parts[0].lower()] = " ".join(parts[1:])
        model["adjustments"] = adjustments

    def _parse_aquifers(self, model: dict, data: List[str]):
        """Parse [AQUIFERS] section.

        One row per aquifer:
          name  por  wp  fc  hydcon  condslp  tension  upevap
                losrate  gw_height  water_table  [upm_field]
        """
        aquifers = []
        for line in data:
            parts = line.split()
            if len(parts) >= 11:
                aq = {
                    "name": parts[0],
                    "por": parts[1],
                    "wp": parts[2],
                    "fc": parts[3],
                    "hydcon": parts[4],
                    "condslp": parts[5],
                    "tension": parts[6],
                    "upevap": parts[7],
                    "losrate": parts[8],
                    "gw_height": parts[9],
                    "water_table": parts[10],
                }
                if len(parts) > 11:
                    aq["upm_field"] = parts[11]
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
        """Parse [RAINGAGES] section."""
        raingages = []
        for line in data:
            parts = line.split()
            if len(parts) >= 6:
                gage = {
                    "name": parts[0],
                    "format": parts[1],
                    "interval": parts[2],
                    "scf": parts[3],
                    "source": parts[4],
                    "file_or_station": " ".join(parts[5:]),
                }
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
                subareas.append(subarea)
        model["subareas"] = subareas

    def _parse_infiltration(self, model: dict, data: List[str]):
        """Parse [INFILTRATION] section."""
        infiltrations = []
        for line in data:
            parts = line.split()
            if len(parts) >= 4:
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
                junctions.append(junction)
        model["junctions"] = junctions

    def _parse_outfalls(self, model: dict, data: List[str]):
        """Parse [OUTFALLS] section."""
        outfalls = []
        for line in data:
            parts = line.split()
            if len(parts) >= 3:
                outfall = {"name": parts[0], "elevation": parts[1], "type": parts[2]}
                if len(parts) > 3:
                    outfall["stage_data"] = parts[3]
                if len(parts) > 4:
                    outfall["gated"] = parts[4]
                if len(parts) > 5:
                    outfall["route_to"] = parts[5]
                outfalls.append(outfall)
        model["outfalls"] = outfalls

    def _parse_storage(self, model: dict, data: List[str]):
        """Parse [STORAGE] section."""
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
                    "curve_params": parts[5:],
                }
                storage_nodes.append(storage)
        model["storage"] = storage_nodes

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
        """Parse [CURVES] section."""
        curves = {}

        for line in data:
            parts = line.split()
            if len(parts) >= 3:
                name = parts[0]
                if name not in curves:
                    curves[name] = {"type": parts[1], "points": []}
                # Pairs of x, y values
                for i in range(1, len(parts), 2):
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
                if len(parts) > 5:
                    outlet["curve_name"] = parts[5]
                if len(parts) > 6:
                    outlet["gated"] = parts[6]
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
            if len(parts) >= 5:
                inflow = {
                    "node": parts[0],
                    "constituent": parts[1],
                    "timeseries": parts[2],
                    "type": parts[3],
                    "mfactor": parts[4],
                }
                if len(parts) > 5:
                    inflow["sfactor"] = parts[5]
                if len(parts) > 6:
                    inflow["baseline"] = parts[6]
                if len(parts) > 7:
                    inflow["pattern"] = parts[7]
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
                pollutants.append(pollutant)
        model["pollutants"] = pollutants

    def _parse_landuses(self, model: dict, data: List[str]):
        """Parse [LANDUSES] section."""
        landuses = []
        for line in data:
            parts = line.split()
            if len(parts) >= 1:
                landuse = {"name": parts[0]}
                if len(parts) > 1:
                    landuse["percent_imperv"] = parts[1]
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
                lid_usage.append(entry)
        model["lid_usage"] = lid_usage

    def _parse_files(self, model: dict, data: List[str]):
        """Parse [FILES] section."""
        files = {}
        for line in data:
            parts = line.split(None, 1)
            if len(parts) == 2:
                key, value = parts
                files[key] = value
        model["files"] = files

    def _parse_hydrographs(self, model: dict, data: List[str]):
        """Parse [HYDROGRAPHS] section (not supported - store as-is)."""
        model["hydrographs"] = "\n".join(data)

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

        Row: ``Conduit Inlet Node [Pct_Clogged Max_Flow Hgt_Dstore
        Wdth_Dstore Placement]``. Stored as a list keyed by conduit so
        consumers can join onto link features.
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
                "pct_clogged", "max_flow",
                "h_dstore", "w_dstore", "placement",
            )
            for i, key in enumerate(optional, start=3):
                if len(parts) > i:
                    entry[key] = parts[i]
            usage.append(entry)
        model["inlet_usage"] = usage

    def _parse_rdii(self, model: dict, data: List[str]):
        """Parse [RDII] section."""
        rdii = []
        for line in data:
            parts = line.split()
            if len(parts) >= 4:
                entry: Dict[str, Any] = {
                    "node": parts[0],
                    "unithydrograph": parts[1],
                    "sewer_area": parts[2],
                    "factor": parts[3],
                }
                rdii.append(entry)
        model["rdii"] = rdii
