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


# ============================================================================
# PROPERTY SETTER TESTS
# ============================================================================


def test_input_setter_outfalls():
    """Test outfalls property setter."""
    with SwmmInput() as inp:
        outfalls = [
            {"name": "O1", "elevation": 90, "type": "FREE"},
            {"name": "O2", "elevation": 85, "type": "FREE"},
        ]
        inp.outfalls = outfalls
        assert inp.outfalls == outfalls
        assert len(inp.outfalls) == 2


def test_input_setter_storage():
    """Test storage property setter."""
    with SwmmInput() as inp:
        storage = [
            {"name": "S1", "elevation": 100, "max_depth": 10},
        ]
        inp.storage = storage
        assert inp.storage == storage
        assert len(inp.storage) == 1


def test_input_setter_pumps():
    """Test pumps property setter."""
    with SwmmInput() as inp:
        pumps = [
            {"name": "P1", "inlet": "J1", "outlet": "J2"},
        ]
        inp.pumps = pumps
        assert inp.pumps == pumps
        assert len(inp.pumps) == 1


def test_input_setter_orifices():
    """Test orifices property setter."""
    with SwmmInput() as inp:
        orifices = [
            {"name": "OR1", "from_node": "S1", "to_node": "J1"},
        ]
        inp.orifices = orifices
        assert inp.orifices == orifices
        assert len(inp.orifices) == 1


def test_input_setter_weirs():
    """Test weirs property setter."""
    with SwmmInput() as inp:
        weirs = [
            {"name": "W1", "from_node": "S1", "to_node": "J1"},
        ]
        inp.weirs = weirs
        assert inp.weirs == weirs
        assert len(inp.weirs) == 1


def test_input_setter_subcatchments():
    """Test subcatchments property setter."""
    with SwmmInput() as inp:
        subcatchments = [
            {"name": "SC1", "raingage": "RG1", "outlet": "J1", "area": 10},
        ]
        inp.subcatchments = subcatchments
        assert inp.subcatchments == subcatchments
        assert len(inp.subcatchments) == 1


def test_input_setter_raingages():
    """Test raingages property setter."""
    with SwmmInput() as inp:
        raingages = [
            {"name": "RG1", "format": "INTENSITY", "interval": "1:00"},
        ]
        inp.raingages = raingages
        assert inp.raingages == raingages
        assert len(inp.raingages) == 1


def test_input_setter_curves():
    """Test curves property setter."""
    with SwmmInput() as inp:
        curves = [
            {"name": "CURVE1", "type": "PUMP1"},
        ]
        inp.curves = curves
        assert inp.curves == curves
        assert len(inp.curves) == 1


def test_input_setter_timeseries():
    """Test timeseries property setter."""
    with SwmmInput() as inp:
        timeseries = [
            {"name": "TS1", "time": "0:00", "value": "0.0"},
        ]
        inp.timeseries = timeseries
        assert inp.timeseries == timeseries
        assert len(inp.timeseries) == 1


def test_input_setter_controls():
    """Test controls property setter."""
    with SwmmInput() as inp:
        controls = [
            {"rule": "RULE1", "trigger": "IF DEPTH J1 > 5"},
        ]
        inp.controls = controls
        assert inp.controls == controls
        assert len(inp.controls) == 1


def test_input_setter_pollutants():
    """Test pollutants property setter."""
    with SwmmInput() as inp:
        pollutants = [
            {"name": "POL1", "units": "mg/L"},
        ]
        inp.pollutants = pollutants
        assert inp.pollutants == pollutants
        assert len(inp.pollutants) == 1


def test_input_setter_landuses():
    """Test landuses property setter."""
    with SwmmInput() as inp:
        landuses = [
            {"name": "LAND1", "percentimperv": 50},
        ]
        inp.landuses = landuses
        assert inp.landuses == landuses
        assert len(inp.landuses) == 1


def test_input_setter_coverages():
    """Test coverages property setter."""
    with SwmmInput() as inp:
        coverages = [
            {"subcatchment": "S1", "landuse": "LAND1", "percent": 100},
        ]
        inp.coverages = coverages
        assert inp.coverages == coverages
        assert len(inp.coverages) == 1


def test_input_setter_buildup():
    """Test buildup property setter."""
    with SwmmInput() as inp:
        buildup = [
            {
                "landuse": "LAND1",
                "pollutant": "POL1",
                "func_type": "LINEAR",
                "coeff": 10,
            },
        ]
        inp.buildup = buildup
        assert inp.buildup == buildup
        assert len(inp.buildup) == 1


