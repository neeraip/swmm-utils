# SWMM Utils

Utilities for encoding and decoding EPA SWMM input files (.inp) to/from multiple formats.

[![Tests](https://img.shields.io/badge/tests-23/23_passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.8+-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

## Overview

This project provides a comprehensive toolkit for encoding and decoding EPA SWMM (Storm Water Management Model) input files. It enables:

- **Multi-format support**: Decode .inp files and encode to .inp, JSON, or Parquet
- **Round-trip conversion**: Decode → Modify → Encode without data loss
- **Flexible Parquet output**: Single-file or multi-file Parquet modes
- **Structured data access**: Work with SWMM models as Python dictionaries
- **Simple API**: Clean encode/decode pattern for all formats

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/neeraip/swmm-utils.git
cd swmm-utils

# Install the package
pip install -e .
```

### Basic Usage (Python)

```python
from swmm_utils import SwmmInputDecoder, SwmmInputEncoder

# Decode a SWMM .inp file into a Python dict
decoder = SwmmInputDecoder()
model = decoder.decode_file("model.inp")

# Access structured data
for junction in model['junctions']:
    print(f"{junction['name']}: elevation={junction['elevation']}")

# Modify the model
model['junctions'][0]['elevation'] = '100.5'
model['title'] = 'Modified SWMM Model'

# Encode to different formats
encoder = SwmmInputEncoder()

# Write back to .inp format
encoder.encode_to_inp_file(model, "modified.inp")

# Encode to JSON
encoder.encode_to_json(model, "model.json", pretty=True)

# Encode to Parquet (multi-file: one file per section)
encoder.encode_to_parquet(model, "model_parquet/", single_file=False)

# Encode to Parquet (single-file: all sections in one file)
encoder.encode_to_parquet(model, "model.parquet", single_file=True)

# Decode from JSON
json_model = decoder.decode_json("model.json")

# Decode from Parquet (auto-detects file or directory)
parquet_model = decoder.decode_parquet("model.parquet")
```

## Architecture

```
.inp file → Decoder → Dict Model → Encoder → .inp/JSON/Parquet
                                   ↓
                               Decoder
                                   ↓
                              Dict Model
```

The architecture uses Python dictionaries as the in-memory data model:

1. **Decoder**: Reads .inp, JSON, or Parquet files into Python dict structures
2. **Encoder**: Writes dict objects to .inp, JSON, or Parquet formats
3. **Dict Model**: Simple Python dictionaries - easy to inspect, modify, and manipulate

## Features

- ✅ Decode all SWMM 5.2.4 input file sections (60+ sections)
- ✅ Encode to .inp, JSON, and Parquet formats
- ✅ Decode from .inp, JSON, and Parquet formats
- ✅ Configurable Parquet output (single-file or multi-file modes)
- ✅ Round-trip conversion (decode → encode) without data loss
- ✅ Comprehensive test suite (23 tests passing)
- ✅ Full support for comments, whitespace, and formatting
- ✅ Clean encode/decode API pattern
- ✅ Backwards compatibility with old parser/unparser API

## Supported SWMM Sections

### Project Configuration
- `[TITLE]` - Project title and description
- `[OPTIONS]` - Simulation options (34 parameters)
- `[REPORT]` - Output reporting options
- `[FILES]` - External file references
- `[MAP]` - Map extent and units
- `[BACKDROP]` - Background image settings
- `[PROFILES]` - Longitudinal profile definitions

### Hydrology
- `[RAINGAGES]` - Rain gage definitions
- `[EVAPORATION]` - Evaporation data
- `[SUBCATCHMENTS]` - Subcatchment properties
- `[SUBAREAS]` - Subcatchment surface areas
- `[INFILTRATION]` - Infiltration parameters
- `[AQUIFERS]` - Groundwater aquifer properties
- `[GROUNDWATER]` - Subcatchment groundwater
- `[GWF]` - Groundwater flow equations
- `[SNOWPACKS]` - Snow pack parameters
- `[TEMPERATURE]` - Temperature data
- `[ADJUSTMENTS]` - Climate adjustments

### Hydraulic Network - Nodes
- `[JUNCTIONS]` - Junction nodes
- `[OUTFALLS]` - Outfall nodes
- `[STORAGE]` - Storage unit nodes
- `[DIVIDERS]` - Flow divider nodes

### Hydraulic Network - Links
- `[CONDUITS]` - Conduit links
- `[PUMPS]` - Pump links
- `[ORIFICES]` - Orifice links
- `[WEIRS]` - Weir links
- `[OUTLETS]` - Outlet links

### Cross-Sections
- `[XSECTIONS]` - Link cross-section geometry
- `[LOSSES]` - Minor losses
- `[TRANSECTS]` - Irregular cross-section data

### Water Quality
- `[POLLUTANTS]` - Pollutant properties
- `[LANDUSES]` - Land use categories
- `[COVERAGES]` - Subcatchment land use coverage
- `[BUILDUP]` - Pollutant buildup functions
- `[WASHOFF]` - Pollutant washoff functions
- `[TREATMENT]` - Treatment equations
- `[INFLOWS]` - External inflows
- `[DWF]` - Dry weather inflows
- `[RDII]` - RDII inflow parameters
- `[HYDROGRAPHS]` - Unit hydrograph data
- `[LOADING]` - Initial pollutant loads

### LID Controls (Low Impact Development)
- `[LID_CONTROLS]` - LID control definitions
- `[LID_USAGE]` - LID usage in subcatchments

### Street/Inlet Modeling (SWMM 5.2+)
- `[STREETS]` - Street cross-section properties
- `[INLETS]` - Inlet design parameters
- `[INLET_USAGE]` - Inlet usage on streets

### Curves & Time Series
- `[TIMESERIES]` - Time series data
- `[PATTERNS]` - Time patterns
- `[CURVES]` - Curve data

### Operational Controls
- `[CONTROLS]` - Rule-based controls

### Visualization
- `[COORDINATES]` - Node coordinates
- `[VERTICES]` - Link vertices
- `[POLYGONS]` - Subcatchment polygons
- `[SYMBOLS]` - Rain gage symbols
- `[LABELS]` - Map labels
- `[TAGS]` - Object tags

## Examples

### Example 1: Decode and Analyze

```python
from swmm_utils import SwmmInputDecoder

decoder = SwmmInputDecoder()
model = decoder.decode_file("large_network.inp")

# Count elements
print(f"Junctions: {len(model.get('junctions', []))}")
print(f"Conduits: {len(model.get('conduits', []))}")
print(f"Subcatchments: {len(model.get('subcatchments', []))}")

# Find high-elevation junctions
for junc in model.get('junctions', []):
    if float(junc['elevation']) > 100:
        print(f"High junction: {junc['name']} at {junc['elevation']}m")
```

### Example 2: Convert for Analytics

```python
from swmm_utils import SwmmInputDecoder, SwmmInputEncoder

# Decode SWMM model
decoder = SwmmInputDecoder()
model = decoder.decode_file("network.inp")

# Export to Parquet for analysis in pandas/R/SQL
encoder = SwmmInputEncoder()
encoder.encode_to_parquet(model, "network_parquet/", single_file=False)

# Now analyze with pandas
import pandas as pd
junctions = pd.read_parquet("network_parquet/junctions.parquet")
conduits = pd.read_parquet("network_parquet/conduits.parquet")

print(junctions.describe())
print(f"Average pipe length: {conduits['length'].astype(float).mean():.2f}")
```

### Example 3: Batch Processing

```python
from pathlib import Path
from swmm_utils import SwmmInputDecoder, SwmmInputEncoder

decoder = SwmmInputDecoder()
encoder = SwmmInputEncoder()

# Convert all .inp files in a directory to JSON
for inp_file in Path("models/").glob("*.inp"):
    model = decoder.decode_file(str(inp_file))
    json_file = inp_file.with_suffix('.json')
    encoder.encode_to_json(model, str(json_file), pretty=True)
    print(f"Converted {inp_file.name} → {json_file.name}")
```

### Example 4: Round-Trip Conversion

```python
from swmm_utils import SwmmInputDecoder, SwmmInputEncoder

decoder = SwmmInputDecoder()
encoder = SwmmInputEncoder()

# Decode from .inp
model = decoder.decode_file("original.inp")

# Encode to JSON
encoder.encode_to_json(model, "model.json", pretty=True)

# Decode from JSON
json_model = decoder.decode_json("model.json")

# Encode to Parquet (single file)
encoder.encode_to_parquet(json_model, "model.parquet", single_file=True)

# Decode from Parquet
parquet_model = decoder.decode_parquet("model.parquet")

# Encode back to .inp
encoder.encode_to_inp_file(parquet_model, "final.inp")

# All data preserved throughout the round-trip!
```

## Testing

```bash
# Run all tests
pytest -q

# Run with coverage
pytest --cov=swmm_utils --cov-report=html

# Run specific test file
pytest tests/test_formats.py -v

# Run the demo
python example/demo.py
```

All 23 tests pass, including comprehensive format conversion and round-trip tests.

## Project Structure

```
swmm-utils/
├── src/
│   └── swmm_utils/              # Main package
│       ├── __init__.py          # Package exports
│       ├── decoder.py           # Decode .inp/JSON/Parquet → dict
│       └── encoder.py           # Encode dict → .inp/JSON/Parquet
├── example/
│   ├── demo.py                  # Comprehensive demonstration
│   └── README.md                # Example documentation
├── tests/
│   ├── test_parser.py           # Core parsing tests
│   ├── test_formats.py          # Format conversion tests
│   ├── test_roundtrip.py        # Round-trip validation
│   ├── test_edgecases.py        # Edge case tests
│   └── README.md                # Test documentation
├── data/                        # Sample SWMM input files
├── docs/
│   └── SWMM_INPUT_FILE.md       # Complete SWMM format reference
├── setup.py                     # Package configuration
├── requirements.txt             # Core dependencies
├── requirements-dev.txt         # Development dependencies
└── README.md                    # This file
```

## Performance

Tested on a 240-junction SWMM model (10_Outfalls.inp):

- **Decode .inp**: ~0.05 seconds
- **Encode to JSON**: 873 KB
- **Encode to Parquet (multi-file)**: 18 files, ~110 KB total
- **Encode to Parquet (single-file)**: 1 file, ~109 KB
- **Round-trip (.inp → JSON → Parquet → .inp)**: All data preserved

## Documentation

- **[README.md](README.md)** - This file
- **[example/README.md](example/README.md)** - Example usage and demo
- **[docs/SWMM_INPUT_FILE.md](docs/SWMM_INPUT_FILE.md)** - Complete SWMM format reference
- **[tests/README.md](tests/README.md)** - Testing guide

## Dependencies

### Required
- Python 3.8+
- pyarrow >= 10.0.0 (for Parquet support)

### Development
- pytest >= 7.0.0
- pytest-cov >= 4.0.0

## Known Limitations

1. **Round-trip Formatting**: Some cosmetic differences
   - Comments may not be preserved in exact original positions
   - Whitespace normalized to SWMM standard format
   - All data and structure fully preserved

2. **Complex Sections**: Some sections have simplified handling
   - `[CONTROLS]` - Stored as text (complex rule syntax)
   - `[TRANSECTS]` - Multi-line format preserved

## Backwards Compatibility

The old API (`SwmmParser`, `SwmmUnparser`, `SwmmConverter`) is still available for backwards compatibility:

```python
# Old API (deprecated but still works)
from swmm_utils import SwmmParser, SwmmUnparser, SwmmConverter

parser = SwmmParser()
model = parser.parse_file("model.inp")

converter = SwmmConverter()
converter.to_json(model, "model.json")

unparser = SwmmUnparser()
unparser.unparse_to_file(model, "output.inp")

# New API (recommended)
from swmm_utils import SwmmInputDecoder, SwmmInputEncoder

decoder = SwmmInputDecoder()
model = decoder.decode_file("model.inp")

encoder = SwmmInputEncoder()
encoder.encode_to_json(model, "model.json")
encoder.encode_to_inp_file(model, "output.inp")
```

## Contributing

Contributions welcome! Areas of interest:

- Enhanced validation logic
- Model manipulation utilities
- Performance optimization
- Additional output formats (e.g., GeoJSON)
- Documentation improvements
- More example scripts

## Changelog

### v0.1.0 (Current)
- ✅ Refactored to encode/decode pattern
- ✅ Added JSON and Parquet decoding support
- ✅ Configurable Parquet output (single-file or multi-file)
- ✅ Moved to `src/` layout for better package structure
- ✅ Comprehensive test suite (23 tests)
- ✅ Backwards compatibility with old API
- ✅ Removed protobuf dependencies
- ✅ Clean API with clear naming

## License

MIT License - see LICENSE file

## Acknowledgments

- EPA SWMM development team for the excellent documentation
- Apache Arrow/Parquet for columnar analytics support

## Contact

For questions or issues, please open a GitHub issue.

---

**Status**: ✅ Production-ready (Python implementation complete)
