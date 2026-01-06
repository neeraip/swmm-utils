"""Test SWMM .out file decoder and encoder (low-level API).

Tests the SwmmOutputDecoder and SwmmOutputEncoder classes for parsing
and generating .out binary files.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import json

from swmm_utils import SwmmOutputDecoder, SwmmOutputEncoder


# Get the examples directory
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLE1_OUT = EXAMPLES_DIR / "example1" / "example1.out"


@pytest.fixture
def example_data():
    """Load example output data for testing decoder and encoder."""
    if not EXAMPLE1_OUT.exists():
        pytest.skip("example1.out not found")
    
    decoder = SwmmOutputDecoder()
    return decoder.decode_file(EXAMPLE1_OUT)


# ============================================================================
# DECODER TESTS
# ============================================================================


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


# ============================================================================
# ENCODER TESTS
# ============================================================================


def test_encoder_initialization():
    """Test encoder can be initialized."""
    encoder = SwmmOutputEncoder()
    assert encoder is not None


@pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
def test_encoder_to_json_with_summary(example_data, tmp_path):
    """Test encoding to JSON format with summary function."""
    encoder = SwmmOutputEncoder()
    json_file = tmp_path / "output.json"
    
    def summary_func():
        return {
            "version": "5.2",
            "n_periods": example_data["metadata"]["n_periods"],
        }
    
    encoder.encode_to_json(
        example_data, json_file, pretty=True, summary_func=summary_func
    )
    
    # Verify file was created
    assert json_file.exists()
    assert json_file.stat().st_size > 0
    
    # Verify JSON structure
    with open(json_file, "r") as f:
        data = json.load(f)
        assert "header" in data
        assert "metadata" in data
        assert "summary" in data
        assert data["summary"]["version"] == "5.2"


@pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
def test_encoder_to_json_without_summary(example_data, tmp_path):
    """Test encoding to JSON format without summary function."""
    encoder = SwmmOutputEncoder()
    json_file = tmp_path / "output_no_summary.json"
    
    encoder.encode_to_json(example_data, json_file, pretty=True)
    
    assert json_file.exists()
    
    # Verify JSON doesn't include summary
    with open(json_file, "r") as f:
        data = json.load(f)
        assert "header" in data
        assert "metadata" in data
        assert "summary" not in data


@pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
def test_encoder_json_pretty_formatting(example_data, tmp_path):
    """Test JSON pretty printing vs compact formatting."""
    encoder = SwmmOutputEncoder()
    
    json_pretty = tmp_path / "pretty.json"
    json_compact = tmp_path / "compact.json"
    
    encoder.encode_to_json(example_data, json_pretty, pretty=True)
    encoder.encode_to_json(example_data, json_compact, pretty=False)
    
    # Compact should be smaller or equal in size
    assert json_compact.stat().st_size <= json_pretty.stat().st_size


@pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
def test_encoder_to_parquet_single_file(example_data, tmp_path):
    """Test encoding to Parquet single file format."""
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    
    encoder = SwmmOutputEncoder()
    parquet_file = tmp_path / "output.parquet"
    
    def summary_func():
        return {"version": "5.2"}
    
    encoder.encode_to_parquet(
        example_data, parquet_file, single_file=True, summary_func=summary_func
    )
    
    assert parquet_file.exists()
    assert parquet_file.stat().st_size > 0


@pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
def test_encoder_to_parquet_multiple_files(example_data, tmp_path):
    """Test encoding to Parquet multi-file format."""
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    
    encoder = SwmmOutputEncoder()
    parquet_dir = tmp_path / "output_parquet"
    
    def summary_func():
        return {"version": "5.2"}
    
    encoder.encode_to_parquet(
        example_data, parquet_dir, single_file=False, summary_func=summary_func
    )
    
    # Check directory and summary file exist
    assert parquet_dir.exists()
    assert (parquet_dir / "summary.parquet").exists()
    
    # Check element files exist based on data
    if example_data["metadata"]["labels"]["node"]:
        assert (parquet_dir / "nodes.parquet").exists()
    if example_data["metadata"]["labels"]["link"]:
        assert (parquet_dir / "links.parquet").exists()
    if example_data["metadata"]["labels"]["subcatchment"]:
        assert (parquet_dir / "subcatchments.parquet").exists()


@pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
def test_encoder_format_auto_detection_json(example_data, tmp_path):
    """Test encode_to_file auto-detects JSON format from extension."""
    encoder = SwmmOutputEncoder()
    json_file = tmp_path / "output.json"
    
    encoder.encode_to_file(example_data, json_file)
    
    assert json_file.exists()
    with open(json_file, "r") as f:
        data = json.load(f)
        assert "header" in data


@pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
def test_encoder_format_auto_detection_parquet(example_data, tmp_path):
    """Test encode_to_file auto-detects Parquet format from extension."""
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    
    encoder = SwmmOutputEncoder()
    parquet_file = tmp_path / "output.parquet"
    
    encoder.encode_to_file(example_data, parquet_file)
    
    assert parquet_file.exists()


@pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
def test_encoder_explicit_format_specification(example_data, tmp_path):
    """Test encode_to_file with explicit format specification."""
    encoder = SwmmOutputEncoder()
    output_file = tmp_path / "output.dat"
    
    # Explicitly specify JSON format despite .dat extension
    encoder.encode_to_file(example_data, output_file, file_format="json")
    
    assert output_file.exists()
    with open(output_file, "r") as f:
        data = json.load(f)
        assert "header" in data


