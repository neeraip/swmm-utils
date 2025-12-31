"""SWMM input file encoder - encode dicts to .inp, .json, or .parquet formats."""

import json
from typing import Any, Dict, Optional, TextIO, Union
from pathlib import Path


class SwmmInputEncoder:
    """Encode SWMM model dicts into .inp, .json, or .parquet file formats."""

    def __init__(self):
        """Initialize the encoder."""
        pass

    def encode_to_file(
        self, model: Dict[str, Any], filepath: str, format: Optional[str] = None
    ):
        """Encode a SWMM model to a file.

        Args:
            model: SWMM model dict
            filepath: Output file path
            format: Output format ('inp', 'json', 'parquet'). If None, inferred from filepath extension.
        """
        if format is None:
            # Infer format from file extension
            ext = Path(filepath).suffix.lower()
            format_map = {".inp": "inp", ".json": "json", ".parquet": "parquet"}
            format = format_map.get(ext, "inp")

        if format == "inp":
            self.encode_to_inp_file(model, filepath)
        elif format == "json":
            self.encode_to_json(model, filepath, pretty=True)
        elif format == "parquet":
            self.encode_to_parquet(model, filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def encode_to_inp_file(self, model: Dict[str, Any], filepath: str):
        """Encode a SWMM model to a .inp file.

        Args:
            model: SWMM model dict
            filepath: Output .inp file path
        """
        with open(filepath, "w", encoding="utf-8") as f:
            self.encode_to_inp(model, f)

    def encode_to_inp(self, model: Dict[str, Any], file: TextIO):
        """Encode a SWMM model to a file object in .inp format.

        Args:
            model: SWMM model dict
            file: File object to write to
        """
        # Write sections in standard order
        self._write_title(model, file)
        self._write_options(model, file)
        self._write_evaporation(model, file)
        self._write_raingages(model, file)
        self._write_subcatchments(model, file)
        self._write_subareas(model, file)
        self._write_infiltration(model, file)
        self._write_junctions(model, file)
        self._write_outfalls(model, file)
        self._write_storage(model, file)
        self._write_conduits(model, file)
        self._write_pumps(model, file)
        self._write_orifices(model, file)
        self._write_weirs(model, file)
        self._write_outlets(model, file)
        self._write_xsections(model, file)
        self._write_losses(model, file)
        self._write_transects(model, file)
        self._write_controls(model, file)
        self._write_inflows(model, file)
        self._write_dwf(model, file)
        self._write_timeseries(model, file)
        self._write_patterns(model, file)
        self._write_curves(model, file)
        self._write_coordinates(model, file)
        self._write_vertices(model, file)
        self._write_polygons(model, file)
        self._write_symbols(model, file)
        self._write_labels(model, file)
        self._write_profiles(model, file)
        self._write_tags(model, file)
        self._write_report(model, file)
        self._write_map(model, file)
        self._write_backdrop(model, file)

    def encode_to_json(
        self, model: Dict[str, Any], filepath: str, pretty: bool = False
    ) -> str:
        """Encode SWMM model to JSON format.

        Args:
            model: SWMM model dict
            filepath: Output JSON file path
            pretty: If True, format with indentation

        Returns:
            JSON string
        """
        with open(filepath, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(model, f, indent=2)
            else:
                json.dump(model, f)

        # Return the JSON string for backwards compatibility
        return json.dumps(model, indent=2 if pretty else None)

    def encode_to_parquet(
        self, model: Dict[str, Any], output_path: str, single_file: bool = False
    ):
        """Encode SWMM model to Parquet format.

        Args:
            model: SWMM model dict
            output_path: Output file path (if single_file=True) or directory path (if single_file=False)
            single_file: If True, write all data to a single parquet file with section metadata.
                        If False, write one parquet file per section in a directory.
        """
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            raise ImportError(
                "pyarrow is required for Parquet support. Install with: pip install pyarrow"
            )

        if single_file:
            # Single file mode: store all sections in one file with section_name column
            all_rows = []
            for section_name, section_data in model.items():
                if isinstance(section_data, list) and len(section_data) > 0:
                    # Add section_name to each row
                    for item in section_data:
                        row = {"section_name": section_name, "section_data": item}
                        all_rows.append(row)
                elif isinstance(section_data, str):
                    # For string sections like title
                    all_rows.append(
                        {
                            "section_name": section_name,
                            "section_data": {"value": section_data},
                        }
                    )

            if all_rows:
                table = pa.Table.from_pylist(all_rows)
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                pq.write_table(table, str(output_file))
        else:
            # Multi-file mode: one file per section in a directory
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)

            for section_name, section_data in model.items():
                if isinstance(section_data, list) and len(section_data) > 0:
                    # Convert list of dicts to Arrow table
                    table = pa.Table.from_pylist(section_data)
                    output_file = output_dir / f"{section_name}.parquet"
                    pq.write_table(table, str(output_file))
                elif isinstance(section_data, str):
                    # For string sections (like title), write as single-row table
                    table = pa.Table.from_pylist([{"value": section_data}])
                    output_file = output_dir / f"{section_name}.parquet"
                    pq.write_table(table, str(output_file))

    # Backwards compatibility aliases
    def unparse_to_file(self, model: Dict[str, Any], filepath: str):
        """Alias for encode_to_inp_file (backwards compatibility)."""
        return self.encode_to_inp_file(model, filepath)

    def unparse(self, model: Dict[str, Any], file: TextIO):
        """Alias for encode_to_inp (backwards compatibility)."""
        return self.encode_to_inp(model, file)

    def to_json(
        self, model: Dict[str, Any], filepath: str, pretty: bool = False
    ) -> str:
        """Alias for encode_to_json (backwards compatibility)."""
        return self.encode_to_json(model, filepath, pretty)

    def to_parquet(
        self, model: Dict[str, Any], output_dir: str, single_file: bool = False
    ):
        """Alias for encode_to_parquet (backwards compatibility)."""
        return self.encode_to_parquet(model, output_dir, single_file)

    def from_json(self, json_input: Union[str, TextIO]) -> Dict[str, Any]:
        """Load SWMM model from JSON (backwards compatibility helper).

        Args:
            json_input: JSON string or file path

        Returns:
            SWMM model dict
        """
        if isinstance(json_input, str):
            # Check if it's a file path
            path = Path(json_input)
            if path.exists() and path.is_file():
                with open(path, "r", encoding="utf-8") as f:
                    json_str = f.read()
            else:
                # Parse as JSON string
                json_str = json_input
        else:
            # Assume file object
            json_str = json_input.read()

        return json.loads(json_str)

    def _write_section_header(self, file: TextIO, section_name: str):
        """Write a section header.

        Args:
            file: File to write to
            section_name: Name of section
        """
        file.write(f"\n[{section_name}]\n")
        file.write(f";;{'-' * 78}\n")

    def _get_field(self, obj: Dict[str, Any], *field_names: str, default: Any = ""):
        """Get a field from dict, trying multiple field name variations.

        Args:
            obj: Dictionary object
            *field_names: Field names to try in order
            default: Default value if none found

        Returns:
            Field value or default
        """
        for name in field_names:
            if name in obj:
                value = obj[name]
                # Return the value if it's not None, otherwise continue searching
                if value is not None:
                    return value
        return default

    def _write_title(self, model: Dict[str, Any], file: TextIO):
        """Write [TITLE] section."""
        if "title" in model and model["title"]:
            self._write_section_header(file, "TITLE")
            file.write(model["title"])
            file.write("\n")

    def _write_options(self, model: Dict[str, Any], file: TextIO):
        """Write [OPTIONS] section."""
        if "options" in model and model["options"]:
            self._write_section_header(file, "OPTIONS")
            file.write(";;Option             Value\n")

            for key, value in model["options"].items():
                file.write(f"{key:<20} {value}\n")

    def _write_evaporation(self, model: Dict[str, Any], file: TextIO):
        """Write [EVAPORATION] section."""
        if "evaporation" in model and model["evaporation"]:
            self._write_section_header(file, "EVAPORATION")
            evap = model["evaporation"]
            file.write(f";;Type       Parameters\n")

            values = " ".join(evap.get("values", []))
            file.write(f"{evap.get('type', 'CONSTANT'):<12} {values}\n")

    def _write_raingages(self, model: Dict[str, Any], file: TextIO):
        """Write [RAINGAGES] section."""
        if "raingages" in model and model["raingages"]:
            self._write_section_header(file, "RAINGAGES")
            file.write(";;Name           Format    Interval SCF      Source    \n")

            for gage in model["raingages"]:
                name = self._get_field(gage, "name")
                format_type = self._get_field(gage, "format", default="INTENSITY")
                interval = self._get_field(gage, "interval", default="1:00")
                scf = self._get_field(gage, "scf", default="1.0")
                source = self._get_field(gage, "source", default="TIMESERIES")
                file_or_station = self._get_field(
                    gage, "file_or_station", "fileOrStation", default=""
                )

                file.write(
                    f"{name:<16} {format_type:<9} {interval:<8} "
                    f"{scf:<8} {source:<9} {file_or_station}\n"
                )

    def _write_subcatchments(self, model: Dict[str, Any], file: TextIO):
        """Write [SUBCATCHMENTS] section."""
        if "subcatchments" in model and model["subcatchments"]:
            self._write_section_header(file, "SUBCATCHMENTS")
            file.write(
                ";;Name           Rain Gage        Outlet           Area     %Imperv  Width    %Slope   CurbLen  SnowPack        \n"
            )

            for sub in model["subcatchments"]:
                # Handle multiple field name variations for flexibility
                name = self._get_field(sub, "name")
                raingage = self._get_field(sub, "raingage", "rain_gage")
                outlet = self._get_field(sub, "outlet")
                area = self._get_field(sub, "area", default=0)
                imperv = self._get_field(
                    sub, "imperv", "imperv_pct", "percent_imperv", default=0
                )
                width = self._get_field(sub, "width", default=0)
                slope = self._get_field(sub, "slope", "percent_slope", default=0)
                curb_length = self._get_field(sub, "curb_length", "curb_len", default=0)
                snowpack = self._get_field(sub, "snowpack", "snow_pack")

                file.write(
                    f"{name:<16} {raingage:<16} {outlet:<16} "
                    f"{area:<8} {imperv:<8} {width:<8} "
                    f"{slope:<8} {curb_length:<8} {snowpack}\n"
                )

    def _write_subareas(self, model: Dict[str, Any], file: TextIO):
        """Write [SUBAREAS] section."""
        if "subareas" in model and model["subareas"]:
            self._write_section_header(file, "SUBAREAS")
            file.write(
                ";;Subcatchment   N-Imperv   N-Perv     S-Imperv   S-Perv     PctZero    RouteTo    PctRouted \n"
            )

            for sub in model["subareas"]:
                subcatchment = self._get_field(sub, "subcatchment")
                n_imperv = self._get_field(sub, "n_imperv", "nImperv", default=0)
                n_perv = self._get_field(sub, "n_perv", "nPerv", default=0)
                s_imperv = self._get_field(sub, "s_imperv", "sImperv", default=0)
                s_perv = self._get_field(sub, "s_perv", "sPerv", default=0)
                pct_zero = self._get_field(sub, "pct_zero", "pctZero", default=0)
                route_to = self._get_field(sub, "route_to", "routeTo")
                pct_routed = self._get_field(sub, "pct_routed", "pctRouted")

                file.write(
                    f"{subcatchment:<16} {n_imperv:<10} {n_perv:<10} "
                    f"{s_imperv:<10} {s_perv:<10} {pct_zero:<10} "
                    f"{route_to:<10} {pct_routed}\n"
                )

    def _write_infiltration(self, model: Dict[str, Any], file: TextIO):
        """Write [INFILTRATION] section."""
        if "infiltrations" in model and model["infiltrations"]:
            self._write_section_header(file, "INFILTRATION")
            file.write(
                ";;Subcatchment   Param1     Param2     Param3     Param4     Param5    \n"
            )

            for infil in model["infiltrations"]:
                subcatchment = self._get_field(infil, "subcatchment")

                # Handle both array format (parameters) and individual fields (param1, param2, ...)
                if "parameters" in infil:
                    # Array format: parameters is a list
                    params = infil["parameters"]
                    param1 = params[0] if len(params) > 0 else ""
                    param2 = params[1] if len(params) > 1 else ""
                    param3 = params[2] if len(params) > 2 else ""
                    param4 = params[3] if len(params) > 3 else ""
                    param5 = params[4] if len(params) > 4 else ""
                else:
                    # Individual field format: param1, param2, ...
                    param1 = self._get_field(infil, "param1", default="")
                    param2 = self._get_field(infil, "param2", default="")
                    param3 = self._get_field(infil, "param3", default="")
                    param4 = self._get_field(infil, "param4", default="")
                    param5 = self._get_field(infil, "param5", default="")

                file.write(
                    f"{subcatchment:<16} {param1:<10} {param2:<10} "
                    f"{param3:<10} {param4:<10} {param5}\n"
                )

    def _write_junctions(self, model: Dict[str, Any], file: TextIO):
        """Write [JUNCTIONS] section."""
        if "junctions" in model and model["junctions"]:
            self._write_section_header(file, "JUNCTIONS")
            file.write(
                ";;Name           Elevation  MaxDepth   InitDepth  SurDepth   Aponded   \n"
            )

            for junc in model["junctions"]:
                name = self._get_field(junc, "name")
                elevation = self._get_field(junc, "elevation", default="0")
                max_depth = self._get_field(junc, "max_depth", "maxDepth", default="0")
                init_depth = self._get_field(
                    junc, "init_depth", "initDepth", default="0"
                )
                surcharge_depth = self._get_field(
                    junc, "surcharge_depth", "surchargeDepth", default="0"
                )
                ponded_area = self._get_field(
                    junc, "ponded_area", "pondedArea", default="0"
                )

                file.write(
                    f"{name:<16} {elevation:<10} {max_depth:<10} "
                    f"{init_depth:<10} {surcharge_depth:<10} {ponded_area}\n"
                )

    def _write_outfalls(self, model: Dict[str, Any], file: TextIO):
        """Write [OUTFALLS] section."""
        if "outfalls" in model and model["outfalls"]:
            self._write_section_header(file, "OUTFALLS")
            file.write(
                ";;Name           Elevation  Type       Stage Data       Gated    Route To        \n"
            )

            for outfall in model["outfalls"]:
                name = self._get_field(outfall, "name")
                elevation = self._get_field(outfall, "elevation", default="0")
                outfall_type = self._get_field(outfall, "type", default="FREE")
                stage_data = self._get_field(
                    outfall, "stage_data", "stageData", default=""
                )
                gated = self._get_field(outfall, "gated", default="NO")
                route_to = self._get_field(outfall, "route_to", "routeTo", default="")

                file.write(
                    f"{name:<16} {elevation:<10} {outfall_type:<10} "
                    f"{stage_data:<16} {gated:<8} {route_to}\n"
                )

    def _write_storage(self, model: Dict[str, Any], file: TextIO):
        """Write [STORAGE] section."""
        if "storage" in model and model["storage"]:
            self._write_section_header(file, "STORAGE")
            file.write(
                ";;Name           Elev.    MaxDepth   InitDepth  Shape      Curve Name/Params            \n"
            )

            for storage in model["storage"]:
                name = self._get_field(storage, "name")
                elevation = self._get_field(storage, "elevation", default="0")
                max_depth = self._get_field(
                    storage, "max_depth", "maxDepth", default="0"
                )
                init_depth = self._get_field(
                    storage, "init_depth", "initDepth", default="0"
                )
                curve_type = self._get_field(
                    storage, "curve_type", "curveType", default="TABULAR"
                )
                curve_params = storage.get("curve_params", [])
                params = " ".join(curve_params) if curve_params else ""

                file.write(
                    f"{name:<16} {elevation:<8} {max_depth:<10} "
                    f"{init_depth:<10} {curve_type:<10} {params}\n"
                )

    def _write_conduits(self, model: Dict[str, Any], file: TextIO):
        """Write [CONDUITS] section."""
        if "conduits" in model and model["conduits"]:
            self._write_section_header(file, "CONDUITS")
            file.write(
                ";;Name           From Node        To Node          Length     Roughness  InOffset   OutOffset  InitFlow   MaxFlow   \n"
            )

            for conduit in model["conduits"]:
                name = self._get_field(conduit, "name")
                from_node = self._get_field(conduit, "from_node", "fromNode")
                to_node = self._get_field(conduit, "to_node", "toNode")
                length = self._get_field(conduit, "length", default=0)
                roughness = self._get_field(conduit, "roughness", default=0)
                in_offset = self._get_field(conduit, "in_offset", "inOffset", default=0)
                out_offset = self._get_field(
                    conduit, "out_offset", "outOffset", default=0
                )
                init_flow = self._get_field(conduit, "init_flow", "initFlow", default=0)
                max_flow = self._get_field(conduit, "max_flow", "maxFlow", default=0)

                file.write(
                    f"{name:<16} {from_node:<16} {to_node:<16} "
                    f"{length:<10} {roughness:<10} {in_offset:<10} "
                    f"{out_offset:<10} {init_flow:<10} {max_flow}\n"
                )

    def _write_pumps(self, model: Dict[str, Any], file: TextIO):
        """Write [PUMPS] section."""
        if "pumps" in model and model["pumps"]:
            self._write_section_header(file, "PUMPS")
            file.write(
                ";;Name           From Node        To Node          Pump Curve       Status   Sartup Shutoff \n"
            )

            for pump in model["pumps"]:
                name = self._get_field(pump, "name")
                from_node = self._get_field(pump, "from_node", "fromNode")
                to_node = self._get_field(pump, "to_node", "toNode")
                curve = self._get_field(pump, "curve", default="")
                status = self._get_field(pump, "status", default="ON")
                startup = self._get_field(pump, "startup", default="0")
                shutoff = self._get_field(pump, "shutoff", default="0")

                file.write(
                    f"{name:<16} {from_node:<16} {to_node:<16} "
                    f"{curve:<16} {status:<8} {startup:<6} {shutoff}\n"
                )

    def _write_orifices(self, model: Dict[str, Any], file: TextIO):
        """Write [ORIFICES] section."""
        if "orifices" in model and model["orifices"]:
            self._write_section_header(file, "ORIFICES")
            file.write(
                ";;Name           From Node        To Node          Type         Offset     Qcoeff     Gated    CloseTime \n"
            )

            for orifice in model["orifices"]:
                name = self._get_field(orifice, "name")
                from_node = self._get_field(orifice, "from_node", "fromNode")
                to_node = self._get_field(orifice, "to_node", "toNode")
                orifice_type = self._get_field(orifice, "type", default="")
                offset = self._get_field(orifice, "offset", default="0")
                discharge_coeff = self._get_field(
                    orifice, "discharge_coeff", "dischargeCoeff", default="0"
                )
                gated = self._get_field(orifice, "gated", default="NO")
                close_time = self._get_field(
                    orifice, "close_time", "closeTime", default="0"
                )

                file.write(
                    f"{name:<16} {from_node:<16} {to_node:<16} "
                    f"{orifice_type:<12} {offset:<10} {discharge_coeff:<10} "
                    f"{gated:<8} {close_time}\n"
                )

    def _write_weirs(self, model: Dict[str, Any], file: TextIO):
        """Write [WEIRS] section."""
        if "weirs" in model and model["weirs"]:
            self._write_section_header(file, "WEIRS")
            file.write(
                ";;Name           From Node        To Node          Type         CrestHt    Qcoeff     Gated    EndCon   EndCoeff   Surcharge  RoadWidth  RoadSurf  \n"
            )

            for weir in model["weirs"]:
                name = self._get_field(weir, "name")
                from_node = self._get_field(weir, "from_node", "fromNode")
                to_node = self._get_field(weir, "to_node", "toNode")
                weir_type = self._get_field(weir, "type", default="TRANSVERSE")
                crest_height = self._get_field(
                    weir, "crest_height", "crestHeight", default="0"
                )
                discharge_coeff = self._get_field(
                    weir, "discharge_coeff", "dischargeCoeff", default="0"
                )
                gated = self._get_field(weir, "gated", default="NO")
                end_con = self._get_field(weir, "end_con", "endCon", default="0")
                end_coeff = self._get_field(weir, "end_coeff", "endCoeff", default="0")
                surcharge = self._get_field(weir, "surcharge", default="YES")
                road_width = self._get_field(
                    weir, "road_width", "roadWidth", default=""
                )
                road_surf = self._get_field(weir, "road_surf", "roadSurf", default="")

                file.write(
                    f"{name:<16} {from_node:<16} {to_node:<16} "
                    f"{weir_type:<12} {crest_height:<10} {discharge_coeff:<10} "
                    f"{gated:<8} {end_con:<8} {end_coeff:<10} {surcharge:<10} {road_width:<10} {road_surf}\n"
                )

    def _write_xsections(self, model: Dict[str, Any], file: TextIO):
        """Write [XSECTIONS] section."""
        if "xsections" in model and model["xsections"]:
            self._write_section_header(file, "XSECTIONS")
            file.write(
                ";;Link           Shape        Geom1            Geom2      Geom3      Geom4      Barrels    Culvert   \n"
            )

            for xs in model["xsections"]:
                link = self._get_field(xs, "link")
                shape = self._get_field(xs, "shape", default="CIRCULAR")
                geom1 = self._get_field(xs, "geom1", default="0")
                geom2 = self._get_field(xs, "geom2", default="0")
                geom3 = self._get_field(xs, "geom3", default="0")
                geom4 = self._get_field(xs, "geom4", default="0")
                barrels = self._get_field(xs, "barrels", default="1")
                culvert = self._get_field(xs, "culvert", default="")

                file.write(
                    f"{link:<16} {shape:<12} {geom1:<16} "
                    f"{geom2:<10} {geom3:<10} {geom4:<10} {barrels:<10} {culvert}\n"
                )

    def _write_losses(self, model: Dict[str, Any], file: TextIO):
        """Write [LOSSES] section."""
        if "losses" in model and model["losses"]:
            self._write_section_header(file, "LOSSES")
            file.write(
                ";;Link           Kentry     Kexit      Kavg       Flap Gate  Seepage   \n"
            )

            for loss in model["losses"]:
                link = self._get_field(loss, "link")
                inlet = self._get_field(loss, "inlet", default="0")
                outlet = self._get_field(loss, "outlet", default="0")
                average = self._get_field(loss, "average", default="0")
                flap_gate = self._get_field(loss, "flap_gate", "flapGate", default="NO")
                seepage = self._get_field(loss, "seepage", default="0")

                file.write(
                    f"{link:<16} {inlet:<10} {outlet:<10} "
                    f"{average:<10} {flap_gate:<10} {seepage}\n"
                )

    def _write_controls(self, model: Dict[str, Any], file: TextIO):
        """Write [CONTROLS] section."""
        if "controls" in model and model["controls"]:
            self._write_section_header(file, "CONTROLS")
            file.write(model["controls"])
            file.write("\n")

    def _write_timeseries(self, model: Dict[str, Any], file: TextIO):
        """Write [TIMESERIES] section."""
        if "timeseries" in model and model["timeseries"]:
            self._write_section_header(file, "TIMESERIES")
            file.write(";;Name           Date       Time       Value     \n")

            # Handle both dict format (name -> entries) and array format ([{name, entries}])
            timeseries_data = model["timeseries"]
            if isinstance(timeseries_data, dict):
                # Dict format: iterate over items
                for name, entries in timeseries_data.items():
                    for entry in entries:
                        date = self._get_field(entry, "date", default="")
                        time = self._get_field(entry, "time", default="")
                        value = self._get_field(entry, "value", default="0")

                        # Format output based on what fields are present
                        if date and time:
                            file.write(f"{name:<16} {date:<10} {time:<10} {value}\n")
                        elif time:
                            file.write(f"{name:<16} {time:<10} {value}\n")
                        else:
                            file.write(f"{name:<16} {value}\n")
            elif isinstance(timeseries_data, list):
                # Array format: iterate over list
                for ts in timeseries_data:
                    name = self._get_field(ts, "name")
                    entries = ts.get("entries", [])
                    for entry in entries:
                        date = self._get_field(entry, "date", default="")
                        time = self._get_field(entry, "time", default="")
                        value = self._get_field(entry, "value", default="0")

                        # Format output based on what fields are present
                        if date and time:
                            file.write(f"{name:<16} {date:<10} {time:<10} {value}\n")
                        elif time:
                            file.write(f"{name:<16} {time:<10} {value}\n")
                        else:
                            file.write(f"{name:<16} {value}\n")

    def _write_patterns(self, model: Dict[str, Any], file: TextIO):
        """Write [PATTERNS] section."""
        if "patterns" in model and model["patterns"]:
            self._write_section_header(file, "PATTERNS")
            file.write(";;Name           Type       Multipliers\n")

            # Handle both dict format (name -> values) and array format ([{name, values}])
            patterns_data = model["patterns"]
            if isinstance(patterns_data, dict):
                # Dict format: iterate over items
                for name, values in patterns_data.items():
                    # Write 6 values per line
                    for i in range(0, len(values), 6):
                        chunk = values[i : i + 6]
                        file.write(f"{name:<16} {' '.join(chunk)}\n")
            elif isinstance(patterns_data, list):
                # Array format: iterate over list
                for pattern in patterns_data:
                    name = self._get_field(pattern, "name")
                    values = pattern.get("values", [])
                    # Write 6 values per line
                    for i in range(0, len(values), 6):
                        chunk = values[i : i + 6]
                        file.write(f"{name:<16} {' '.join(chunk)}\n")

    def _write_curves(self, model: Dict[str, Any], file: TextIO):
        """Write [CURVES] section."""
        if "curves" in model and model["curves"]:
            self._write_section_header(file, "CURVES")
            file.write(";;Name           Type       X-Value    Y-Value   \n")

            # Handle both dict format (name -> {type, points}) and array format ([{name, type, points}])
            curves_data = model["curves"]
            if isinstance(curves_data, dict):
                # Dict format: iterate over items
                for name, curve in curves_data.items():
                    curve_type = curve.get("type", "STORAGE")
                    points = curve.get("points", [])
                    for point in points:
                        x = self._get_field(point, "x", default="0")
                        y = self._get_field(point, "y", default="0")
                        file.write(f"{name:<16} {curve_type:<10} {x:<10} {y}\n")
            elif isinstance(curves_data, list):
                # Array format: iterate over list
                for curve in curves_data:
                    name = self._get_field(curve, "name")
                    curve_type = self._get_field(curve, "type", default="STORAGE")
                    points = curve.get("points", [])
                    for point in points:
                        x = self._get_field(point, "x", default="0")
                        y = self._get_field(point, "y", default="0")
                        file.write(f"{name:<16} {curve_type:<10} {x:<10} {y}\n")

    def _write_coordinates(self, model: Dict[str, Any], file: TextIO):
        """Write [COORDINATES] section."""
        if "coordinates" in model and model["coordinates"]:
            self._write_section_header(file, "COORDINATES")
            file.write(";;Node           X-Coord            Y-Coord           \n")

            for coord in model["coordinates"]:
                node = self._get_field(coord, "node")
                x = self._get_field(coord, "x", default="0")
                y = self._get_field(coord, "y", default="0")
                file.write(f"{node:<16} {x:<18} {y}\n")

    def _write_vertices(self, model: Dict[str, Any], file: TextIO):
        """Write [VERTICES] section."""
        if "vertices" in model and model["vertices"]:
            self._write_section_header(file, "VERTICES")
            file.write(";;Link           X-Coord            Y-Coord           \n")

            for vertex in model["vertices"]:
                link = self._get_field(vertex, "link")
                x = self._get_field(vertex, "x", default="0")
                y = self._get_field(vertex, "y", default="0")
                file.write(f"{link:<16} {x:<18} {y}\n")

    def _write_polygons(self, model: Dict[str, Any], file: TextIO):
        """Write [POLYGONS] section."""
        if "polygons" in model and model["polygons"]:
            self._write_section_header(file, "POLYGONS")
            file.write(";;Subcatchment   X-Coord            Y-Coord           \n")

            for poly in model["polygons"]:
                subcatchment = self._get_field(poly, "subcatchment")
                x = self._get_field(poly, "x", default="0")
                y = self._get_field(poly, "y", default="0")
                file.write(f"{subcatchment:<16} {x:<18} {y}\n")

    def _write_symbols(self, model: Dict[str, Any], file: TextIO):
        """Write [SYMBOLS] section."""
        if "symbols" in model and model["symbols"]:
            self._write_section_header(file, "SYMBOLS")
            file.write(";;Gage           X-Coord            Y-Coord           \n")

            for symbol in model["symbols"]:
                gage = self._get_field(symbol, "gage")
                x = self._get_field(symbol, "x", default="0")
                y = self._get_field(symbol, "y", default="0")
                file.write(f"{gage:<16} {x:<18} {y}\n")

    def _write_labels(self, model: Dict[str, Any], file: TextIO):
        """Write [LABELS] section."""
        if "labels" in model and model["labels"]:
            self._write_section_header(file, "LABELS")
            file.write(";;X-Coord          Y-Coord            Label           \n")

            for label in model["labels"]:
                x = self._get_field(label, "x", default="0")
                y = self._get_field(label, "y", default="0")
                text = self._get_field(label, "text", default="")
                anchor = self._get_field(label, "anchor", default="")
                file.write(f'{x:<17} {y:<18} "{text}" {anchor}\n')

    def _write_tags(self, model: Dict[str, Any], file: TextIO):
        """Write [TAGS] section."""
        if "tags" in model and model["tags"]:
            self._write_section_header(file, "TAGS")

            for tag in model["tags"]:
                tag_type = self._get_field(tag, "type", default="Node")
                name = self._get_field(tag, "name")
                tag_value = self._get_field(tag, "tag", default="")
                file.write(f"{tag_type:<16} {name:<16} {tag_value}\n")

    def _write_outlets(self, model: Dict[str, Any], file: TextIO):
        """Write [OUTLETS] section."""
        if "outlets" in model and model["outlets"]:
            self._write_section_header(file, "OUTLETS")
            file.write(
                ";;Name           From Node        To Node          Offset     Type         Curve Name       Gated   \n"
            )

            for outlet in model["outlets"]:
                name = self._get_field(outlet, "name")
                from_node = self._get_field(outlet, "from_node", "fromNode")
                to_node = self._get_field(outlet, "to_node", "toNode")
                offset = self._get_field(outlet, "offset", default="0")
                outlet_type = self._get_field(
                    outlet, "type", default="FUNCTIONAL/DEPTH"
                )
                curve_name = self._get_field(
                    outlet, "curve_name", "curveName", default=""
                )
                gated = self._get_field(outlet, "gated", default="NO")

                file.write(
                    f"{name:<16} {from_node:<16} {to_node:<16} "
                    f"{offset:<10} {outlet_type:<12} {curve_name:<16} {gated}\n"
                )

    def _write_transects(self, model: Dict[str, Any], file: TextIO):
        """Write [TRANSECTS] section."""
        if "transects" in model and model["transects"]:
            self._write_section_header(file, "TRANSECTS")
            file.write(model["transects"])
            file.write("\n")

    def _write_report(self, model: Dict[str, Any], file: TextIO):
        """Write [REPORT] section."""
        if "report" in model and model["report"]:
            self._write_section_header(file, "REPORT")

            for key, value in model["report"].items():
                file.write(f"{key:<20} {value}\n")

    def _write_map(self, model: Dict[str, Any], file: TextIO):
        """Write [MAP] section."""
        if "map" in model and model["map"]:
            self._write_section_header(file, "MAP")

            for key, value in model["map"].items():
                file.write(f"{key:<20} {value}\n")

    def _write_backdrop(self, model: Dict[str, Any], file: TextIO):
        """Write [BACKDROP] section."""
        if "backdrop" in model and model["backdrop"]:
            self._write_section_header(file, "BACKDROP")

            for key, value in model["backdrop"].items():
                file.write(f"{key:<20} {value}\n")

    def _write_profiles(self, model: Dict[str, Any], file: TextIO):
        """Write [PROFILES] section."""
        if "profiles" in model and model["profiles"]:
            self._write_section_header(file, "PROFILES")

            for profile in model["profiles"]:
                name = self._get_field(profile, "name")
                links = profile.get("links", [])
                links_str = " ".join(links) if links else ""
                file.write(f"{name:<16} {links_str}\n")

    def _write_inflows(self, model: Dict[str, Any], file: TextIO):
        """Write [INFLOWS] section."""
        if "inflows" in model and model["inflows"]:
            self._write_section_header(file, "INFLOWS")
            file.write(
                ";;Node           Constituent      Time Series      Type     Mfactor  Sfactor  Baseline Pattern\n"
            )

            for inflow in model["inflows"]:
                node = self._get_field(inflow, "node")
                constituent = self._get_field(inflow, "constituent", default="FLOW")
                timeseries = self._get_field(inflow, "timeseries", default="")
                inflow_type = self._get_field(inflow, "type", default="CONCEN")
                mfactor = self._get_field(inflow, "mfactor", default="1.0")
                sfactor = self._get_field(inflow, "sfactor", default="")
                baseline = self._get_field(inflow, "baseline", default="")
                pattern = self._get_field(inflow, "pattern", default="")

                file.write(
                    f"{node:<16} {constituent:<16} {timeseries:<16} "
                    f"{inflow_type:<8} {mfactor:<8} {sfactor:<8} {baseline:<8} {pattern}\n"
                )

    def _write_dwf(self, model: Dict[str, Any], file: TextIO):
        """Write [DWF] section."""
        if "dwf" in model and model["dwf"]:
            self._write_section_header(file, "DWF")
            file.write(";;Node           Constituent      Baseline   Patterns\n")

            for entry in model["dwf"]:
                node = self._get_field(entry, "node")
                constituent = self._get_field(entry, "constituent", default="")
                baseline = self._get_field(entry, "baseline", default="0")
                patterns = " ".join(entry.get("patterns", []))

                file.write(f"{node:<16} {constituent:<16} {baseline:<10} {patterns}\n")
