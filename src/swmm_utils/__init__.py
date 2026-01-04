"""SWMM Utils - Encode and decode SWMM input, report, and output files.

This package provides tools to:
- Decode .inp files into structured dict objects
- Encode dict objects to .inp, .json, or .parquet formats
- Decode .rpt (report) files into structured data
- Decode .out (output) binary files into structured data
- Validate SWMM models
"""

__version__ = "0.3.2"

from .inp_decoder import SwmmInputDecoder
from .inp_encoder import SwmmInputEncoder
from .inp import SwmmInput
from .rpt_decoder import SwmmReportDecoder
from .rpt import SwmmReport
from .out_decoder import SwmmOutputDecoder
from .out import SwmmOutput

__all__ = [
    "SwmmInput",  # Primary input file interface
    "SwmmInputDecoder",
    "SwmmInputEncoder",
    "SwmmReport",  # Primary report file interface
    "SwmmReportDecoder",
    "SwmmOutput",  # Primary output file interface
    "SwmmOutputDecoder",
]
