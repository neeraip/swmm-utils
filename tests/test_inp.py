"""Test SWMM .inp high-level SwmmInput interface.

Tests the SwmmInput class which provides typed properties and
context manager support for working with SWMM models.
"""

import pytest
from pathlib import Path
from swmm_utils import SwmmInput


def test_swmm_input_load_and_modify(tmp_path):
    """Test loading and modifying a SWMM input file."""
    # Use an existing test file
    test_file = Path(__file__).parent.parent / "data" / "simple_test.inp"

    if not test_file.exists():
        pytest.skip("Test file not found")

    # Load and modify
    with SwmmInput(test_file) as inp:
        # Check loaded data
        assert inp.title is not None

        # Modify title
        original_title = inp.title
        inp.title = "Modified Test Model"
        assert inp.title == "Modified Test Model"
        assert inp.title != original_title

        # Check typed properties
        if inp.junctions:
            assert isinstance(inp.junctions, list)
            assert len(inp.junctions) > 0

        # Save to new file
        output_inp = tmp_path / "modified.inp"
        inp.to_inp(output_inp)

        assert output_inp.exists()

    # Load the modified file and verify
    with SwmmInput(output_inp) as inp2:
        assert inp2.title == "Modified Test Model"


def test_swmm_input_create_new():
    """Test creating a new SWMM model from scratch."""
    with SwmmInput() as inp:
        # Set basic properties
        inp.title = "New Model"

        # Add junctions
        inp.junctions = [
            {"name": "J1", "elevation": 100, "max_depth": 5},
            {"name": "J2", "elevation": 95, "max_depth": 5},
        ]

        # Add outfall
        inp.outfalls = [
            {"name": "O1", "elevation": 90, "type": "FREE"},
        ]

        # Add conduits
        inp.conduits = [
            {
                "name": "C1",
                "from_node": "J1",
                "to_node": "J2",
                "length": 100,
                "roughness": 0.01,
            },
            {
                "name": "C2",
                "from_node": "J2",
                "to_node": "O1",
                "length": 100,
                "roughness": 0.01,
            },
        ]

        # Verify properties
        assert inp.title == "New Model"
        assert len(inp.junctions) == 2
        assert len(inp.outfalls) == 1
        assert len(inp.conduits) == 2

        # Test dict access
        assert "junctions" in inp
        assert inp["junctions"] == inp.junctions


def test_swmm_input_json_roundtrip(tmp_path):
    """Test saving to JSON and loading back."""
    # Create a model
    with SwmmInput() as inp:
        inp.title = "JSON Test"
        inp.junctions = [{"name": "J1", "elevation": 100}]

        # Save to JSON
        json_file = tmp_path / "test.json"
        inp.to_json(json_file)

        assert json_file.exists()

    # Load from JSON
    with SwmmInput(json_file) as inp2:
        assert inp2.title == "JSON Test"
        assert len(inp2.junctions) == 1
        assert inp2.junctions[0]["name"] == "J1"


def test_swmm_input_parquet_roundtrip(tmp_path):
    """Test saving to Parquet and loading back."""
    # Create a model
    with SwmmInput() as inp:
        inp.title = "Parquet Test"
        inp.junctions = [{"name": "J1", "elevation": 100}]
        inp.outfalls = [{"name": "O1", "elevation": 90}]

        # Save to Parquet (single file)
        parquet_file = tmp_path / "test.parquet"
        inp.to_parquet(parquet_file, single_file=True)

        assert parquet_file.exists()

    # Load from Parquet
    with SwmmInput(parquet_file) as inp2:
        assert inp2.title == "Parquet Test"
        assert len(inp2.junctions) == 1
        assert len(inp2.outfalls) == 1


def test_swmm_input_without_context_manager():
    """Test that SwmmInput works without context manager."""
    inp = SwmmInput()
    inp.title = "No Context Manager"
    inp.junctions = [{"name": "J1", "elevation": 100}]

    assert inp.title == "No Context Manager"
    assert len(inp.junctions) == 1


def test_swmm_input_options():
    """Test options property."""
    with SwmmInput() as inp:
        # Options should be empty dict initially
        assert inp.options == {}

        # Add options
        inp.options["FLOW_UNITS"] = "CFS"
        inp.options["INFILTRATION"] = "HORTON"

        assert inp.options["FLOW_UNITS"] == "CFS"
        assert inp.options["INFILTRATION"] == "HORTON"

        # Set entire options dict
        inp.options = {"START_DATE": "01/01/2020", "END_DATE": "01/02/2020"}
        assert "START_DATE" in inp.options
        assert "FLOW_UNITS" not in inp.options  # Old options replaced


def test_swmm_input_repr():
    """Test string representation."""
    with SwmmInput() as inp:
        inp.title = "Test"
        inp.junctions = [{"name": "J1"}]

        repr_str = repr(inp)
        assert "SwmmInput" in repr_str
        assert "sections=" in repr_str
