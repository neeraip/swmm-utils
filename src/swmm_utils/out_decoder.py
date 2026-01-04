"""
SWMM Output File Decoder

This module provides functionality to decode SWMM .out (binary output) files
into structured data. The .out files contain time series results from SWMM
simulations including flows, depths, volumes, etc.
"""

import struct
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta


class SwmmOutputDecoder:
    """Decoder for SWMM output (.out) binary files."""

    # Binary file constants
    _MAGIC_NUMBER = 516114522  # 0x1EAE682A in hex
    _RECORD_SIZE = 4  # 4 bytes per record
    _FLOW_UNITS = ["CFS", "GPM", "MGD", "CMS", "LPS", "MLD"]
    _CONCENTRATION_UNITS = ["MG", "UG", "COUNTS"]
    _NODE_TYPES = ["JUNCTION", "OUTFALL", "STORAGE", "DIVIDER"]
    _LINK_TYPES = ["CONDUIT", "PUMP", "ORIFICE", "WEIR", "OUTLET"]
    _PROPERTY_LABELS = ["type", "area", "invert", "max_depth", "offset", "length"]

    def decode_file(
        self, filepath: str | Path, include_time_series: bool = False
    ) -> Dict[str, Any]:
        """
        Decode a SWMM output (.out) binary file.

        Args:
            filepath: Path to the .out file
            include_time_series: Whether to read and include time series data (default False)
                               Setting to True reads all time series records which can be memory-intensive
                               for large simulations

        Returns:
            Dictionary containing parsed output data with metadata, time index, and
            optionally time series data
        """
        filepath = Path(filepath)

        with open(filepath, "rb") as f:
            # Read header and metadata
            header = self._parse_header(f)
            metadata = self._parse_metadata(f, header)

            # Create time index
            time_index = self._create_time_index(
                metadata["start_date"],
                metadata["report_interval"],
                metadata["n_periods"],
            )

            # Optionally read time series data
            time_series = None
            if include_time_series:
                time_series = self._read_time_series_data(
                    f, header, metadata, time_index
                )

            return {
                "header": header,
                "metadata": metadata,
                "time_index": time_index,
                "time_series": time_series,
                "filepath": str(filepath),
            }

    def _parse_header(self, f) -> Dict[str, Any]:
        """Parse the binary file header."""
        # Read magic number at start
        f.seek(0)
        magic_start = self._read_int(f)
        if magic_start != self._MAGIC_NUMBER:
            raise ValueError("Invalid .out file: magic number mismatch at start")

        # Read version and flow unit info
        swmm_version = self._read_int(f)
        flow_unit_code = self._read_int(f)
        n_subcatch = self._read_int(f)
        n_nodes = self._read_int(f)
        n_links = self._read_int(f)
        n_pollutants = self._read_int(f)

        # Convert flow unit code to string
        flow_unit = (
            self._FLOW_UNITS[flow_unit_code]
            if flow_unit_code < len(self._FLOW_UNITS)
            else "UNKNOWN"
        )

        return {
            "magic_start": magic_start,
            "version": swmm_version,
            "version_str": f"{swmm_version // 10000}.{(swmm_version // 100) % 100}.{swmm_version % 100}",
            "flow_unit": flow_unit,
            "flow_unit_code": flow_unit_code,
            "n_subcatchments": n_subcatch,
            "n_nodes": n_nodes,
            "n_links": n_links,
            "n_pollutants": n_pollutants,
        }

    def _read_time_series_data(
        self,
        f,
        header: Dict[str, Any],
        metadata: Dict[str, Any],
        time_index: List[datetime],
    ) -> Dict[str, Any]:
        """
        Read time series data records from the binary file.

        This method reads all the 4-byte record values for each time step.
        Returns organized by element type and time step.

        Args:
            f: File handle positioned after metadata
            header: Parsed header information
            metadata: Parsed metadata information
            time_index: List of timestamps

        Returns:
            Dictionary with time series data organized by element type
        """
        n_subcatch = header["n_subcatchments"]
        n_nodes = header["n_nodes"]
        n_links = header["n_links"]
        n_periods = metadata["n_periods"]

        n_subcatch_vars = metadata["variables"]["subcatchment"]
        n_node_vars = metadata["variables"]["node"]
        n_link_vars = metadata["variables"]["link"]
        n_system_vars = metadata["variables"]["system"]

        # Calculate total record size in bytes
        record_size = (
            n_subcatch * n_subcatch_vars
            + n_nodes * n_node_vars
            + n_links * n_link_vars
            + n_system_vars
        ) * 4

        # Find the start of time series data
        # It's after the metadata section, which we've already read past
        current_pos = f.tell()

        # Initialize storage for time series
        time_series = {
            "subcatchments": {},
            "nodes": {},
            "links": {},
            "system": [],
        }

        # Initialize nested structures for each element
        for subcatch_label in metadata["labels"]["subcatchment"]:
            time_series["subcatchments"][subcatch_label] = []

        for node_label in metadata["labels"]["node"]:
            time_series["nodes"][node_label] = []

        for link_label in metadata["labels"]["link"]:
            time_series["links"][link_label] = []

        # Read all time step records
        for period in range(n_periods):
            f.seek(current_pos + period * record_size)

            # Read subcatchment data
            for subcatch_label in metadata["labels"]["subcatchment"]:
                values = [self._read_float(f) for _ in range(n_subcatch_vars)]
                time_series["subcatchments"][subcatch_label].append(
                    {
                        "timestamp": time_index[period].isoformat(),
                        "values": values,
                    }
                )

            # Read node data
            for node_label in metadata["labels"]["node"]:
                values = [self._read_float(f) for _ in range(n_node_vars)]
                time_series["nodes"][node_label].append(
                    {
                        "timestamp": time_index[period].isoformat(),
                        "values": values,
                    }
                )

            # Read link data
            for link_label in metadata["labels"]["link"]:
                values = [self._read_float(f) for _ in range(n_link_vars)]
                time_series["links"][link_label].append(
                    {
                        "timestamp": time_index[period].isoformat(),
                        "values": values,
                    }
                )

            # Read system data
            system_values = [self._read_float(f) for _ in range(n_system_vars)]
            time_series["system"].append(
                {
                    "timestamp": time_index[period].isoformat(),
                    "values": system_values,
                }
            )

        return time_series

    def _parse_metadata(self, f, header: Dict[str, Any]) -> Dict[str, Any]:
        """Parse metadata section (labels, properties, etc.)."""
        # Read labels for each object type
        labels = {
            "subcatchment": self._read_string_array(f, header["n_subcatchments"]),
            "node": self._read_string_array(f, header["n_nodes"]),
            "link": self._read_string_array(f, header["n_links"]),
            "pollutant": self._read_string_array(f, header["n_pollutants"]),
        }

        # Read pollutant units
        pollutant_units = {}
        for i in range(header["n_pollutants"]):
            unit_code = self._read_int(f)
            unit_str = (
                self._CONCENTRATION_UNITS[unit_code]
                if unit_code < len(self._CONCENTRATION_UNITS)
                else "UNKNOWN"
            )
            if i < len(labels["pollutant"]):
                pollutant_units[labels["pollutant"][i]] = unit_str

        # Read properties for objects
        properties = {}
        properties["subcatchment"] = self._read_object_properties(
            f, header["n_subcatchments"], "subcatchment", labels["subcatchment"]
        )
        properties["node"] = self._read_object_properties(
            f, header["n_nodes"], "node", labels["node"]
        )
        properties["link"] = self._read_object_properties(
            f, header["n_links"], "link", labels["link"]
        )

        # Read number of variables for each object type
        variables = {
            "subcatchment": self._read_int(f),
            "node": self._read_int(f),
            "link": self._read_int(f),
            "system": self._read_int(f),
        }

        # Read start date/time and time step info
        start_date = self._read_datetime(f)
        report_interval_seconds = self._read_int(f)
        report_interval = timedelta(seconds=report_interval_seconds)

        # Seek to end of file to read footer
        f.seek(-6 * self._RECORD_SIZE, 2)  # 6 integers at end
        footer = self._read_n_ints(f, 6)
        n_periods = footer[3]

        return {
            "labels": labels,
            "properties": properties,
            "pollutant_units": pollutant_units,
            "variables": variables,
            "start_date": start_date,
            "report_interval": report_interval,
            "report_interval_seconds": report_interval_seconds,
            "n_periods": n_periods,
        }

    def _read_object_properties(
        self, f, _n_objects: int, obj_type: str, labels: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Read properties for objects (type, area, invert, max_depth, etc.)."""
        properties = {}

        # Read number of properties
        n_props = self._read_int(f)

        # Read property codes
        prop_codes = []
        for _ in range(n_props):
            prop_code = self._read_int(f)
            if prop_code < len(self._PROPERTY_LABELS):
                prop_codes.append(self._PROPERTY_LABELS[prop_code])
            else:
                prop_codes.append(f"property_{prop_code}")

        # Read property values for each object
        for label in labels:
            properties[label] = {}
            for prop_name in prop_codes:
                if prop_name == "type":
                    type_code = self._read_int(f)
                    if obj_type == "node":
                        properties[label][prop_name] = (
                            self._NODE_TYPES[type_code]
                            if type_code < len(self._NODE_TYPES)
                            else f"UNKNOWN_{type_code}"
                        )
                    elif obj_type == "link":
                        properties[label][prop_name] = (
                            self._LINK_TYPES[type_code]
                            if type_code < len(self._LINK_TYPES)
                            else f"UNKNOWN_{type_code}"
                        )
                else:
                    properties[label][prop_name] = self._read_float(f)

        return properties

    def _read_string_array(self, f, n_strings: int) -> List[str]:
        """Read an array of null-terminated strings."""
        strings = []
        for _ in range(n_strings):
            # Read string length
            length = self._read_int(f)
            # Read string bytes
            if length > 0:
                string_bytes = f.read(length)
                string = string_bytes.decode("utf-8", errors="replace").rstrip("\x00")
                strings.append(string)
            else:
                strings.append("")
        return strings

    def _read_datetime(self, f) -> datetime:
        """Read a date/time value (5 integers: year, month, day, hour, minute)."""
        year = self._read_int(f)
        month = self._read_int(f)
        day = self._read_int(f)
        hour = self._read_int(f)
        minute = self._read_int(f)

        try:
            return datetime(year, month, day, hour, minute)
        except ValueError:
            return datetime(2000, 1, 1, 0, 0)  # Default if invalid

    def _create_time_index(
        self, start_date: datetime, interval: timedelta, n_periods: int
    ) -> List[datetime]:
        """Create a list of datetime values for the time series."""
        return [start_date + interval * i for i in range(n_periods)]

    def _read_int(self, f) -> int:
        """Read a 4-byte integer from the file."""
        data = f.read(4)
        if len(data) < 4:
            return 0
        return struct.unpack("<i", data)[0]

    def _read_n_ints(self, f, n: int) -> List[int]:
        """Read n 4-byte integers from the file."""
        return [self._read_int(f) for _ in range(n)]

    def _read_float(self, f) -> float:
        """Read a 4-byte float from the file."""
        data = f.read(4)
        if len(data) < 4:
            return 0.0
        return struct.unpack("<f", data)[0]

    def _read_double(self, f) -> float:
        """Read an 8-byte double from the file."""
        data = f.read(8)
        if len(data) < 8:
            return 0.0
        return struct.unpack("<d", data)[0]
