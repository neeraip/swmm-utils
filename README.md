# SWMM Utils

Utilities for interpreting EPA SWMM input (.inp), report (.rpt), and output (.out) files.

[![Tests](https://img.shields.io/badge/tests-69/69_passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.8+-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

## Overview

This project provides a comprehensive toolkit for working with EPA SWMM (Storm Water Management Model) files:

- **[Input Files (.inp)](docs/SWMM_INPUT_FILE.md)** - Load, modify, and save SWMM models with typed properties. Support for .inp, JSON, and Parquet formats.
- **[Report Files (.rpt)](docs/SWMM_REPORT_FILE.md)** - Parse simulation results and extract all major sections (node depths, link flows, pumping, storage, LID performance, etc.)
- **[Output Files (.out)](docs/SWMM_OUTPUT_FILE.md)** - Extract binary SWMM output data with optional time series loading. Export to JSON or Parquet.

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/neeraip/swmm-utils.git
cd swmm-utils

# Install the package
pip install -e .
```

### Basic Usage

For detailed examples and API documentation for each file type, see:

- **[Input Files (.inp) Usage](docs/SWMM_INPUT_FILE.md)** - Loading, modifying, and saving SWMM models
- **[Report Files (.rpt) Usage](docs/SWMM_REPORT_FILE.md)** - Parsing and analyzing simulation results
- **[Output Files (.out) Usage](docs/SWMM_OUTPUT_FILE.md)** - Extracting binary output data with time series

**Quick example:**
```python
from swmm_utils import SwmmInput, SwmmReport, SwmmOutput

# Input files
with SwmmInput("model.inp") as inp:
    inp.title = "Modified Model"
    inp.to_json("model.json")

# Report files
with SwmmReport("simulation.rpt") as report:
    for node in report.node_depth:
        print(f"{node['name']}: {node['maximum_depth']:.2f} ft")

# Output files (metadata only or with time series)
output = SwmmOutput("simulation.out", load_time_series=True)
output.to_json("output_complete.json", pretty=True)
```

## API Reference

Detailed API documentation is available in the respective docs files:

- **[SwmmInput API](docs/SWMM_INPUT_FILE.md#api-reference)** - High-level interface for input files with typed properties
- **[SwmmReport API](docs/SWMM_REPORT_FILE.md#api-reference)** - High-level interface for report files
- **[SwmmOutput API](docs/SWMM_OUTPUT_FILE.md#api-reference)** - High-level interface for output files with optional time series loading

### Core Classes

All classes support context manager pattern (`with` statement) for clean resource management:

```python
# All three file types use context managers
with SwmmInput("model.inp") as inp:
    ...

with SwmmReport("simulation.rpt") as report:
    ...

with SwmmOutput("simulation.out") as output:
    ...
```

### Lower-Level APIs (Advanced)

For direct decoder/encoder access:

- **SwmmInputDecoder** & **SwmmInputEncoder** - Direct dict-based access to input file data
- **SwmmReportDecoder** - Direct dict-based access to report file data

See [Input Files documentation](docs/SWMM_INPUT_FILE.md#lower-level-api) for details.

## Architecture

```
Input Files:
.inp file → SwmmInput → Modify Properties → Save (.inp/JSON/Parquet)
               ↓
          Typed Properties
       (title, junctions, etc.)

Report Files:
.rpt file → SwmmReport → Access Results
               ↓
          Typed Properties
       (node_depth, link_flow, etc.)

Output Files:
.out file → SwmmOutput → Export (JSON/Parquet)
               ↓
       Metadata or Time Series
    (default: metadata only)
```

The architecture uses Python dictionaries as the in-memory data model:

1. **SwmmInput/SwmmReport/SwmmOutput**: High-level interfaces with typed properties and context managers
2. **Decoders**: Read .inp/.rpt/.out/JSON/Parquet files into Python dict structures
3. **Encoders**: Write dict objects to .inp/JSON/Parquet formats (input files only)
4. **Dict Model**: Simple Python dictionaries - easy to inspect, modify, and manipulate

## Features

### Input File Features
- ✅ Simple, intuitive API with typed properties
- ✅ Context manager support for clean resource management
- ✅ Decode all SWMM 5.2.4 input file sections (60+ sections)
- ✅ Encode to .inp, JSON, and Parquet formats
- ✅ Decode from .inp, JSON, and Parquet formats
- ✅ Configurable Parquet output (single-file or multi-file modes)
- ✅ Round-trip conversion (load → modify → save) without data loss
- ✅ Full support for comments, whitespace, and formatting

### Report File Features
- ✅ Comprehensive parsing of SWMM 5.2 report files
- ✅ Extract 20+ report sections (hydraulics, hydrology, water quality)
- ✅ Node results: depth, inflow, flooding, surcharge
- ✅ Link results: flow, velocity, classification
- ✅ Pump and storage performance metrics
- ✅ LID (Low Impact Development) performance analysis
- ✅ Water quality: pollutant loads, washoff, continuity
- ✅ Groundwater and RDII tracking
- ✅ Easy result lookup by element name

### Output File Features
- ✅ Binary SWMM 5.0+ output file parsing (.out format)
- ✅ Extract simulation time series metadata and statistics
- ✅ Access node, link, and subcatchment properties
- ✅ Time index generation with full timestamp support
- ✅ Export to JSON and Parquet formats
- ✅ Pollutant tracking and water quality data
- ✅ Efficient memory usage (metadata-based access, not full time series loading)
- ✅ Element lookup by name

### Testing
- ✅ Comprehensive test suite (69 tests passing)
- ✅ Input file tests (28 tests)
- ✅ Report file tests (12 tests)
- ✅ Output file tests (29 tests)

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

### Example 1: Input File - Decode and Analyze

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

### Example 2: Report File - Analyze Simulation Results

```python
from swmm_utils import SwmmReport

with SwmmReport("results.rpt") as report:
    # Check for critical conditions
    print(f"Analysis: {report.header['title']}")
    print(f"Flow Units: {report.analysis_options.get('flow_units', 'N/A')}")
    
    # Find nodes with excessive depth
    critical_nodes = [
        node for node in report.node_depth 
        if node['maximum_depth'] > 10
    ]
    print(f"\n{len(critical_nodes)} nodes exceeded 10 ft depth")
    
    # Analyze pump efficiency
    if report.pumping_summary:
        for pump in report.pumping_summary:
            if pump['percent_utilized'] < 20:
                print(f"Pump {pump['pump_name']} underutilized: "
                      f"{pump['percent_utilized']:.1f}%")
    
    # Check system continuity
    continuity = report.continuity.get('flow_routing', {})
    error = continuity.get('continuity_error')
    if error and abs(error) > 1.0:
        print(f"Warning: Continuity error {error:.2f}%")
```

### Example 3: Convert Input Files for Analytics

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

### Example 4: Complete Workflow - Simulate and Analyze

```python
import subprocess
from swmm_utils import SwmmInput, SwmmReport

# Step 1: Modify input file
with SwmmInput("model.inp") as inp:
    # Increase all pipe roughness by 10%
    for conduit in inp.conduits:
        roughness = float(conduit.get('roughness', 0.01))
        conduit['roughness'] = str(roughness * 1.1)
    
    inp.to_inp("modified.inp")

# Step 2: Run SWMM simulation
subprocess.run([
    "./bin/runswmm", 
    "modified.inp", 
    "modified.rpt", 
    "modified.out"
])

# Step 3: Analyze results
with SwmmReport("modified.rpt") as report:
    print(f"Simulation complete!")
    print(f"Total runtime: {report.analysis_time.get('elapsed', 'N/A')}")
    
    # Compare peak flows
    for link in report.link_flow[:10]:
        print(f"{link['name']}: {link['maximum_flow']:.2f} CFS")
```

### Example 5: Batch Processing

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

### Example 6: LID Performance Analysis

```python
from swmm_utils import SwmmReport

with SwmmReport("lid_scenario.rpt") as report:
    # Analyze LID performance
    if report.lid_performance:
        # Group by subcatchment
        from collections import defaultdict
        by_subcatchment = defaultdict(list)
        
        for lid in report.lid_performance:
            by_subcatchment[lid['subcatchment']].append(lid)
        
        # Calculate total infiltration per subcatchment
        for sub, lids in by_subcatchment.items():
            total_infil = sum(lid['infil_loss'] for lid in lids)
            total_inflow = sum(lid['total_inflow'] for lid in lids)
            reduction = (total_infil / total_inflow * 100) if total_inflow > 0 else 0
            
            print(f"{sub}: {reduction:.1f}% runoff reduction via infiltration")
```

### Example 7: Round-Trip Conversion

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
pytest tests/test_rpt.py -v
```

All 40 tests pass, including comprehensive format conversion, round-trip tests, and report parsing.

## Running Examples

_Before running these examples, make sure you have the built SWMM binary executable `runswmm` in the `/bin` directory._

```bash
# Example 1: Basic input file operations
python examples/example1/example1.py

# Example 2: Report parsing with water quality
python examples/example2/example2.py
```

## Project Structure

```
swmm-utils/
├── src/
│   └── swmm_utils/              # Main package
│       ├── __init__.py          # Package exports
│       ├── inp.py               # High-level input file interface
│       ├── inp_decoder.py       # Decode .inp/JSON/Parquet → dict
│       ├── inp_encoder.py       # Encode dict → .inp/JSON/Parquet
│       ├── rpt.py               # High-level report file interface
│       └── rpt_decoder.py       # Decode .rpt → dict
├── examples/
│   ├── example1/                # Basic input file example
│   └── example2/                # Report parsing example
├── tests/
│   ├── test_inp.py              # Input file interface tests
│   ├── test_inp_decoder_encoder.py  # Core parsing tests
│   ├── test_inp_formats.py      # Format conversion tests
│   └── test_rpt.py              # Report parser tests
├── data/                        # Location for sample SWMM files
├── bin/                         # Location for swmm binary executable
├── docs/
│   └── SWMM_INPUT_FILE.md       # Complete SWMM input file reference
├── setup.py                     # Package configuration
├── requirements.txt             # Core dependencies
├── requirements-dev.txt         # Development dependencies
└── README.md                    # Project information
```

## Performance

### Input Files
Tested on various SWMM models:

- **Decode .inp**: ~0.05 seconds (240 junctions)
- **Encode to JSON**: 873 KB (240 junctions)
- **Encode to Parquet (multi-file)**: 18 files, ~110 KB total
- **Encode to Parquet (single-file)**: 1 file, ~109 KB
- **Round-trip (.inp → JSON → Parquet → .inp)**: All data preserved

### Report Files
Tested on diverse simulation results:

- **Parse .rpt**: ~0.02 seconds (small models) to ~0.5 seconds (large models)
- **Large model support**: Successfully parsed 809 KB report with 2,227 nodes
- **Memory efficient**: Processes reports on-demand without loading entire file

## Documentation

- **[README.md](README.md)** - This file (overview and quick start)
- **[examples/](examples/)** - Working examples with real SWMM models
- **[docs/SWMM_INPUT_FILE.md](docs/SWMM_INPUT_FILE.md)** - Complete SWMM input file (.inp) format reference
- **[docs/SWMM_REPORT_FILE.md](docs/SWMM_REPORT_FILE.md)** - Complete SWMM report file (.rpt) format reference  
- **[docs/SWMM_OUTPUT_FILE.md](docs/SWMM_OUTPUT_FILE.md)** - Complete SWMM output file (.out) binary format reference

## Dependencies

### Required
- Python 3.8+
- pandas >= 1.0.0 (for Parquet support)
- pyarrow >= 10.0.0 (for Parquet support)

### Development
- pytest >= 7.0.0
- pytest-cov >= 4.0.0

## Known Limitations

### Input Files
1. **Round-trip Formatting**: Some cosmetic differences
   - Comments may not be preserved in exact original positions
   - Whitespace normalized to SWMM standard format
   - All data and structure fully preserved

2. **Complex Sections**: Some sections have simplified handling
   - `[CONTROLS]` - Stored as text (complex rule syntax)
   - `[TRANSECTS]` - Multi-line format preserved

### Report Files
1. **Read-only**: Report files are parsed for reading only (no modification/encoding)
2. **Section Availability**: Not all sections appear in every report (depends on simulation settings)
3. **Format Variations**: Minor format differences across SWMM versions handled gracefully

## License

[MIT LICENSE](./LICENSE)

## Contact

For questions or issues, please open a GitHub issue.
