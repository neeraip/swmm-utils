"""SWMM Input - High-level interface for SWMM input files with typed properties."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from .inp_decoder import SwmmInputDecoder
from .inp_encoder import SwmmInputEncoder


class SwmmInput:
    """High-level interface for SWMM input files with typed properties and context manager support.

    Usage:
        # Load from file
        with SwmmInput("model.inp") as inp:
            inp.title = "Modified Model"
            inp.to_inp("output.inp")
            inp.to_json("output.json")

        # Create new model
        with SwmmInput() as inp:
            inp.title = "New Model"
            inp.junctions = [{"name": "J1", "elevation": 100}]
            inp.to_inp("new_model.inp")
    """

    def __init__(self, filepath: Optional[Union[str, Path]] = None):
        """Initialize SwmmInput, optionally loading from a file.

        Args:
            filepath: Optional path to .inp, .json, or .parquet file to load
        """
        self._decoder = SwmmInputDecoder()
        self._encoder = SwmmInputEncoder()
        self._data: Dict[str, Any] = {}

        if filepath:
            self._load(filepath)

    def _load(self, filepath: Union[str, Path]) -> None:
        """Load data from a file."""
        filepath = Path(filepath)
        suffix = filepath.suffix.lower()

        if suffix == ".inp":
            self._data = self._decoder.decode_file(str(filepath))
        elif suffix == ".json":
            self._data = self._decoder.decode_json(str(filepath))
        elif suffix == ".parquet":
            self._data = self._decoder.decode_parquet(str(filepath))
        else:
            raise ValueError(
                f"Unsupported file format: {suffix}. Use .inp, .json, or .parquet"
            )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        return False

    # Output methods
    def to_inp(self, filepath: Union[str, Path]) -> None:
        """Save to .inp file.

        Args:
            filepath: Path to output .inp file
        """
        self._encoder.encode_to_inp_file(self._data, str(filepath))

    def to_json(self, filepath: Union[str, Path], pretty: bool = True) -> None:
        """Save to JSON file.

        Args:
            filepath: Path to output JSON file
            pretty: Whether to format JSON with indentation (default: True)
        """
        self._encoder.encode_to_json(self._data, str(filepath), pretty=pretty)

    def to_parquet(
        self, output_path: Union[str, Path], single_file: bool = False
    ) -> None:
        """Save to Parquet format.

        Args:
            output_path: Path to output file or directory
            single_file: If True, save as single file; if False, save as directory with one file per section
        """
        self._encoder.encode_to_parquet(
            self._data, str(output_path), single_file=single_file
        )

    # Typed properties for common SWMM sections

    @property
    def title(self) -> str:
        """Model title/description."""
        title = self._data.get("title", "")
        # Handle case where title is stored as a list (from Parquet)
        if isinstance(title, list) and len(title) > 0:
            if isinstance(title[0], dict) and "value" in title[0]:
                return title[0]["value"]
        return title if isinstance(title, str) else ""

    @title.setter
    def title(self, value: str) -> None:
        self._data["title"] = value

    @property
    def options(self) -> Dict[str, Any]:
        """Simulation options."""
        if "options" not in self._data:
            self._data["options"] = {}
        return self._data["options"]

    @options.setter
    def options(self, value: Dict[str, Any]) -> None:
        self._data["options"] = value

    @property
    def junctions(self) -> List[Dict[str, Any]]:
        """List of junction nodes."""
        if "junctions" not in self._data:
            self._data["junctions"] = []
        return self._data["junctions"]

    @junctions.setter
    def junctions(self, value: List[Dict[str, Any]]) -> None:
        self._data["junctions"] = value

    @property
    def outfalls(self) -> List[Dict[str, Any]]:
        """List of outfall nodes."""
        if "outfalls" not in self._data:
            self._data["outfalls"] = []
        return self._data["outfalls"]

    @outfalls.setter
    def outfalls(self, value: List[Dict[str, Any]]) -> None:
        self._data["outfalls"] = value

    @property
    def storage(self) -> List[Dict[str, Any]]:
        """List of storage nodes."""
        if "storage" not in self._data:
            self._data["storage"] = []
        return self._data["storage"]

    @storage.setter
    def storage(self, value: List[Dict[str, Any]]) -> None:
        self._data["storage"] = value

    @property
    def conduits(self) -> List[Dict[str, Any]]:
        """List of conduit links."""
        if "conduits" not in self._data:
            self._data["conduits"] = []
        return self._data["conduits"]

    @conduits.setter
    def conduits(self, value: List[Dict[str, Any]]) -> None:
        self._data["conduits"] = value

    @property
    def pumps(self) -> List[Dict[str, Any]]:
        """List of pump links."""
        if "pumps" not in self._data:
            self._data["pumps"] = []
        return self._data["pumps"]

    @pumps.setter
    def pumps(self, value: List[Dict[str, Any]]) -> None:
        self._data["pumps"] = value

    @property
    def orifices(self) -> List[Dict[str, Any]]:
        """List of orifice links."""
        if "orifices" not in self._data:
            self._data["orifices"] = []
        return self._data["orifices"]

    @orifices.setter
    def orifices(self, value: List[Dict[str, Any]]) -> None:
        self._data["orifices"] = value

    @property
    def weirs(self) -> List[Dict[str, Any]]:
        """List of weir links."""
        if "weirs" not in self._data:
            self._data["weirs"] = []
        return self._data["weirs"]

    @weirs.setter
    def weirs(self, value: List[Dict[str, Any]]) -> None:
        self._data["weirs"] = value

    @property
    def subcatchments(self) -> List[Dict[str, Any]]:
        """List of subcatchments."""
        if "subcatchments" not in self._data:
            self._data["subcatchments"] = []
        return self._data["subcatchments"]

    @subcatchments.setter
    def subcatchments(self, value: List[Dict[str, Any]]) -> None:
        self._data["subcatchments"] = value

    @property
    def raingages(self) -> List[Dict[str, Any]]:
        """List of rain gages."""
        if "raingages" not in self._data:
            self._data["raingages"] = []
        return self._data["raingages"]

    @raingages.setter
    def raingages(self, value: List[Dict[str, Any]]) -> None:
        self._data["raingages"] = value

    @property
    def curves(self) -> List[Dict[str, Any]]:
        """List of curves."""
        if "curves" not in self._data:
            self._data["curves"] = []
        return self._data["curves"]

    @curves.setter
    def curves(self, value: List[Dict[str, Any]]) -> None:
        self._data["curves"] = value

    @property
    def timeseries(self) -> List[Dict[str, Any]]:
        """List of time series."""
        if "timeseries" not in self._data:
            self._data["timeseries"] = []
        return self._data["timeseries"]

    @timeseries.setter
    def timeseries(self, value: List[Dict[str, Any]]) -> None:
        self._data["timeseries"] = value

    @property
    def controls(self) -> List[Dict[str, Any]]:
        """List of control rules."""
        if "controls" not in self._data:
            self._data["controls"] = []
        return self._data["controls"]

    @controls.setter
    def controls(self, value: List[Dict[str, Any]]) -> None:
        self._data["controls"] = value

    @property
    def pollutants(self) -> List[Dict[str, Any]]:
        """List of pollutants."""
        if "pollutants" not in self._data:
            self._data["pollutants"] = []
        return self._data["pollutants"]

    @pollutants.setter
    def pollutants(self, value: List[Dict[str, Any]]) -> None:
        self._data["pollutants"] = value

    @property
    def landuses(self) -> List[Dict[str, Any]]:
        """List of land uses."""
        if "landuses" not in self._data:
            self._data["landuses"] = []
        return self._data["landuses"]

    @landuses.setter
    def landuses(self, value: List[Dict[str, Any]]) -> None:
        self._data["landuses"] = value

    # Generic access for all sections
    def __getitem__(self, key: str) -> Any:
        """Get a section by name (generic access)."""
        return self._data.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a section by name (generic access)."""
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        """Check if a section exists."""
        return key in self._data

    def keys(self):
        """Return section names."""
        return self._data.keys()

    def items(self):
        """Return section items."""
        return self._data.items()

    def to_dict(self) -> Dict[str, Any]:
        """Export the entire model as a dictionary.

        Returns:
            Dictionary representation of the SWMM model
        """
        return self._data.copy()

    def __repr__(self) -> str:
        """String representation."""
        sections = list(self._data.keys())
        return f"SwmmInput(sections={len(sections)}, keys={sections[:5]}{'...' if len(sections) > 5 else ''})"
