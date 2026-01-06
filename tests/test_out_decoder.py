"""Test SWMM .out file decoder (low-level API).

Tests the SwmmOutputDecoder class for parsing .out binary files.
"""

import pytest
from pathlib import Path
from datetime import datetime

from swmm_utils import SwmmOutputDecoder


# Get the examples directory
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLE1_OUT = EXAMPLES_DIR / "example1" / "example1.out"


@pytest.fixture
def example_data():
    """Load example output data for testing decoder."""
    if not EXAMPLE1_OUT.exists():
        pytest.skip("example1.out not found")

    decoder = SwmmOutputDecoder()
    return decoder.decode_file(EXAMPLE1_OUT)


def test_decoder_initialization():
    """Test decoder can be initialized."""
    decoder = SwmmOutputDecoder()
    assert decoder is not None


@pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
def test_decoder_file_parsing(example_data):
    """Test decoding example1.out file returns expected structure."""
    assert "header" in example_data
    assert "metadata" in example_data
    assert "time_index" in example_data


@pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
def test_decoder_header_structure(example_data):
    """Test header information is correctly parsed."""
    header = example_data["header"]

    # Verify magic number
    assert header["magic_start"] == 516114522

    # Verify version info
    assert header["version"] > 0
    assert "version_str" in header
    assert "." in header["version_str"]

    # Verify flow unit
    assert header["flow_unit"] in ["CFS", "GPM", "MGD", "CMS", "LPS", "MLD"]

    # Verify element counts
    assert header["n_subcatchments"] >= 0
    assert header["n_nodes"] >= 0
    assert header["n_links"] >= 0
    assert header["n_pollutants"] >= 0


@pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
def test_decoder_metadata_structure(example_data):
    """Test metadata is correctly parsed."""
    metadata = example_data["metadata"]

    # Check required sections
    assert "labels" in metadata
    assert "properties" in metadata
    assert "start_date" in metadata
    assert "report_interval" in metadata
    assert "n_periods" in metadata

    # Check labels structure
    labels = metadata["labels"]
    assert "subcatchment" in labels
    assert "node" in labels
    assert "link" in labels
    assert "pollutant" in labels

    # Check all labels are lists
    assert isinstance(labels["subcatchment"], list)
    assert isinstance(labels["node"], list)
    assert isinstance(labels["link"], list)
    assert isinstance(labels["pollutant"], list)


@pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
def test_decoder_time_index_creation(example_data):
    """Test time index is properly created."""
    time_index = example_data["time_index"]

    assert isinstance(time_index, list)
    assert len(time_index) == example_data["metadata"]["n_periods"]

    # If multiple periods, check they're ordered
    if len(time_index) > 1:
        assert time_index[0] < time_index[-1]
        # Check all are datetime objects
        for ts in time_index:
            assert isinstance(ts, datetime)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
