"""Unit tests for SWMM output file decoder and encoder."""

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
    """Load example output data for testing encoder."""
    if not EXAMPLE1_OUT.exists():
        pytest.skip("example1.out not found")
    
    decoder = SwmmOutputDecoder()
    return decoder.decode_file(EXAMPLE1_OUT)


class TestSwmmOutputDecoder:
    """Tests for SwmmOutputDecoder class."""

    def test_decoder_initialization(self):
        """Test decoder can be initialized."""
        decoder = SwmmOutputDecoder()
        assert decoder is not None

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_decode_example1_file(self):
        """Test decoding example1.out file."""
        decoder = SwmmOutputDecoder()
        data = decoder.decode_file(EXAMPLE1_OUT)

        assert "header" in data
        assert "metadata" in data
        assert "time_index" in data

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_header_parsing(self):
        """Test header information is correctly parsed."""
        decoder = SwmmOutputDecoder()
        data = decoder.decode_file(EXAMPLE1_OUT)

        header = data["header"]
        assert header["magic_start"] == 516114522
        assert header["version"] > 0
        assert "version_str" in header
        assert header["flow_unit"] in ["CFS", "GPM", "MGD", "CMS", "LPS", "MLD"]
        assert header["n_subcatchments"] >= 0
        assert header["n_nodes"] >= 0
        assert header["n_links"] >= 0
        assert header["n_pollutants"] >= 0

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_metadata_parsing(self):
        """Test metadata is correctly parsed."""
        decoder = SwmmOutputDecoder()
        data = decoder.decode_file(EXAMPLE1_OUT)

        metadata = data["metadata"]
        assert "labels" in metadata
        assert "properties" in metadata
        assert "start_date" in metadata
        assert "report_interval" in metadata
        assert "n_periods" in metadata

        # Check labels structure
        assert "subcatchment" in metadata["labels"]
        assert "node" in metadata["labels"]
        assert "link" in metadata["labels"]
        assert "pollutant" in metadata["labels"]

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_time_index_creation(self):
        """Test time index is properly created."""
        decoder = SwmmOutputDecoder()
        data = decoder.decode_file(EXAMPLE1_OUT)

        time_index = data["time_index"]
        assert isinstance(time_index, list)
        assert len(time_index) == data["metadata"]["n_periods"]

        if len(time_index) > 1:
            # Check time increases monotonically
            assert time_index[0] < time_index[-1]


class TestSwmmOutputEncoder:
    """Tests for SwmmOutputEncoder class."""

    def test_encoder_initialization(self):
        """Test encoder can be initialized."""
        encoder = SwmmOutputEncoder()
        assert encoder is not None

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_encode_to_json_single_file(self, example_data, tmp_path):
        """Test encoding output data to JSON format."""
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

        assert json_file.exists()
        assert json_file.stat().st_size > 0

        # Verify JSON content
        with open(json_file, "r") as f:
            data = json.load(f)
            assert "header" in data
            assert "metadata" in data
            assert "summary" in data
            assert data["summary"]["version"] == "5.2"

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_encode_to_json_without_summary(self, example_data, tmp_path):
        """Test encoding to JSON without summary function."""
        encoder = SwmmOutputEncoder()
        json_file = tmp_path / "output_no_summary.json"

        encoder.encode_to_json(example_data, json_file, pretty=True)

        assert json_file.exists()

        # Verify JSON content doesn't have summary
        with open(json_file, "r") as f:
            data = json.load(f)
            assert "header" in data
            assert "metadata" in data
            assert "summary" not in data

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_encode_to_json_compact(self, example_data, tmp_path):
        """Test encoding to JSON without pretty printing."""
        encoder = SwmmOutputEncoder()
        json_file_pretty = tmp_path / "output_pretty.json"
        json_file_compact = tmp_path / "output_compact.json"

        encoder.encode_to_json(example_data, json_file_pretty, pretty=True)
        encoder.encode_to_json(example_data, json_file_compact, pretty=False)

        # Compact should be smaller or equal
        assert json_file_compact.stat().st_size <= json_file_pretty.stat().st_size

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_encode_to_parquet_single_file(self, example_data, tmp_path):
        """Test encoding output data to Parquet single file format."""
        pytest.importorskip("pandas")
        pytest.importorskip("pyarrow")

        encoder = SwmmOutputEncoder()
        parquet_file = tmp_path / "output.parquet"

        def summary_func():
            return {
                "version": "5.2",
                "n_periods": example_data["metadata"]["n_periods"],
            }

        encoder.encode_to_parquet(
            example_data, parquet_file, single_file=True, summary_func=summary_func
        )

        assert parquet_file.exists()
        assert parquet_file.stat().st_size > 0

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_encode_to_parquet_multiple_files(self, example_data, tmp_path):
        """Test encoding to Parquet multi-file format."""
        pytest.importorskip("pandas")
        pytest.importorskip("pyarrow")

        encoder = SwmmOutputEncoder()
        parquet_dir = tmp_path / "output_parquet"

        def summary_func():
            return {
                "version": "5.2",
                "n_periods": example_data["metadata"]["n_periods"],
            }

        encoder.encode_to_parquet(
            example_data, parquet_dir, single_file=False, summary_func=summary_func
        )

        assert parquet_dir.exists()
        assert (parquet_dir / "summary.parquet").exists()

        # Check for element files based on data content
        if example_data["metadata"]["labels"]["node"]:
            assert (parquet_dir / "nodes.parquet").exists()
        if example_data["metadata"]["labels"]["link"]:
            assert (parquet_dir / "links.parquet").exists()
        if example_data["metadata"]["labels"]["subcatchment"]:
            assert (parquet_dir / "subcatchments.parquet").exists()

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_encode_to_file_infers_json_format(self, example_data, tmp_path):
        """Test encode_to_file infers JSON format from extension."""
        encoder = SwmmOutputEncoder()
        json_file = tmp_path / "output.json"

        encoder.encode_to_file(example_data, json_file)

        assert json_file.exists()
        with open(json_file, "r") as f:
            data = json.load(f)
            assert "header" in data

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_encode_to_file_infers_parquet_format(self, example_data, tmp_path):
        """Test encode_to_file infers Parquet format from extension."""
        pytest.importorskip("pandas")
        pytest.importorskip("pyarrow")

        encoder = SwmmOutputEncoder()
        parquet_file = tmp_path / "output.parquet"

        encoder.encode_to_file(example_data, parquet_file)

        assert parquet_file.exists()

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_encode_to_file_explicit_format(self, example_data, tmp_path):
        """Test encode_to_file with explicit format specification."""
        encoder = SwmmOutputEncoder()
        output_file = tmp_path / "output.dat"

        # Explicitly specify JSON format despite wrong extension
        encoder.encode_to_file(example_data, output_file, file_format="json")

        assert output_file.exists()
        with open(output_file, "r") as f:
            data = json.load(f)
            assert "header" in data

