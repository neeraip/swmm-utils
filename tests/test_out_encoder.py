"""Test SWMM .out file encoder (low-level API).

Tests the SwmmOutputEncoder class for generating .out files in other formats.
"""

import pytest
from pathlib import Path
import json

from swmm_utils import SwmmOutputDecoder, SwmmOutputEncoder


# Get the examples directory
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLE1_OUT = EXAMPLES_DIR / "example1" / "example1.out"


@pytest.fixture
def example_data():
    """Load example output data for testing encoder."""
    if not EXAMPLE1_OUT.exists():
        pytest.skip("example1.out not found")

    decoder = SwmmOutputDecoder()
    return decoder.decode_file(EXAMPLE1_OUT)


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
