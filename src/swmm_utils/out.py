"""
SWMM Output File (.out) Interface

This module provides a high-level interface for accessing SWMM output file data.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .out_decoder import SwmmOutputDecoder


class SwmmOutput:
    """High-level interface for SWMM output (.out) files."""

    def __init__(self, filepath: str | Path, load_time_series: bool = False):
        """
        Initialize SWMM output file reader.

        Args:
            filepath: Path to the .out file
            load_time_series: If True, loads all time series data into memory.
                            This enables to_json() to include all timestep data,
                            but requires more memory and processing time.
                            Default is False (only metadata loaded).
        """
        self.filepath = Path(filepath)
        self.decoder = SwmmOutputDecoder()
        self.load_time_series = load_time_series

        # Decode the file with specified settings
        self._data = self.decoder.decode_file(
            self.filepath, include_time_series=load_time_series
        )

    @property
    def version(self) -> str:
        """Get SWMM version string."""
        return self._data["header"]["version_str"]

    @property
    def flow_unit(self) -> str:
        """Get flow unit (CFS, GPM, LPS, etc.)."""
        return self._data["header"]["flow_unit"]

    @property
    def start_date(self) -> datetime:
        """Get simulation start date/time."""
        return self._data["metadata"]["start_date"]

    @property
    def end_date(self) -> datetime:
        """Get simulation end date/time."""
        if self.n_periods > 0:
            return self.start_date + self.report_interval * (self.n_periods - 1)
        return self.start_date

    @property
    def report_interval(self) -> timedelta:
        """Get reporting time interval."""
        return self._data["metadata"]["report_interval"]

    @property
    def n_periods(self) -> int:
        """Get number of reporting periods (time steps)."""
        return self._data["metadata"]["n_periods"]

    @property
    def time_index(self) -> List[datetime]:
        """Get list of all time steps."""
        return self._data["time_index"]

    @property
    def n_subcatchments(self) -> int:
        """Get number of subcatchments in model."""
        return self._data["header"]["n_subcatchments"]

    @property
    def n_nodes(self) -> int:
        """Get number of nodes in model."""
        return self._data["header"]["n_nodes"]

    @property
    def n_links(self) -> int:
        """Get number of links in model."""
        return self._data["header"]["n_links"]

    @property
    def n_pollutants(self) -> int:
        """Get number of pollutants in model."""
        return self._data["header"]["n_pollutants"]

    @property
    def subcatchment_labels(self) -> List[str]:
        """Get list of subcatchment names/IDs."""
        return self._data["metadata"]["labels"]["subcatchment"]

    @property
    def node_labels(self) -> List[str]:
        """Get list of node names/IDs."""
        return self._data["metadata"]["labels"]["node"]

    @property
    def link_labels(self) -> List[str]:
        """Get list of link names/IDs."""
        return self._data["metadata"]["labels"]["link"]

    @property
    def pollutant_labels(self) -> List[str]:
        """Get list of pollutant names."""
        return self._data["metadata"]["labels"]["pollutant"]

    @property
    def pollutant_units(self) -> Dict[str, str]:
        """Get units for each pollutant (MG, UG, COUNTS)."""
        return self._data["metadata"]["pollutant_units"]

    @property
    def node_properties(self) -> Dict[str, Dict[str, Any]]:
        """Get properties for each node (type, invert, max_depth)."""
        return self._data["metadata"]["properties"]["node"]

    @property
    def link_properties(self) -> Dict[str, Dict[str, Any]]:
        """Get properties for each link (type, offsets, length)."""
        return self._data["metadata"]["properties"]["link"]

    @property
    def subcatchment_properties(self) -> Dict[str, Dict[str, Any]]:
        """Get properties for each subcatchment (area)."""
        return self._data["metadata"]["properties"]["subcatchment"]

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific node.

        Args:
            node_id: Node name/ID

        Returns:
            Dictionary with node properties or None if not found
        """
        if node_id in self.node_properties:
            return {"id": node_id, **self.node_properties[node_id]}
        return None

    def get_link(self, link_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific link.

        Args:
            link_id: Link name/ID

        Returns:
            Dictionary with link properties or None if not found
        """
        if link_id in self.link_properties:
            return {"id": link_id, **self.link_properties[link_id]}
        return None

    def get_subcatchment(self, subcatch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific subcatchment.

        Args:
            subcatch_id: Subcatchment name/ID

        Returns:
            Dictionary with subcatchment properties or None if not found
        """
        if subcatch_id in self.subcatchment_properties:
            return {"id": subcatch_id, **self.subcatchment_properties[subcatch_id]}
        return None

    def summary(self) -> Dict[str, Any]:
        """Get a summary of the output file contents."""
        return {
            "version": self.version,
            "flow_unit": self.flow_unit,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "duration": str(self.end_date - self.start_date),
            "report_interval": str(self.report_interval),
            "n_periods": self.n_periods,
            "n_subcatchments": self.n_subcatchments,
            "n_nodes": self.n_nodes,
            "n_links": self.n_links,
            "n_pollutants": self.n_pollutants,
            "pollutants": self.pollutant_labels,
        }

    def to_json(
        self,
        filepath: str | Path,
        pretty: bool = True,
    ) -> None:
        """
        Export output file data to JSON format.

        Exports all data that was loaded during initialization.
        If initialized with load_time_series=False (default), exports only metadata.
        If initialized with load_time_series=True, exports metadata and all time series data.

        Args:
            filepath: Path where JSON file will be saved
            pretty: Whether to pretty-print JSON (default True)
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        output_data = {
            "header": self._data["header"],
            "metadata": {
                "labels": self._data["metadata"]["labels"],
                "pollutant_units": self._data["metadata"]["pollutant_units"],
                "properties": self._data["metadata"]["properties"],
                "variables": self._data["metadata"]["variables"],
                "start_date": self._data["metadata"]["start_date"].isoformat(),
                "report_interval_seconds": self._data["metadata"][
                    "report_interval_seconds"
                ],
                "n_periods": self._data["metadata"]["n_periods"],
            },
            "summary": self.summary(),
        }

        # Add time series if it was loaded
        if self._data.get("time_series") is not None:
            output_data["time_series"] = self._data["time_series"]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                output_data,
                f,
                indent=2 if pretty else None,
                ensure_ascii=False,
            )

    def to_parquet(
        self, filepath: str | Path | None = None, single_file: bool = True
    ) -> None:
        """
        Export output file metadata to Parquet format.

        Args:
            filepath: Path where Parquet file will be saved. If single_file=False,
                     this is treated as a directory path.
            single_file: Whether to save as single file (True) or multiple files (False).
                        If False, creates separate parquet files for each data type.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for Parquet export. Install with: pip install pandas"
            )

        try:
            import pyarrow  # noqa: F401
        except ImportError:
            raise ImportError(
                "pyarrow is required for Parquet export. Install with: pip install pyarrow"
            )

        if single_file:
            # Export all metadata as a single parquet file
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Create a summary dataframe
            summary_data = []
            summary = self.summary()

            for key, value in summary.items():
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                summary_data.append({"field": key, "value": str(value)})

            df = pd.DataFrame(summary_data)
            df.to_parquet(filepath, index=False)

        else:
            # Export as multiple parquet files in a directory
            dirpath = Path(filepath)
            dirpath.mkdir(parents=True, exist_ok=True)

            # Export nodes
            if self.node_labels:
                nodes_data = []
                for node_id in self.node_labels:
                    node = self.get_node(node_id)
                    if node:
                        nodes_data.append(node)
                if nodes_data:
                    df_nodes = pd.DataFrame(nodes_data)
                    df_nodes.to_parquet(dirpath / "nodes.parquet", index=False)

            # Export links
            if self.link_labels:
                links_data = []
                for link_id in self.link_labels:
                    link = self.get_link(link_id)
                    if link:
                        links_data.append(link)
                if links_data:
                    df_links = pd.DataFrame(links_data)
                    df_links.to_parquet(dirpath / "links.parquet", index=False)

            # Export subcatchments
            if self.subcatchment_labels:
                subcatch_data = []
                for subcatch_id in self.subcatchment_labels:
                    subcatch = self.get_subcatchment(subcatch_id)
                    if subcatch:
                        subcatch_data.append(subcatch)
                if subcatch_data:
                    df_subcatch = pd.DataFrame(subcatch_data)
                    df_subcatch.to_parquet(
                        dirpath / "subcatchments.parquet", index=False
                    )

            # Export summary
            summary = self.summary()
            summary_data = []
            for key, value in summary.items():
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                summary_data.append({"field": key, "value": str(value)})

            df_summary = pd.DataFrame(summary_data)
            df_summary.to_parquet(dirpath / "summary.parquet", index=False)