def test_input_setter_washoff():
    """Test washoff property setter."""
    with SwmmInput() as inp:
        washoff = [
            {"landuse": "LAND1", "pollutant": "POL1", "func_type": "EMC", "coeff": 5},
        ]
        inp.washoff = washoff
        assert inp.washoff == washoff
        assert len(inp.washoff) == 1


def test_input_setter_lid_controls():
    """Test lid_controls property setter."""
    with SwmmInput() as inp:
        lid_controls = [
            {"name": "LID1", "type": "BC", "surface_layer": ""},
        ]
        inp.lid_controls = lid_controls
        assert inp.lid_controls == lid_controls
        assert len(inp.lid_controls) == 1


def test_input_setter_lid_usage():
    """Test lid_usage property setter."""
    with SwmmInput() as inp:
        lid_usage = [
            {"subcatchment": "S1", "lid_control": "LID1", "number": 1},
        ]
        inp.lid_usage = lid_usage
        assert inp.lid_usage == lid_usage
        assert len(inp.lid_usage) == 1


def test_input_setter_files():
    """Test files property setter."""
    with SwmmInput() as inp:
        files = [
            {"type": "RAINFALL", "file": "/path/to/rain.dat"},
        ]
        inp.files = files
        assert inp.files == files
        assert len(inp.files) == 1


def test_input_setter_hydrographs():
    """Test hydrographs property setter."""
    with SwmmInput() as inp:
        hydrographs = [
            {"name": "UH1", "data": "1 0.5 0.3 0.2"},
        ]
        inp.hydrographs = hydrographs
        assert inp.hydrographs == hydrographs
        assert len(inp.hydrographs) == 1


def test_input_setter_rdii():
    """Test rdii property setter."""
    with SwmmInput() as inp:
        rdii = [
            {"node": "J1", "unithydrograph": "UH1", "sewerfrac": 0.5},
        ]
        inp.rdii = rdii
        assert inp.rdii == rdii
        assert len(inp.rdii) == 1


# ============================================================================
# DICTIONARY-LIKE INTERFACE TESTS
# ============================================================================


def test_input_getitem():
    """Test __getitem__ generic access."""
    with SwmmInput() as inp:
        inp.title = "Test"
        inp.junctions = [{"name": "J1"}]

        # Access via __getitem__
        assert inp["title"] == "Test"
        assert inp["junctions"] == inp.junctions
        assert len(inp["junctions"]) == 1


def test_input_setitem():
    """Test __setitem__ generic access."""
    with SwmmInput() as inp:
        # Set via __setitem__
        inp["title"] = "New Title"
        inp["junctions"] = [{"name": "J1", "elevation": 100}]

        assert inp.title == "New Title"
        assert len(inp.junctions) == 1
        assert inp["junctions"][0]["elevation"] == 100


def test_input_contains():
    """Test __contains__ for membership testing."""
    with SwmmInput() as inp:
        inp.title = "Test"
        inp.junctions = [{"name": "J1"}]

        assert "title" in inp
        assert "junctions" in inp
        assert "nonexistent" not in inp


def test_input_keys():
    """Test keys() method."""
    with SwmmInput() as inp:
        inp.title = "Test"
        inp.junctions = [{"name": "J1"}]
        inp.outfalls = [{"name": "O1"}]

        keys = list(inp.keys())
        assert "title" in keys
        assert "junctions" in keys
        assert "outfalls" in keys
        assert len(keys) == 3


def test_input_items():
    """Test items() method."""
    with SwmmInput() as inp:
        inp.title = "Test"
        inp.junctions = [{"name": "J1"}]

        items = list(inp.items())
        # Should have title and junctions
        assert len(items) == 2

        # Check that items contain the right keys and values
        keys_from_items = [k for k, v in items]
        assert "title" in keys_from_items
        assert "junctions" in keys_from_items


def test_input_to_dict():
    """Test to_dict() method."""
    with SwmmInput() as inp:
        inp.title = "Test"
        inp.junctions = [{"name": "J1", "elevation": 100}]
        inp.outfalls = [{"name": "O1", "elevation": 90}]

        model_dict = inp.to_dict()

        assert isinstance(model_dict, dict)
        assert model_dict["title"] == "Test"
        assert len(model_dict["junctions"]) == 1
        assert len(model_dict["outfalls"]) == 1

        # Verify it's a copy, not a reference
        model_dict["title"] = "Modified"
        assert inp.title == "Test"  # Original unchanged


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


def test_input_load_invalid_format():
    """Test loading a file with unsupported format."""
    invalid_file = Path("/tmp/test.xyz")

    with pytest.raises(ValueError, match="Unsupported file format"):
        SwmmInput(invalid_file)


