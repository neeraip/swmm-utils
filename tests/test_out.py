"""Unit tests for SWMM output file decoder and interface."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta

from swmm_utils import SwmmOutput, SwmmOutputDecoder


# Get the examples directory
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLE1_OUT = EXAMPLES_DIR / "example1" / "example1.out"
EXAMPLE2_OUT = EXAMPLES_DIR / "example2" / "example2.out"


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


class TestSwmmOutput:
    """Tests for SwmmOutput high-level interface."""

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_output_initialization(self):
        """Test SwmmOutput can be initialized."""
        output = SwmmOutput(EXAMPLE1_OUT)
        assert output is not None
        assert output.filepath == EXAMPLE1_OUT

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_version_property(self):
        """Test version property."""
        output = SwmmOutput(EXAMPLE1_OUT)
        version = output.version
        assert isinstance(version, str)
        assert "." in version  # Should be in format X.Y.Z

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_flow_unit_property(self):
        """Test flow unit property."""
        output = SwmmOutput(EXAMPLE1_OUT)
        flow_unit = output.flow_unit
        assert isinstance(flow_unit, str)
        assert flow_unit in ["CFS", "GPM", "MGD", "CMS", "LPS", "MLD", "UNKNOWN"]

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_date_properties(self):
        """Test date and time properties."""
        output = SwmmOutput(EXAMPLE1_OUT)

        start_date = output.start_date
        assert isinstance(start_date, datetime)

        end_date = output.end_date
        assert isinstance(end_date, datetime)

        assert end_date >= start_date

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_report_interval_property(self):
        """Test report interval property."""
        output = SwmmOutput(EXAMPLE1_OUT)
        interval = output.report_interval
        assert isinstance(interval, timedelta)
        assert interval.total_seconds() > 0

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_n_periods_property(self):
        """Test number of periods property."""
        output = SwmmOutput(EXAMPLE1_OUT)
        n_periods = output.n_periods
        assert isinstance(n_periods, int)
        assert n_periods > 0

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_time_index_property(self):
        """Test time index property."""
        output = SwmmOutput(EXAMPLE1_OUT)
        time_index = output.time_index
        assert isinstance(time_index, list)
        assert len(time_index) == output.n_periods

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_element_count_properties(self):
        """Test element count properties."""
        output = SwmmOutput(EXAMPLE1_OUT)

        assert output.n_subcatchments >= 0
        assert output.n_nodes >= 0
        assert output.n_links >= 0
        assert output.n_pollutants >= 0

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_label_properties(self):
        """Test label list properties."""
        output = SwmmOutput(EXAMPLE1_OUT)

        subcatch_labels = output.subcatchment_labels
        assert isinstance(subcatch_labels, list)
        assert len(subcatch_labels) == output.n_subcatchments

        node_labels = output.node_labels
        assert isinstance(node_labels, list)
        assert len(node_labels) == output.n_nodes

        link_labels = output.link_labels
        assert isinstance(link_labels, list)
        assert len(link_labels) == output.n_links

        pollutant_labels = output.pollutant_labels
        assert isinstance(pollutant_labels, list)
        assert len(pollutant_labels) == output.n_pollutants

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_properties_access(self):
        """Test accessing element properties."""
        output = SwmmOutput(EXAMPLE1_OUT)

        node_props = output.node_properties
        assert isinstance(node_props, dict)

        link_props = output.link_properties
        assert isinstance(link_props, dict)

        subcatch_props = output.subcatchment_properties
        assert isinstance(subcatch_props, dict)

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_get_node_method(self):
        """Test getting a specific node."""
        output = SwmmOutput(EXAMPLE1_OUT)

        if output.n_nodes > 0:
            node_id = output.node_labels[0]
            node = output.get_node(node_id)
            assert node is not None
            assert "id" in node
            assert node["id"] == node_id

        # Test non-existent node
        node = output.get_node("NONEXISTENT_NODE")
        assert node is None

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_get_link_method(self):
        """Test getting a specific link."""
        output = SwmmOutput(EXAMPLE1_OUT)

        if output.n_links > 0:
            link_id = output.link_labels[0]
            link = output.get_link(link_id)
            assert link is not None
            assert "id" in link
            assert link["id"] == link_id

        # Test non-existent link
        link = output.get_link("NONEXISTENT_LINK")
        assert link is None

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_get_subcatchment_method(self):
        """Test getting a specific subcatchment."""
        output = SwmmOutput(EXAMPLE1_OUT)

        if output.n_subcatchments > 0:
            subcatch_id = output.subcatchment_labels[0]
            subcatch = output.get_subcatchment(subcatch_id)
            assert subcatch is not None
            assert "id" in subcatch
            assert subcatch["id"] == subcatch_id

        # Test non-existent subcatchment
        subcatch = output.get_subcatchment("NONEXISTENT_SUBCATCH")
        assert subcatch is None

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_summary_method(self):
        """Test summary method."""
        output = SwmmOutput(EXAMPLE1_OUT)
        summary = output.summary()

        assert isinstance(summary, dict)
        assert "version" in summary
        assert "flow_unit" in summary
        assert "start_date" in summary
        assert "end_date" in summary
        assert "n_periods" in summary
        assert "n_nodes" in summary
        assert "n_links" in summary
        assert "n_subcatchments" in summary
        assert "pollutants" in summary

    @pytest.mark.skipif(not EXAMPLE2_OUT.exists(), reason="example2.out not found")
    def test_example2_file(self):
        """Test parsing example2.out file."""
        output = SwmmOutput(EXAMPLE2_OUT)
        assert output is not None
        assert output.n_periods > 0
        assert output.version

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_pollutant_units(self):
        """Test pollutant units property."""
        output = SwmmOutput(EXAMPLE1_OUT)
        units = output.pollutant_units
        assert isinstance(units, dict)

        for pollutant_name, unit in units.items():
            assert unit in ["MG", "UG", "COUNTS", "UNKNOWN"]

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_json_single_file(self, tmp_path):
        """Test exporting to JSON format."""
        output = SwmmOutput(EXAMPLE1_OUT)
        json_file = tmp_path / "output.json"

        output.to_json(json_file, pretty=True)

        assert json_file.exists()
        assert json_file.stat().st_size > 0

        # Verify JSON content
        import json

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
    def test_to_json_creates_parent_directory(self, tmp_path):
        """Test that to_json creates parent directories if they don't exist."""
        output = SwmmOutput(EXAMPLE1_OUT)
        json_file = tmp_path / "subdir" / "deep" / "output.json"

        output.to_json(json_file)

        assert json_file.exists()
        assert json_file.parent.exists()

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
        import json

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
