"""SWMM Utils - Encode and decode SWMM input files.

This package provides tools to:
- Decode .inp files into structured dict objects
- Encode dict objects to .inp, .json, or .parquet formats
- Validate SWMM models
"""

__version__ = "0.1.0"

from .decoder import SwmmInputDecoder
from .encoder import SwmmInputEncoder

# Backwards compatibility aliases (deprecated)
SwmmParser = SwmmInputDecoder
SwmmUnparser = SwmmInputEncoder
SwmmConverter = SwmmInputEncoder

__all__ = [
    "SwmmInputDecoder",
    "SwmmInputEncoder",
    # Backwards compatibility
    "SwmmParser",
    "SwmmUnparser",
    "SwmmConverter",
]
