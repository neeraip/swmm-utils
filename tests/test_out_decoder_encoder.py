"""Unit tests for SWMM output file decoder."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta

from swmm_utils import SwmmOutputDecoder


# Get the examples directory
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLE1_OUT = EXAMPLES_DIR / "example1" / "example1.out"


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
