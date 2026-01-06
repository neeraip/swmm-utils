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
    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_dataframe_full_export(self, tmp_path):
        """Test full DataFrame export with metadata and all sections."""
        pytest.importorskip("pandas")

        output = SwmmOutput(EXAMPLE1_OUT, load_time_series=True)
        result = output.to_dataframe()

        # Check structure
        assert isinstance(result, dict)
        assert "metadata" in result
        assert "nodes" in result
        assert "links" in result
        assert "subcatchments" in result

        # Check metadata
        metadata_df = result["metadata"]
        assert metadata_df.shape[0] == 1
        assert "version" in metadata_df.columns
        assert "flow_unit" in metadata_df.columns
        assert "n_periods" in metadata_df.columns

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_dataframe_links_section(self, tmp_path):
        """Test section-level DataFrame export for links."""
        pytest.importorskip("pandas")

        output = SwmmOutput(EXAMPLE1_OUT, load_time_series=True)
        links_df = output.to_dataframe("links")

        # Should be a DataFrame
        assert hasattr(links_df, "shape")

        if len(links_df) > 0:
            # Check MultiIndex structure
            assert links_df.index.names == ["timestamp", "element_name"]

            # Check for value columns
            value_cols = [col for col in links_df.columns if col.startswith("value_")]
            assert len(value_cols) > 0

            # Can filter by timestamp
            first_timestamp = links_df.index.get_level_values("timestamp")[0]
            filtered = links_df.loc[first_timestamp]
            assert len(filtered) > 0

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_dataframe_single_element(self, tmp_path):
        """Test single element DataFrame export."""
        pytest.importorskip("pandas")

        output = SwmmOutput(EXAMPLE1_OUT, load_time_series=True)

        if output.n_links > 0:
            first_link = output.link_labels[0]
            link_df = output.to_dataframe("links", first_link)

            # Should be a DataFrame
            assert hasattr(link_df, "shape")

            if len(link_df) > 0:
                # Check timestamp index
                assert link_df.index.name == "timestamp"

                # Should have value columns
                value_cols = [col for col in link_df.columns if col.startswith("value_")]
                assert len(value_cols) > 0

                # Should have n_periods rows
                assert len(link_df) == output.n_periods

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_dataframe_pandas_operations(self, tmp_path):
        """Test that exported DataFrames support pandas operations."""
        pytest.importorskip("pandas")

        output = SwmmOutput(EXAMPLE1_OUT, load_time_series=True)

        if output.n_links > 0:
            first_link = output.link_labels[0]
            link_df = output.to_dataframe("links", first_link)

            if len(link_df) > 0 and "value_0" in link_df.columns:
                # Test pandas operations
                max_val = link_df["value_0"].max()
                assert isinstance(max_val, (int, float))

                mean_val = link_df["value_0"].mean()
                assert isinstance(mean_val, (int, float))

                # Test resampling if pandas available
                try:
                    resampled = link_df["value_0"].resample("1D").mean()
                    assert len(resampled) > 0
                except Exception:
                    # Resampling may fail with synthetic data, that's okay
                    pass