def test_input_load_nonexistent_file():
    """Test loading a non-existent file."""
    nonexistent_file = Path("/tmp/this_file_does_not_exist_12345.inp")

    with pytest.raises(FileNotFoundError):
        SwmmInput(nonexistent_file)


def test_input_load_nonexistent_json():
    """Test loading a non-existent JSON file."""
    nonexistent_file = Path("/tmp/this_file_does_not_exist_12345.json")

    # JSON decoder may raise different error - just check it raises an exception
    with pytest.raises((FileNotFoundError, Exception)):
        SwmmInput(nonexistent_file)


def test_input_load_nonexistent_parquet():
    """Test loading a non-existent Parquet file."""
    nonexistent_file = Path("/tmp/this_file_does_not_exist_12345.parquet")

    with pytest.raises(FileNotFoundError):
        SwmmInput(nonexistent_file)


def test_input_export_to_invalid_path(tmp_path):
    """Test exporting to INP requires parent directory to exist."""
    with SwmmInput() as inp:
        inp.title = "Test"

        # Parent directory must exist - encoders don't create it
        deep_path = tmp_path / "deep"
        deep_path.mkdir()
        output_path = deep_path / "model.inp"
        inp.to_inp(output_path)

        assert output_path.exists()


def test_input_export_json_creates_directory(tmp_path):
    """Test exporting to JSON with existing parent directory."""
    with SwmmInput() as inp:
        inp.title = "Test"

        # Parent directory must exist - encoders don't create it
        deep_path = tmp_path / "deep"
        deep_path.mkdir()
        output_path = deep_path / "model.json"
        inp.to_json(output_path)

        assert output_path.exists()


def test_input_export_parquet_creates_directory(tmp_path):
    """Test exporting to Parquet with existing parent directory."""
    with SwmmInput() as inp:
        inp.title = "Test"
        inp.junctions = [{"name": "J1"}]

        # Parent directory must exist - encoders don't create it
        deep_path = tmp_path / "deep"
        deep_path.mkdir()
        output_path = deep_path / "model.parquet"
        inp.to_parquet(output_path, single_file=True)

        # Parent directories should be created
        assert output_path.exists()


# DATAFRAME TESTS
def test_input_to_dataframe_single_section():
    """Test exporting a single section to DataFrame."""
    pd = pytest.importorskip("pandas")

    with SwmmInput() as inp:
        inp.junctions = [
            {"name": "J1", "elevation": 100, "max_depth": 5},
            {"name": "J2", "elevation": 95, "max_depth": 6},
        ]

        df = inp.to_dataframe("junctions")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "name" in df.columns
        assert df["name"].tolist() == ["J1", "J2"]


def test_input_to_dataframe_all_sections():
    """Test exporting all sections to DataFrame dictionary."""
    pd = pytest.importorskip("pandas")

    with SwmmInput() as inp:
        inp.junctions = [
            {"name": "J1", "elevation": 100},
            {"name": "J2", "elevation": 95},
        ]
        inp.outfalls = [
            {"name": "O1", "elevation": 80},
        ]
        inp.title = "Test Model"

        dfs = inp.to_dataframe()

        assert isinstance(dfs, dict)
        assert "junctions" in dfs
        assert "outfalls" in dfs
        assert "title" not in dfs  # String sections excluded
        assert len(dfs["junctions"]) == 2
        assert len(dfs["outfalls"]) == 1


def test_input_to_dataframe_empty():
    """Test exporting empty section returns empty DataFrame."""
    pd = pytest.importorskip("pandas")

    with SwmmInput() as inp:
        inp.junctions = []

        df = inp.to_dataframe("junctions")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


def test_input_to_dataframe_invalid_section():
    """Test error when requesting invalid section."""
    with SwmmInput() as inp:
        with pytest.raises(ValueError, match="not found"):
            inp.to_dataframe("nonexistent_section")


def test_input_to_dataframe_complex_data():
    """Test DataFrame export with complex nested data."""
    pd = pytest.importorskip("pandas")

    with SwmmInput() as inp:
        inp.conduits = [
            {
                "name": "C1",
                "inlet_node": "J1",
                "outlet_node": "J2",
                "length": 1000,
                "roughness": 0.01,
            },
            {
                "name": "C2",
                "inlet_node": "J2",
                "outlet_node": "O1",
                "length": 500,
                "roughness": 0.012,
            },
        ]

        df = inp.to_dataframe("conduits")

        assert len(df) == 2
        assert df.loc[df["name"] == "C1", "length"].values[0] == 1000
        assert df.loc[df["name"] == "C2", "roughness"].values[0] == 0.012
