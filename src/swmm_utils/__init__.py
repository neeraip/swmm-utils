"""SWMM Utils - Encode and decode SWMM input and report files.

This package provides tools to:
- Decode .inp files into structured dict objects
- Encode dict objects to .inp, .json, or .parquet formats
- Decode .rpt (report) files into structured data
- Validate SWMM models
"""

__version__ = "0.1.0"

from .inp_decoder import SwmmInputDecoder
from .inp_encoder import SwmmInputEncoder
from .inp import SwmmInput
from .rpt_decoder import SwmmReportDecoder
from .rpt import SwmmReport

__all__ = [
    "SwmmInput",  # Primary input file interface
    "SwmmInputDecoder",
    "SwmmInputEncoder",
    "SwmmReport",  # Primary report file interface
    "SwmmReportDecoder",
]
