"""
SWMM Report Interface

This module provides a high-level interface for working with SWMM report (.rpt) files.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from .rpt_decoder import SwmmReportDecoder


class SwmmReport:
    """
    High-level interface for SWMM report files.

    Provides read-only access to SWMM simulation report data.

    Example:
        >>> with SwmmReport("model.rpt") as report:
        ...     print(report.header)
        ...     print(f"Number of nodes: {report.element_count.get('nodes', 0)}")
        ...     for node in report.node_depth:
        ...         print(f"{node['name']}: {node['maximum_depth']} ft")
    """

    def __init__(self, filepath: Optional[str | Path] = None):
        """
        Initialize SwmmReport.

        Args:
            filepath: Path to the .rpt file to load (optional)
        """
        self._data: Dict[str, Any] = {}
        self._decoder = SwmmReportDecoder()

        if filepath:
            self.load(filepath)

    def load(self, filepath: str | Path) -> None:
        """
        Load a SWMM report file.

        Args:
            filepath: Path to the .rpt file
        """
        filepath = Path(filepath)

        if filepath.suffix.lower() != ".rpt":
            raise ValueError(f"Expected .rpt file, got: {filepath.suffix}")

        if not filepath.exists():
            raise FileNotFoundError(f"Report file not found: {filepath}")

        self._data = self._decoder.decode_file(filepath)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        return False

    @property
    def header(self) -> Dict[str, str]:
        """Get report header information (version, build, title)."""
        return self._data.get("header", {})

    @property
    def element_count(self) -> Dict[str, int]:
        """Get element count summary."""
        return self._data.get("element_count", {})

    @property
    def analysis_options(self) -> Dict[str, Any]:
        """Get analysis options."""
        return self._data.get("analysis_options", {})

    @property
    def continuity(self) -> Dict[str, Any]:
        """Get continuity summaries (runoff, flow routing, quality)."""
        return self._data.get("continuity", {})

    @property
    def subcatchment_runoff(self) -> List[Dict[str, Any]]:
        """Get subcatchment runoff summary."""
        return self._data.get("subcatchment_runoff", [])

    @property
    def node_depth(self) -> List[Dict[str, Any]]:
        """Get node depth summary."""
        return self._data.get("node_depth", [])

    @property
    def node_inflow(self) -> List[Dict[str, Any]]:
        """Get node inflow summary."""
        return self._data.get("node_inflow", [])

    @property
    def node_flooding(self) -> Optional[str]:
        """Get node flooding summary."""
        return self._data.get("node_flooding")

    @property
    def outfall_loading(self) -> List[Dict[str, Any]]:
        """Get outfall loading summary."""
        return self._data.get("outfall_loading", [])

    @property
    def link_flow(self) -> List[Dict[str, Any]]:
        """Get link flow summary."""
        return self._data.get("link_flow", [])

    @property
    def conduit_surcharge(self) -> Optional[str]:
        """Get conduit surcharge summary."""
        return self._data.get("conduit_surcharge")

    @property
    def node_surcharge(self) -> List[Dict[str, Any]]:
        """Get node surcharge summary."""
        return self._data.get("node_surcharge", [])

    @property
    def storage_volume(self) -> List[Dict[str, Any]]:
        """Get storage volume summary."""
        return self._data.get("storage_volume", [])

    @property
    def pumping_summary(self) -> List[Dict[str, Any]]:
        """Get pumping summary."""
        return self._data.get("pumping_summary", [])

    @property
    def lid_performance(self) -> List[Dict[str, Any]]:
        """Get LID performance summary."""
        return self._data.get("lid_performance", [])

    @property
    def flow_classification(self) -> List[Dict[str, Any]]:
        """Get flow classification summary."""
        return self._data.get("flow_classification", [])

    @property
    def groundwater_summary(self) -> Optional[Dict[str, Any]]:
        """Get groundwater continuity summary."""
        return self._data.get("groundwater_summary")

    @property
    def quality_routing_continuity(self) -> Optional[Dict[str, Any]]:
        """Get quality routing continuity summary."""
        return self._data.get("quality_routing_continuity")

    @property
    def subcatchment_washoff(self) -> List[Dict[str, Any]]:
        """Get subcatchment washoff summary."""
        return self._data.get("subcatchment_washoff", [])

    @property
    def link_pollutant_load(self) -> List[Dict[str, Any]]:
        """Get link pollutant load summary."""
        return self._data.get("link_pollutant_load", [])

    @property
    def analysis_time(self) -> Dict[str, str]:
        """Get analysis time information."""
        return self._data.get("analysis_time", {})

    def get_node_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get node information by name from depth or inflow summaries.

        Args:
            name: Node name

        Returns:
            Dictionary with node information or None if not found
        """
        for node in self.node_depth:
            if node["name"] == name:
                return node
        return None

    def get_link_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get link information by name from flow summary.

        Args:
            name: Link name

        Returns:
            Dictionary with link information or None if not found
        """
        for link in self.link_flow:
            if link["name"] == name:
                return link
        return None

    def get_subcatchment_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get subcatchment information by name from runoff summary.

        Args:
            name: Subcatchment name

        Returns:
            Dictionary with subcatchment information or None if not found
        """
        for sub in self.subcatchment_runoff:
            if sub["name"] == name:
                return sub
        return None

    def get_pump_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get pump information by name from pumping summary.

        Args:
            name: Pump name

        Returns:
            Dictionary with pump information or None if not found
        """
        for pump in self.pumping_summary:
            if pump["pump_name"] == name:
                return pump
        return None

    def get_storage_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get storage unit information by name from storage volume summary.

        Args:
            name: Storage unit name

        Returns:
            Dictionary with storage unit information or None if not found
        """
        for storage in self.storage_volume:
            if storage["storage_unit"] == name:
                return storage
        return None

    def __repr__(self) -> str:
        """String representation."""
        if not self._data:
            return "SwmmReport(empty)"

        header = self.header
        title = header.get("title", "Unknown")
        version = header.get("version", "Unknown")

        return f"SwmmReport(title='{title}', version='{version}')"
