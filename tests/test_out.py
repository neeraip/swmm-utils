"""Unit tests for SWMM output file high-level interface."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta

from swmm_utils import SwmmOutput


# Get the examples directory
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLE1_OUT = EXAMPLES_DIR / "example1" / "example1.out"
EXAMPLE2_OUT = EXAMPLES_DIR / "example2" / "example2.out"


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
    def test_to_dataframe_no_timeseries(self):
        """Test to_dataframe() without time series loaded."""
        output = SwmmOutput(EXAMPLE1_OUT, load_time_series=False)

        # Full export should return dict with empty DataFrames
        result = output.to_dataframe()
        assert isinstance(result, dict)
        assert "metadata" in result
        assert "nodes" in result
        assert "links" in result
        assert "subcatchments" in result

        # Metadata should have data (single row)
        assert len(result["metadata"]) == 1
        # Metadata should have some columns (varies based on load_time_series)
        assert len(result["metadata"].columns) > 0

        # Other sections should be empty
        assert len(result["nodes"]) == 0
        assert len(result["links"]) == 0
        assert len(result["subcatchments"]) == 0

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_dataframe_with_timeseries(self):
        """Test to_dataframe() with time series loaded."""
        output = SwmmOutput(EXAMPLE1_OUT, load_time_series=True)

        # Full export
        result = output.to_dataframe()
        assert isinstance(result, dict)
        assert "metadata" in result
        assert "nodes" in result
        assert "links" in result
        assert "subcatchments" in result

        # Check metadata
        meta_df = result["metadata"]
        assert len(meta_df) == 1
        assert "n_periods" in meta_df.columns
        assert meta_df["n_periods"].iloc[0] == output.n_periods

        # Check time series sections (may have 0 rows if no data)
        for section_name in ["nodes", "links", "subcatchments"]:
            section_df = result[section_name]
            if len(section_df) > 0:
                # Should have MultiIndex
                assert section_df.index.names == ["timestamp", "element_name"]

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_dataframe_section_export(self):
        """Test to_dataframe() section-level export."""
        output = SwmmOutput(EXAMPLE1_OUT, load_time_series=True)

        # Section export
        nodes_df = output.to_dataframe("nodes")
        links_df = output.to_dataframe("links")
        subcatchments_df = output.to_dataframe("subcatchments")

        # All should be DataFrames
        for section_df in [nodes_df, links_df, subcatchments_df]:
            assert hasattr(section_df, "shape")  # Is a DataFrame
            if len(section_df) > 0:
                # Should have MultiIndex if not empty
                assert section_df.index.names == ["timestamp", "element_name"]

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_dataframe_single_element(self):
        """Test to_dataframe() single element export."""
        output = SwmmOutput(EXAMPLE1_OUT, load_time_series=True)

        # Get first link if available
        if output.n_links > 0:
            first_link = output.link_labels[0]
            link_df = output.to_dataframe("links", first_link)

            assert hasattr(link_df, "shape")  # Is a DataFrame
            if len(link_df) > 0:
                # Should have simple timestamp index
                assert link_df.index.name == "timestamp"
                # Should have value columns
                assert any(col.startswith("value_") for col in link_df.columns)

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_dataframe_invalid_element_type(self):
        """Test to_dataframe() with invalid element type."""
        output = SwmmOutput(EXAMPLE1_OUT, load_time_series=True)

        with pytest.raises(ValueError):
            output.to_dataframe("invalid_type")

    @pytest.mark.skipif(not EXAMPLE1_OUT.exists(), reason="example1.out not found")
    def test_to_dataframe_element_name_without_type(self):
        """Test to_dataframe() with element_name but no element_type."""
        output = SwmmOutput(EXAMPLE1_OUT, load_time_series=True)

        with pytest.raises(ValueError):
            output.to_dataframe(element_name="SomeElement")