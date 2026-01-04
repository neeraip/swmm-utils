"""SWMM input file decoder - decode .inp files into Python dicts."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, TextIO, Union


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
        with open(filepath, "r", encoding="utf-8") as f:
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

        elif file_path.is_dir():
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

        else:
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

        Args:
            file: File object to read from

        Returns:
            Dictionary with parsed SWMM data
        """
        model = {}
        self.current_section = None
        self.line_number = 0
        section_data = []

        for line in file:
            self.line_number += 1
            line = self._preprocess_line(line)

            # Skip empty lines
            if not line:
                continue

            # Check for section header
            section_match = re.match(r"^\[([A-Z_]+)\]$", line)
            if section_match:
                # Process previous section
                if self.current_section and section_data:
                    self._process_section(model, self.current_section, section_data)

                # Start new section
                self.current_section = section_match.group(1)
                section_data = []
                continue

            # Add data to current section
            if self.current_section:
                section_data.append(line)

        # Process final section
        if self.current_section and section_data:
            self._process_section(model, self.current_section, section_data)

        return model

    def _preprocess_line(self, line: str) -> str:
        """Preprocess a line by removing comments and whitespace.

        Args:
            line: Raw line from file

        Returns:
            Cleaned line or empty string
        """
        # Remove comments
        if ";" in line:
            line = line[: line.index(";")]

        # Strip whitespace
        line = line.strip()

        return line

    def _process_section(self, model: dict, section: str, data: List[str]):
        """Process a section and add to model.

        Args:
            model: SwmmModel to populate
            section: Section name
            data: List of data lines
        """
        handler_name = f"_parse_{section.lower()}"
        handler = getattr(self, handler_name, None)

        if handler:
            handler(model, data)
        else:
            print(f"Warning: No handler for section [{section}]")

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
        """Parse [EVAPORATION] section."""
        evaporation = {}
        for line in data:
            parts = line.split()
            if parts:
                evap_type = parts[0]
                evaporation["type"] = evap_type
                if len(parts) > 1:
                    evaporation["values"] = parts[1:]
        model["evaporation"] = evaporation

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
                entry = {
                    "node": parts[0],
                    "constituent": parts[1],
                    "baseline": parts[2],
                }
                if len(parts) > 3:
                    entry["patterns"] = parts[3:]
                dwf.append(entry)
        model["dwf"] = dwf
