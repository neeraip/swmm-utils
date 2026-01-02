"""Tests for SWMM report file parsing."""

import pytest
from pathlib import Path
from swmm_utils import SwmmReport, SwmmReportDecoder


def get_test_report():
    """Get path to test report file."""
    # Use example2.rpt from examples
    examples_dir = Path(__file__).parent.parent / "examples" / "example2"
    rpt_file = examples_dir / "example2.rpt"

    if not rpt_file.exists():
        pytest.skip(f"Test report file not found: {rpt_file}")

    return rpt_file


def test_swmm_report_decoder():
    """Test SwmmReportDecoder basic functionality."""
    rpt_file = get_test_report()
    decoder = SwmmReportDecoder()

    data = decoder.decode_file(rpt_file)

    assert isinstance(data, dict)
    assert "header" in data
    assert "element_count" in data
    assert "analysis_options" in data


def test_swmm_report_header():
    """Test parsing report header."""
    rpt_file = get_test_report()
    decoder = SwmmReportDecoder()
    data = decoder.decode_file(rpt_file)

    header = data["header"]
    assert "version" in header
    assert header["version"] == "5.2"
    assert "build" in header


def test_swmm_report_element_count():
    """Test parsing element count."""
    rpt_file = get_test_report()
    decoder = SwmmReportDecoder()
    data = decoder.decode_file(rpt_file)

    element_count = data["element_count"]
    assert element_count["subcatchments"] == 4
    assert element_count["nodes"] == 5
    assert element_count["links"] == 4
    assert element_count["rain_gages"] == 1


def test_swmm_report_analysis_options():
    """Test parsing analysis options."""
    rpt_file = get_test_report()
    decoder = SwmmReportDecoder()
    data = decoder.decode_file(rpt_file)

    options = data["analysis_options"]
    assert options["flow_units"] == "CFS"
    assert options["infiltration_method"] == "GREEN_AMPT"
    assert options["flow_routing_method"] == "DYNWAVE"


def test_swmm_report_subcatchment_runoff():
    """Test parsing subcatchment runoff summary."""
    rpt_file = get_test_report()
    decoder = SwmmReportDecoder()
    data = decoder.decode_file(rpt_file)

    runoff = data["subcatchment_runoff"]
    assert len(runoff) == 4

    # Check first subcatchment
    ca1 = runoff[0]
    assert ca1["name"] == "CA-1"
    assert ca1["total_precip"] == pytest.approx(6.65, rel=0.01)
    assert ca1["total_runoff"] == pytest.approx(4.15, rel=0.01)


def test_swmm_report_node_depth():
    """Test parsing node depth summary."""
    rpt_file = get_test_report()
    decoder = SwmmReportDecoder()
    data = decoder.decode_file(rpt_file)

    nodes = data["node_depth"]
    assert len(nodes) == 5

    # Find outlet node
    outlet = next((n for n in nodes if n["name"] == "Outlet"), None)
    assert outlet is not None
    assert outlet["type"] == "OUTFALL"
    assert outlet["maximum_depth"] == pytest.approx(1.42, rel=0.01)


def test_swmm_report_link_flow():
    """Test parsing link flow summary."""
    rpt_file = get_test_report()
    decoder = SwmmReportDecoder()
    data = decoder.decode_file(rpt_file)

    links = data["link_flow"]
    assert len(links) == 4

    # Check first link
    p001 = links[0]
    assert p001["name"] == "P001"
    assert p001["type"] == "CONDUIT"
    assert p001["maximum_flow"] == pytest.approx(23.73, rel=0.01)


def test_swmm_report_high_level_interface():
    """Test SwmmReport high-level interface."""
    rpt_file = get_test_report()

    with SwmmReport(rpt_file) as report:
        # Test properties
        assert report.header["version"] == "5.2"
        assert report.element_count["nodes"] == 5
        assert len(report.subcatchment_runoff) == 4
        assert len(report.node_depth) == 5
        assert len(report.link_flow) == 4

        # Test getter methods
        node = report.get_node_by_name("Outlet")
        assert node is not None
        assert node["type"] == "OUTFALL"

        link = report.get_link_by_name("P001")
        assert link is not None
        assert link["type"] == "CONDUIT"

        sub = report.get_subcatchment_by_name("CA-1")
        assert sub is not None
        assert sub["total_precip"] == pytest.approx(6.65, rel=0.01)


def test_swmm_report_context_manager():
    """Test SwmmReport context manager."""
    rpt_file = get_test_report()

    report = SwmmReport()
    assert report._data == {}

    with report:
        report.load(rpt_file)
        assert report.header["version"] == "5.2"


def test_swmm_report_file_not_found():
    """Test error handling for missing file."""
    with pytest.raises(FileNotFoundError):
        SwmmReport("nonexistent.rpt")


def test_swmm_report_invalid_extension():
    """Test error handling for invalid file extension."""
    rpt_file = get_test_report()

    # Create a path with wrong extension
    wrong_ext = rpt_file.with_suffix(".txt")

    with pytest.raises(ValueError, match="Expected .rpt file"):
        report = SwmmReport()
        report.load(wrong_ext)


def test_swmm_report_repr():
    """Test string representation."""
    rpt_file = get_test_report()

    report = SwmmReport(rpt_file)
    repr_str = repr(report)
    assert "SwmmReport" in repr_str
    assert "5.2" in repr_str
