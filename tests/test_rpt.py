"""Tests for SWMM report file high-level interface."""

import pytest
from pathlib import Path
from swmm_utils import SwmmReport


def get_test_report():
    """Get path to test report file."""
    # Use example2.rpt from examples
    examples_dir = Path(__file__).parent.parent / "examples" / "example2"
    rpt_file = examples_dir / "example2.rpt"

    if not rpt_file.exists():
        pytest.skip(f"Test report file not found: {rpt_file}")

    return rpt_file


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
