"""Tests for SWMM report file decoder."""

import pytest
from pathlib import Path
from swmm_utils import SwmmReportDecoder


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
