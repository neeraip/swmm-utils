"""
SWMM Output File Decoder

This module provides functionality to decode SWMM .out (binary output) files
into structured data. The .out files contain time series results from SWMM
simulations including flows, depths, volumes, etc.
"""

import struct
from collections.abc import Mapping
from pathlib import Path
from typing import Dict, Any, Iterator, List, Union
from datetime import datetime, timedelta

import numpy as np


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
        self, filepath: Union[str, Path], include_time_series: bool = False
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

            # Optionally read time series data.
            #
            # The results block is read in one go into a numpy array and
            # kept as per-role views of it (see ``_read_time_series_arrays``).
            # ``time_series`` is the same data in the dict-of-lists shape
            # earlier versions built eagerly, now assembled per element on
            # access: building it for every element up front is what took a
            # 278 MB output past 8 GB of RAM and got the producer killed.
            time_series = None
            time_series_arrays = None
            if include_time_series:
                time_series_arrays = self._read_time_series_arrays(
                    f, header, metadata
                )
                time_series = TimeSeriesRecords(
                    time_series_arrays, metadata["labels"], time_index
                )

            return {
                "header": header,
                "metadata": metadata,
                "time_index": time_index,
                "time_series": time_series,
                "time_series_arrays": time_series_arrays,
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

    def _read_time_series_arrays(
        self,
        f,
        header: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Dict[str, np.ndarray]:
        """
        Read every reporting period's values as numpy arrays.

        One ``np.fromfile`` over the results block, then views per role:

            subcatchments  (n_periods, n_subcatchments, n_subcatch_vars)
            nodes          (n_periods, n_nodes, n_node_vars)
            links          (n_periods, n_links, n_link_vars)
            system         (n_periods, n_system_vars)

        All float32, all views of one buffer — the file's own size in RAM
        and nothing more. The previous reader unpacked each value with
        ``struct`` into a dict per element per period, which for a large
        network is gigabytes of Python objects for a few hundred megabytes
        of floats.

        A file cut short (a run that stopped early) yields NaN for the
        periods that are missing rather than zeros, so "no value" cannot be
        mistaken for a dry pipe.
        """
        n_subcatch = header["n_subcatchments"]
        n_nodes = header["n_nodes"]
        n_links = header["n_links"]
        n_periods = metadata["n_periods"]

        n_subcatch_vars = metadata["variables"]["subcatchment"]
        n_node_vars = metadata["variables"]["node"]
        n_link_vars = metadata["variables"]["link"]
        n_system_vars = metadata["variables"]["system"]

        n_values = (
            n_subcatch * n_subcatch_vars
            + n_nodes * n_node_vars
            + n_links * n_link_vars
            + n_system_vars
        )
        # Each record: an 8-byte timestamp (double) followed by the values.
        record_dtype = np.dtype([("t", "<f8"), ("v", "<f4", (n_values,))])

        # Where the records start, from the footer; how many the file
        # actually holds, from its size.
        f.seek(0, 2)
        file_size = f.tell()
        f.seek(-6 * self._RECORD_SIZE, 2)
        footer = self._read_n_ints(f, 6)
        results_pos = footer[2]
        available = max(0, (file_size - results_pos - 6 * self._RECORD_SIZE))
        count = min(n_periods, available // record_dtype.itemsize) if n_values else 0

        if count > 0:
            f.seek(results_pos)
            records = np.fromfile(f, dtype=record_dtype, count=count)
            values = records["v"]
        else:
            values = np.empty((0, n_values), dtype="<f4")

        if values.shape[0] < n_periods:
            padded = np.full((n_periods, n_values), np.nan, dtype="<f4")
            padded[: values.shape[0]] = values
            values = padded

        offset = 0
        arrays: Dict[str, np.ndarray] = {}
        for role, count_elements, n_vars in (
            ("subcatchments", n_subcatch, n_subcatch_vars),
            ("nodes", n_nodes, n_node_vars),
            ("links", n_links, n_link_vars),
        ):
            width = count_elements * n_vars
            arrays[role] = values[:, offset : offset + width].reshape(
                n_periods, count_elements, n_vars
            )
            offset += width
        arrays["system"] = values[:, offset : offset + n_system_vars]
        return arrays

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
        # Each type has: count (int) followed by count variable codes (ints)
        num_subcatch_vars = self._read_int(f)
        subcatch_var_codes = self._read_n_ints(f, num_subcatch_vars)

        num_node_vars = self._read_int(f)
        node_var_codes = self._read_n_ints(f, num_node_vars)

        num_link_vars = self._read_int(f)
        link_var_codes = self._read_n_ints(f, num_link_vars)

        num_system_vars = self._read_int(f)
        system_var_codes = self._read_n_ints(f, num_system_vars)

        variables = {
            "subcatchment": num_subcatch_vars,
            "node": num_node_vars,
            "link": num_link_vars,
            "system": num_system_vars,
        }

        variable_codes = {
            "subcatchment": subcatch_var_codes,
            "node": node_var_codes,
            "link": link_var_codes,
            "system": system_var_codes,
        }

        # Read start date/time and time step info
        # Start date is stored as Excel serial date (double, days since 1899-12-30)
        start_date_double = self._read_double(f)
        start_date = self._excel_date_to_datetime(start_date_double)
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
            "variable_codes": variable_codes,
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

    def _excel_date_to_datetime(self, excel_date: float) -> datetime:
        """Convert Excel serial date to Python datetime.

        Excel serial dates are days since 1899-12-30.
        """
        try:
            base = datetime(1899, 12, 30)
            return base + timedelta(days=excel_date)
        except (ValueError, OverflowError):
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



class TimeSeriesRecords(Mapping):
    """
    The time series in the shape earlier versions returned, built on demand.

    ``data["time_series"]`` used to be ``{"nodes": {label: [{"timestamp",
    "values"}, …]}, …}``, assembled eagerly for every element. This is the
    same mapping — ``ts["nodes"]["J1"]`` gives the same list of records —
    but a list is built only for the element asked for, from the arrays.
    ``to_dict()`` builds all of it, for the JSON export that needs it.
    """

    ROLES = ("subcatchments", "nodes", "links", "system")

    def __init__(
        self,
        arrays: Dict[str, np.ndarray],
        labels: Dict[str, List[str]],
        time_index: List[datetime],
    ):
        self._arrays = arrays
        self._labels = {
            "subcatchments": list(labels.get("subcatchment", [])),
            "nodes": list(labels.get("node", [])),
            "links": list(labels.get("link", [])),
        }
        self._stamps = [t.isoformat() for t in time_index]

    def __getitem__(self, role: str):
        if role == "system":
            return _records(self._arrays["system"], self._stamps)
        if role not in self._labels:
            raise KeyError(role)
        return _RoleRecords(self._arrays[role], self._labels[role], self._stamps)

    def __iter__(self) -> Iterator[str]:
        return iter(self.ROLES)

    def __len__(self) -> int:
        return len(self.ROLES)

    def to_dict(self) -> Dict[str, Any]:
        """Every element's records, materialised. Large for a large run."""
        return {
            role: (self[role] if role == "system" else dict(self[role].items()))
            for role in self.ROLES
        }


class _RoleRecords(Mapping):
    """One role's ``{label: [records]}``, each list built when asked for."""

    def __init__(self, array: np.ndarray, labels: List[str], stamps: List[str]):
        self._array = array
        self._labels = labels
        self._index = {label: i for i, label in enumerate(labels)}
        self._stamps = stamps

    def __getitem__(self, label: str) -> List[Dict[str, Any]]:
        i = self._index[label]
        return _records(self._array[:, i, :], self._stamps)

    def __iter__(self) -> Iterator[str]:
        return iter(self._labels)

    def __len__(self) -> int:
        return len(self._labels)

    def __contains__(self, label: object) -> bool:
        return label in self._index


def _records(rows: np.ndarray, stamps: List[str]) -> List[Dict[str, Any]]:
    values = rows.astype("float64").tolist()
    return [
        {"timestamp": stamp, "values": row}
        for stamp, row in zip(stamps, values)
    ]
