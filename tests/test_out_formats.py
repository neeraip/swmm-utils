"""Unit tests for SWMM output file export formats (JSON, Parquet)."""

import pytest
import json
from pathlib import Path

from swmm_utils import SwmmOutput


# Get the examples directory
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLE1_OUT = EXAMPLES_DIR / "example1" / "example1.out"


class TestSwmmOutputFormats:
    """Tests for SwmmOutput export formats."""

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_json_single_file(self, tmp_path):
        """Test exporting to JSON format."""
        output = SwmmOutput(EXAMPLE1_OUT)
        json_file = tmp_path / "output.json"

        output.to_json(json_file, pretty=True)

        assert json_file.exists()
        assert json_file.stat().st_size > 0

        # Verify JSON content
        with open(json_file, "r") as f:
            data = json.load(f)
            assert "header" in data
            assert "metadata" in data
            assert "summary" in data

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_json_pretty_false(self, tmp_path):
        """Test exporting to JSON without pretty printing."""
        output = SwmmOutput(EXAMPLE1_OUT)
        json_file = tmp_path / "output_compact.json"

        output.to_json(json_file, pretty=False)

        assert json_file.exists()
        assert json_file.stat().st_size > 0

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_json_creates_parent_directory(self, tmp_path):
        """Test that to_json creates parent directories if they don't exist."""
        output = SwmmOutput(EXAMPLE1_OUT)
        json_file = tmp_path / "subdir" / "deep" / "output.json"

        output.to_json(json_file)

        assert json_file.exists()
        assert json_file.parent.exists()

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_json_with_time_series(self, tmp_path):
        """Test exporting to JSON with full time series data."""
        # Initialize with time series loading enabled
        output = SwmmOutput(EXAMPLE1_OUT, load_time_series=True)
        json_file = tmp_path / "output_with_timeseries.json"

        # Export - will include time series since it was loaded
        output.to_json(json_file, pretty=True)

        assert json_file.exists()
        assert json_file.stat().st_size > 0

        # Verify JSON content includes time series
        with open(json_file, "r") as f:
            data = json.load(f)
            assert "header" in data
            assert "metadata" in data
            assert "summary" in data
            assert "time_series" in data

            # Verify time series structure
            ts = data["time_series"]
            assert "nodes" in ts
            assert "links" in ts
            assert "subcatchments" in ts
            assert "system" in ts

            # Verify nodes have time step data
            if ts["nodes"]:
                first_node = next(iter(ts["nodes"].values()))
                assert len(first_node) > 0
                assert "timestamp" in first_node[0]
                assert "values" in first_node[0]

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_json_time_series_file_size(self, tmp_path):
        """Test that time series export creates significantly larger file."""
        # Export without time series (default)
        output_no_ts = SwmmOutput(EXAMPLE1_OUT)
        json_file_no_ts = tmp_path / "output_no_ts.json"
        output_no_ts.to_json(json_file_no_ts, pretty=True)

        # Export with time series (initialized with load_time_series=True)
        output_with_ts = SwmmOutput(EXAMPLE1_OUT, load_time_series=True)
        json_file_with_ts = tmp_path / "output_with_ts.json"
        output_with_ts.to_json(json_file_with_ts, pretty=True)

        size_no_ts = json_file_no_ts.stat().st_size
        size_with_ts = json_file_with_ts.stat().st_size

        # With time series should be significantly larger
        assert size_with_ts > size_no_ts
        # Time series should add at least 5x the size for this example
        assert size_with_ts >= size_no_ts * 5

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_parquet_single_file(self, tmp_path):
        """Test exporting to Parquet single file format."""
        pytest.importorskip("pandas")
        pytest.importorskip("pyarrow")

        output = SwmmOutput(EXAMPLE1_OUT)
        parquet_file = tmp_path / "output.parquet"

        output.to_parquet(parquet_file, single_file=True)

        assert parquet_file.exists()
        assert parquet_file.stat().st_size > 0

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_parquet_multiple_files(self, tmp_path):
        """Test exporting to Parquet multi-file format."""
        pytest.importorskip("pandas")
        pytest.importorskip("pyarrow")

        output = SwmmOutput(EXAMPLE1_OUT)
        parquet_dir = tmp_path / "output_parquet"

        output.to_parquet(parquet_dir, single_file=False)

        assert parquet_dir.exists()
        # Check that at least summary.parquet was created
        assert (parquet_dir / "summary.parquet").exists()

        # Check for other files based on model content
        if output.n_nodes > 0:
            assert (parquet_dir / "nodes.parquet").exists()
        if output.n_links > 0:
            assert (parquet_dir / "links.parquet").exists()
        if output.n_subcatchments > 0:
            assert (parquet_dir / "subcatchments.parquet").exists()

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_parquet_creates_parent_directory(self, tmp_path):
        """Test that to_parquet creates parent directories if they don't exist."""
        pytest.importorskip("pandas")
        pytest.importorskip("pyarrow")

        output = SwmmOutput(EXAMPLE1_OUT)
        parquet_file = tmp_path / "subdir" / "deep" / "output.parquet"

        output.to_parquet(parquet_file, single_file=True)

        assert parquet_file.exists()
        assert parquet_file.parent.exists()
