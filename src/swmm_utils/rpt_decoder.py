"""
SWMM Report File Decoder

This module provides functionality to decode SWMM .rpt (report) files into structured data.
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional


class SwmmReportDecoder:
    """Decoder for SWMM report (.rpt) files."""

    def decode_file(self, filepath: str | Path) -> Dict[str, Any]:
        """
        Decode a SWMM report file.

        Args:
            filepath: Path to the .rpt file

        Returns:
            Dictionary containing parsed report data
        """
        filepath = Path(filepath)

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        report_data = {
            "header": self._parse_header(content),
            "element_count": self._parse_element_count(content),
            "analysis_options": self._parse_analysis_options(content),
            "continuity": self._parse_continuity(content),
            "subcatchment_runoff": self._parse_subcatchment_runoff(content),
            "node_depth": self._parse_node_depth(content),
            "node_inflow": self._parse_node_inflow(content),
            "node_flooding": self._parse_node_flooding(content),
            "node_surcharge": self._parse_node_surcharge(content),
            "storage_volume": self._parse_storage_volume(content),
            "outfall_loading": self._parse_outfall_loading(content),
            "link_flow": self._parse_link_flow(content),
            "flow_classification": self._parse_flow_classification(content),
            "conduit_surcharge": self._parse_conduit_surcharge(content),
            "pumping_summary": self._parse_pumping_summary(content),
            "lid_performance": self._parse_lid_performance(content),
            "groundwater_summary": self._parse_groundwater_summary(content),
            "quality_routing_continuity": self._parse_quality_routing_continuity(
                content
            ),
            "subcatchment_washoff": self._parse_subcatchment_washoff(content),
            "link_pollutant_load": self._parse_link_pollutant_load(content),
            "analysis_time": self._parse_analysis_time(content),
        }

        return report_data

    def _parse_header(self, content: str) -> Dict[str, str]:
        """Parse the report header."""
        header = {}

        # Extract version
        version_match = re.search(
            r"EPA STORM WATER MANAGEMENT MODEL - VERSION ([\d.]+)", content
        )
        if version_match:
            header["version"] = version_match.group(1)

        # Extract build
        build_match = re.search(r"Build ([\d.]+)", content)
        if build_match:
            header["build"] = build_match.group(1)

        # Extract title (first few lines after header)
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "EPA STORM WATER MANAGEMENT MODEL" in line:
                # Next non-empty line should be the title
                for j in range(i + 3, min(i + 10, len(lines))):
                    if lines[j].strip() and not lines[j].strip().startswith("*"):
                        header["title"] = lines[j].strip()
                        break
                break

        return header

    def _parse_element_count(self, content: str) -> Dict[str, int]:
        """Parse the element count section."""
        element_count = {}

        section_match = re.search(
            r"\*+\s*Element Count\s*\*+(.+?)(?=\n\s*\n|\*+)", content, re.DOTALL
        )

        if section_match:
            section_text = section_match.group(1)

            patterns = {
                "rain_gages": r"Number of rain gages\s*\.+\s*(\d+)",
                "subcatchments": r"Number of subcatchments\s*\.+\s*(\d+)",
                "nodes": r"Number of nodes\s*\.+\s*(\d+)",
                "links": r"Number of links\s*\.+\s*(\d+)",
                "pollutants": r"Number of pollutants\s*\.+\s*(\d+)",
                "land_uses": r"Number of land uses\s*\.+\s*(\d+)",
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, section_text)
                if match:
                    element_count[key] = int(match.group(1))

        return element_count

    def _parse_analysis_options(self, content: str) -> Dict[str, Any]:
        """Parse the analysis options section."""
        options = {}

        section_match = re.search(
            r"\*+\s*Analysis Options\s*\*+(.+?)(?=\n\s*\n\s*\*+)", content, re.DOTALL
        )

        if section_match:
            section_text = section_match.group(1)

            # Parse flow units
            flow_match = re.search(r"Flow Units\s*\.+\s*(\w+)", section_text)
            if flow_match:
                options["flow_units"] = flow_match.group(1)

            # Parse infiltration method
            infil_match = re.search(r"Infiltration Method\s*\.+\s*(\w+)", section_text)
            if infil_match:
                options["infiltration_method"] = infil_match.group(1)

            # Parse flow routing method
            routing_match = re.search(
                r"Flow Routing Method\s*\.+\s*(\w+)", section_text
            )
            if routing_match:
                options["flow_routing_method"] = routing_match.group(1)

            # Parse dates
            start_match = re.search(r"Starting Date\s*\.+\s*(.+)", section_text)
            if start_match:
                options["starting_date"] = start_match.group(1).strip()

            end_match = re.search(r"Ending Date\s*\.+\s*(.+)", section_text)
            if end_match:
                options["ending_date"] = end_match.group(1).strip()

        return options

    def _parse_continuity(self, content: str) -> Dict[str, Any]:
        """Parse continuity sections (runoff, flow routing, quality)."""
        continuity = {}

        # Runoff Quantity Continuity
        runoff_match = re.search(
            r"Runoff Quantity Continuity\s+acre-feet\s+inches\s*\*+(.+?)(?=\n\s*\n\s*\*+)",
            content,
            re.DOTALL,
        )
        if runoff_match:
            continuity["runoff_quantity"] = self._parse_continuity_table(
                runoff_match.group(1)
            )

        # Flow Routing Continuity
        flow_match = re.search(
            r"Flow Routing Continuity\s+acre-feet\s+10\^6 gal\s*\*+(.+?)(?=\n\s*\n\s*\*+)",
            content,
            re.DOTALL,
        )
        if flow_match:
            continuity["flow_routing"] = self._parse_continuity_table(
                flow_match.group(1)
            )

        return continuity

    def _parse_continuity_table(self, text: str) -> Dict[str, List[float]]:
        """Parse a continuity table with two columns of values."""
        data = {}
        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("-"):
                continue

            # Match lines like "Total Precipitation ......         8.176         6.655"
            match = re.match(r"([A-Za-z\s()%]+?)\s*\.+\s+([\d.-]+)\s+([\d.-]+)", line)
            if match:
                key = (
                    match.group(1)
                    .strip()
                    .lower()
                    .replace(" ", "_")
                    .replace("(", "")
                    .replace(")", "")
                    .replace("%", "percent")
                )
                values = [float(match.group(2)), float(match.group(3))]
                data[key] = values

        return data

    def _parse_subcatchment_runoff(self, content: str) -> List[Dict[str, Any]]:
        """Parse subcatchment runoff summary."""
        subcatchments = []

        section_match = re.search(
            r"Subcatchment Runoff Summary\s*\*+(.+?)(?=\n\s*\n\s*\*+)",
            content,
            re.DOTALL,
        )

        if section_match:
            section_text = section_match.group(1)
            lines = section_text.strip().split("\n")

            # Skip header lines
            data_started = False
            for line in lines:
                line = line.strip()
                if not line or line.startswith("-"):
                    continue
                # Header line starts with "Subcatchment" with values in the line
                if line.startswith("Subcatchment") and not (
                    "Precip" in line or "Runon" in line
                ):
                    data_started = True
                    continue
                if not data_started:
                    continue

                # Parse data lines
                parts = line.split()
                if len(parts) >= 10:
                    subcatchments.append(
                        {
                            "name": parts[0],
                            "total_precip": float(parts[1]),
                            "total_runon": float(parts[2]),
                            "total_evap": float(parts[3]),
                            "total_infil": float(parts[4]),
                            "imperv_runoff": float(parts[5]),
                            "perv_runoff": float(parts[6]),
                            "total_runoff": float(parts[7]),
                            "total_runoff_mgal": float(parts[8]),
                            "peak_runoff": float(parts[9]),
                            "runoff_coeff": (
                                float(parts[10]) if len(parts) > 10 else None
                            ),
                        }
                    )

        return subcatchments

    def _parse_node_depth(self, content: str) -> List[Dict[str, Any]]:
        """Parse node depth summary."""
        nodes = []

        section_match = re.search(
            r"Node Depth Summary\s*\*+(.+?)(?=\n\s*\n\s*\*+)", content, re.DOTALL
        )

        if section_match:
            section_text = section_match.group(1)
            lines = section_text.strip().split("\n")

            data_started = False
            for line in lines:
                line = line.strip()
                if not line or line.startswith("-"):
                    continue
                if "Node" in line and "Type" in line:
                    data_started = True
                    continue
                if not data_started:
                    continue

                parts = line.split()
                if len(parts) >= 7:
                    nodes.append(
                        {
                            "name": parts[0],
                            "type": parts[1],
                            "average_depth": float(parts[2]),
                            "maximum_depth": float(parts[3]),
                            "maximum_hgl": float(parts[4]),
                            "time_of_max_days": int(parts[5]),
                            "time_of_max": parts[6],
                            "reported_max_depth": (
                                float(parts[7]) if len(parts) > 7 else None
                            ),
                        }
                    )

        return nodes

    def _parse_node_inflow(self, content: str) -> List[Dict[str, Any]]:
        """Parse node inflow summary."""
        nodes = []

        section_match = re.search(
            r"Node Inflow Summary\s*\*+(.+?)(?=\n\s*\n\s*\*+)", content, re.DOTALL
        )

        if section_match:
            section_text = section_match.group(1)
            lines = section_text.strip().split("\n")

            data_started = False
            for line in lines:
                line = line.strip()
                if not line or line.startswith("-"):
                    continue
                if "Node" in line and "Type" in line:
                    data_started = True
                    continue
                if not data_started:
                    continue

                parts = line.split()
                if len(parts) >= 10:
                    nodes.append(
                        {
                            "name": parts[0],
                            "type": parts[1],
                            "maximum_lateral_inflow": float(parts[2]),
                            "maximum_total_inflow": float(parts[3]),
                            "time_of_max_days": int(parts[4]),
                            "time_of_max": parts[5],
                            "lateral_inflow_volume": float(parts[6]),
                            "total_inflow_volume": float(parts[7]),
                            "flow_balance_error": (
                                float(parts[8]) if len(parts) > 8 else None
                            ),
                        }
                    )

        return nodes

    def _parse_node_flooding(self, content: str) -> Optional[str]:
        """Parse node flooding summary."""
        section_match = re.search(
            r"Node Flooding Summary\s*\*+(.+?)(?=\n\s*\n\s*\*+)", content, re.DOTALL
        )

        if section_match:
            section_text = section_match.group(1).strip()
            if "No nodes were flooded" in section_text:
                return "No nodes were flooded"
            # Could parse flooding data here if needed

        return None

    def _parse_outfall_loading(self, content: str) -> List[Dict[str, Any]]:
        """Parse outfall loading summary."""
        outfalls = []

        section_match = re.search(
            r"Outfall Loading Summary\s*\*+(.+?)(?=\n\s*\n\s*\*+)", content, re.DOTALL
        )

        if section_match:
            section_text = section_match.group(1)
            lines = section_text.strip().split("\n")

            data_started = False
            for line in lines:
                line = line.strip()
                if not line or line.startswith("-"):
                    continue
                if "Outfall Node" in line:
                    data_started = True
                    continue
                if not data_started:
                    continue

                parts = line.split()
                if len(parts) >= 4 and parts[0] != "System":
                    outfall = {
                        "name": parts[0],
                        "flow_freq": float(parts[1]),
                        "avg_flow": float(parts[2]),
                        "max_flow": float(parts[3]),
                        "total_volume": float(parts[4]) if len(parts) > 4 else None,
                    }
                    # Add pollutant loads if present
                    if len(parts) > 5:
                        outfall["pollutant_loads"] = [float(p) for p in parts[5:]]
                    outfalls.append(outfall)

        return outfalls

    def _parse_link_flow(self, content: str) -> List[Dict[str, Any]]:
        """Parse link flow summary."""
        links = []

        section_match = re.search(
            r"Link Flow Summary\s*\*+(.+?)(?=\n\s*\n\s*\*+)", content, re.DOTALL
        )

        if section_match:
            section_text = section_match.group(1)
            lines = section_text.strip().split("\n")

            data_started = False
            for line in lines:
                line = line.strip()
                if not line or line.startswith("-"):
                    continue
                if "Link" in line and "Type" in line:
                    data_started = True
                    continue
                if not data_started:
                    continue

                parts = line.split()
                if len(parts) >= 8:
                    links.append(
                        {
                            "name": parts[0],
                            "type": parts[1],
                            "maximum_flow": float(parts[2]),
                            "time_of_max_days": int(parts[3]),
                            "time_of_max": parts[4],
                            "maximum_velocity": float(parts[5]),
                            "max_over_full_flow": (
                                float(parts[6]) if len(parts) > 6 else None
                            ),
                            "max_over_full_depth": (
                                float(parts[7]) if len(parts) > 7 else None
                            ),
                        }
                    )

        return links

    def _parse_conduit_surcharge(self, content: str) -> Optional[str]:
        """Parse conduit surcharge summary."""
        section_match = re.search(
            r"Conduit Surcharge Summary\s*\*+(.+?)(?=\n\s*\n\s*\*+)", content, re.DOTALL
        )

        if section_match:
            section_text = section_match.group(1).strip()
            if "No conduits were surcharged" in section_text:
                return "No conduits were surcharged"
            # Could parse surcharge data here if needed

        return None

    def _parse_analysis_time(self, content: str) -> Dict[str, str]:
        """Parse analysis time information."""
        time_info = {}

        begin_match = re.search(r"Analysis begun on:\s*(.+)", content)
        if begin_match:
            time_info["begun"] = begin_match.group(1).strip()

        end_match = re.search(r"Analysis ended on:\s*(.+)", content)
        if end_match:
            time_info["ended"] = end_match.group(1).strip()

        elapsed_match = re.search(r"Total elapsed time:\s*(.+)", content)
        if elapsed_match:
            time_info["elapsed"] = elapsed_match.group(1).strip()

        return time_info

    def _parse_pumping_summary(self, content: str) -> List[Dict[str, Any]]:
        """Parse pumping summary section."""
        pumps = []

        section_match = re.search(
            r"Pumping Summary\s*\*+.+?-+\s*(.+?)(?=\n\s*\n|\Z)", content, re.DOTALL
        )

        if not section_match:
            return pumps

        section_text = section_match.group(1).strip()
        lines = section_text.split("\n")

        for line in lines:
            line = line.strip()
            # Skip empty lines, separators, and any header-related lines
            if (
                not line
                or line.startswith("-")
                or "Pump" in line
                or "Percent" in line
                or "Number" in line
                or "Flow" in line
                or "Utilized" in line
                or "Min" in line
                or "Avg" in line
                or "Max" in line
                or "Total" in line
                or "Power" in line
                or "Time" in line
                or "Curve" in line
                or "Start-Ups" in line
            ):
                continue

            parts = line.split()
            if len(parts) >= 10:
                try:
                    pumps.append(
                        {
                            "pump_name": parts[0],
                            "percent_utilized": float(parts[1]),
                            "num_startups": int(parts[2]),
                            "min_flow": float(parts[3]),
                            "avg_flow": float(parts[4]),
                            "max_flow": float(parts[5]),
                            "total_volume": float(parts[6]),
                            "power_usage": float(parts[7]),
                            "pct_time_off_curve_low": float(parts[8]),
                            "pct_time_off_curve_high": float(parts[9]),
                        }
                    )
                except (ValueError, IndexError):
                    continue

        return pumps

    def _parse_storage_volume(self, content: str) -> List[Dict[str, Any]]:
        """Parse storage volume summary section."""
        storages = []

        section_match = re.search(
            r"Storage Volume Summary\s*\*+.+?-+\s*(.+?)(?=\n\s*\n\s*\*+|\Z)",
            content,
            re.DOTALL,
        )

        if not section_match:
            return storages

        section_text = section_match.group(1).strip()
        lines = section_text.split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("-") or "Storage Unit" in line:
                continue

            parts = line.split()
            if len(parts) >= 9:
                try:
                    storages.append(
                        {
                            "storage_unit": parts[0],
                            "avg_volume": float(parts[1]),
                            "avg_pct_full": float(parts[2]),
                            "evap_pct_loss": float(parts[3]),
                            "exfil_pct_loss": float(parts[4]),
                            "max_volume": float(parts[5]),
                            "max_pct_full": float(parts[6]),
                            "time_of_max_days": int(parts[7]),
                            "time_of_max": parts[8],
                            "max_outflow": float(parts[9]) if len(parts) > 9 else None,
                        }
                    )
                except (ValueError, IndexError):
                    continue

        return storages

    def _parse_node_surcharge(self, content: str) -> List[Dict[str, Any]]:
        """Parse node surcharge summary section."""
        nodes = []

        section_match = re.search(
            r"Node Surcharge Summary\s*\*+.+?-+\s*(.+?)(?=\n\s*\n\s*\*+|\Z)",
            content,
            re.DOTALL,
        )

        if not section_match:
            return nodes

        section_text = section_match.group(1).strip()
        lines = section_text.split("\n")

        for line in lines:
            line = line.strip()
            if (
                not line
                or line.startswith("-")
                or "Node" in line
                or "Surcharging occurs" in line
            ):
                continue

            parts = line.split()
            if len(parts) >= 5:
                try:
                    nodes.append(
                        {
                            "node_name": parts[0],
                            "node_type": parts[1],
                            "hours_surcharged": float(parts[2]),
                            "max_height_above_crown": float(parts[3]),
                            "min_depth_below_rim": float(parts[4]),
                        }
                    )
                except (ValueError, IndexError):
                    continue

        return nodes

    def _parse_lid_performance(self, content: str) -> List[Dict[str, Any]]:
        """Parse LID performance summary section."""
        lid_controls = []

        section_match = re.search(
            r"LID Performance Summary\s*\*+.+?-+\s*(.+?)(?=\n\s*\n\s*\*+|\Z)",
            content,
            re.DOTALL,
        )

        if not section_match:
            return lid_controls

        section_text = section_match.group(1).strip()
        lines = section_text.split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("-") or "Subcatchment" in line:
                continue

            parts = line.split()
            if len(parts) >= 10:
                try:
                    lid_controls.append(
                        {
                            "subcatchment": parts[0],
                            "lid_control": parts[1],
                            "total_inflow": float(parts[2]),
                            "evap_loss": float(parts[3]),
                            "infil_loss": float(parts[4]),
                            "surface_outflow": float(parts[5]),
                            "drain_outflow": float(parts[6]),
                            "initial_storage": float(parts[7]),
                            "final_storage": float(parts[8]),
                            "continuity_error_pct": float(parts[9]),
                        }
                    )
                except (ValueError, IndexError):
                    continue

        return lid_controls

    def _parse_groundwater_summary(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse groundwater continuity section."""
        gw_match = re.search(
            r"\*+\s*Groundwater Continuity\s*\*+\s*(.+?)(?=\n\s*\n\s*\*+|\Z)",
            content,
            re.DOTALL,
        )

        if not gw_match:
            return None

        section_text = gw_match.group(1).strip()
        gw_data = {}

        # Parse groundwater data
        for line in section_text.split("\n"):
            if "......" in line or "....." in line:
                parts = line.split()
                if len(parts) >= 2:
                    key = "_".join(parts[:-2]).lower().replace(".", "")
                    try:
                        gw_data[key] = float(parts[-2])
                    except ValueError:
                        gw_data[key] = parts[-2]

        return gw_data if gw_data else None

    def _parse_quality_routing_continuity(
        self, content: str
    ) -> Optional[Dict[str, Any]]:
        """Parse quality routing continuity section."""
        qr_match = re.search(
            r"\*+\s*Quality Routing Continuity\s*\*+\s*(.+?)(?=\n\s*\n\s*\*+|\Z)",
            content,
            re.DOTALL,
        )

        if not qr_match:
            return None

        section_text = qr_match.group(1).strip()
        qr_data = {}

        # Parse quality routing data
        for line in section_text.split("\n"):
            if "......" in line or "....." in line:
                parts = line.split()
                if len(parts) >= 2:
                    key = "_".join(parts[:-2]).lower().replace(".", "")
                    try:
                        qr_data[key] = float(parts[-2])
                    except ValueError:
                        qr_data[key] = parts[-2]

        return qr_data if qr_data else None

    def _parse_subcatchment_washoff(self, content: str) -> List[Dict[str, Any]]:
        """Parse subcatchment washoff summary section."""
        washoffs = []

        section_match = re.search(
            r"Subcatchment Washoff Summary\s*\*+.+?-+\s*(.+?)(?=\n\s*\n\s*\*+|\Z)",
            content,
            re.DOTALL,
        )

        if not section_match:
            return washoffs

        section_text = section_match.group(1).strip()
        lines = section_text.split("\n")

        # Parse washoff data - structure varies by pollutants present
        # This is a simplified parser
        for line in lines:
            line = line.strip()
            if not line or line.startswith("-") or "Subcatchment" in line:
                continue

            parts = line.split()
            if len(parts) >= 2:
                washoffs.append({"subcatchment": parts[0], "data": parts[1:]})

        return washoffs

    def _parse_link_pollutant_load(self, content: str) -> List[Dict[str, Any]]:
        """Parse link pollutant load summary section."""
        loads = []

        section_match = re.search(
            r"Link Pollutant Load Summary\s*\*+.+?-+\s*(.+?)(?=\n\s*\n\s*\*+|\Z)",
            content,
            re.DOTALL,
        )

        if not section_match:
            return loads

        section_text = section_match.group(1).strip()
        lines = section_text.split("\n")

        # Parse load data - structure varies by pollutants present
        for line in lines:
            line = line.strip()
            if not line or line.startswith("-") or "Link" in line:
                continue

            parts = line.split()
            if len(parts) >= 2:
                loads.append({"link": parts[0], "data": parts[1:]})

        return loads

    def _parse_flow_classification(self, content: str) -> List[Dict[str, Any]]:
        """Parse flow classification summary section."""
        classifications = []

        section_match = re.search(
            r"Flow Classification Summary\s*\*+.+?-+\s*(.+?)(?=\n\s*\n\s*\*+|\Z)",
            content,
            re.DOTALL,
        )

        if not section_match:
            return classifications

        section_text = section_match.group(1).strip()
        lines = section_text.split("\n")

        for line in lines:
            line = line.strip()
            if (
                not line
                or line.startswith("-")
                or "Conduit" in line
                or "Adjusted" in line
                or "Fraction of Time" in line
            ):
                continue

            parts = line.split()
            if len(parts) >= 5:
                try:
                    classifications.append(
                        {
                            "conduit": parts[0],
                            "dry": float(parts[1]),
                            "up_dry": float(parts[2]) if len(parts) > 2 else None,
                            "down_dry": float(parts[3]) if len(parts) > 3 else None,
                            "sub_crit": float(parts[4]) if len(parts) > 4 else None,
                            "sup_crit": float(parts[5]) if len(parts) > 5 else None,
                            "up_crit": float(parts[6]) if len(parts) > 6 else None,
                            "down_crit": float(parts[7]) if len(parts) > 7 else None,
                            "norm_ltd": float(parts[8]) if len(parts) > 8 else None,
                            "inlet_ctrl": float(parts[9]) if len(parts) > 9 else None,
                        }
                    )
                except (ValueError, IndexError):
                    continue

        return classifications
