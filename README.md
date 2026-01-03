# SWMM Utils

Utilities for interpreting EPA SWMM input (.inp) and report (.rpt) files.

[![Tests](https://img.shields.io/badge/tests-40/40_passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.8+-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

## Overview

This project provides a comprehensive toolkit for working with EPA SWMM (Storm Water Management Model) files. It enables:

### Input Files (.inp)
- **Simple, intuitive API**: Load, modify, and save SWMM models with typed properties
- **Multi-format support**: Work with .inp, JSON, or Parquet formats
- **Context manager support**: Clean resource management with `with` statements
- **Typed properties**: Access model components (junctions, conduits, etc.) with autocomplete
- **Round-trip conversion**: Load → Modify → Save without data loss

### Report Files (.rpt)
- **Comprehensive parsing**: Extract all major sections from SWMM simulation reports
- **Structured data access**: Access simulation results through typed properties
- **Easy analysis**: Programmatically analyze hydraulic and hydrologic results
- **Multiple result types**: Node depths, link flows, pumping, storage, LID performance, water quality, and more

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/neeraip/swmm-utils.git
cd swmm-utils

# Install the package
pip install -e .
```

### Basic Usage - Input Files

```python
from swmm_utils import SwmmInput

# Load, modify, and save with context manager
with SwmmInput("model.inp") as inp:
    # Modify using typed properties
    inp.title = "My Modified Model"
    
    # Access model components with autocomplete
    print(f"Junctions: {len(inp.junctions)}")
    print(f"Conduits: {len(inp.conduits)}")
    
    # Modify model data
    for junction in inp.junctions:
        junction['elevation'] = float(junction.get('elevation', 0)) + 10
    
    # Update options
    inp.options['REPORT_STEP'] = '00:15:00'
    
    # Save to different formats
    inp.to_inp("modified.inp")
    inp.to_json("model.json")
    inp.to_parquet("model.parquet", single_file=True)

# Load from JSON or Parquet
with SwmmInput("model.json") as inp:
    print(f"Title: {inp.title}")
    inp.to_inp("from_json.inp")
```

### Basic Usage - Report Files

```python
from swmm_utils import SwmmReport

# Load and analyze simulation results
with SwmmReport("simulation.rpt") as report:
    # Access simulation metadata
    print(f"SWMM Version: {report.header['version']}")
    print(f"Flow Units: {report.analysis_options['flow_units']}")
    
    # Analyze node results
    for node in report.node_depth:
        if node['maximum_depth'] > 10:
            print(f"Deep node: {node['name']} - {node['maximum_depth']:.2f} ft")
    
    # Check pump performance
    for pump in report.pumping_summary:
        print(f"Pump {pump['pump_name']}: {pump['percent_utilized']:.1f}% utilized")
    
    # Analyze subcatchment runoff
    for sub in report.subcatchment_runoff:
        print(f"{sub['name']}: {sub['peak_runoff']:.2f} CFS peak")
    
    # Check for surcharged nodes
    if report.node_surcharge:
        print(f"Warning: {len(report.node_surcharge)} nodes surcharged!")
    
    # LID performance (if applicable)
    for lid in report.lid_performance:
        print(f"{lid['subcatchment']}/{lid['lid_control']}: "
              f"{lid['infil_loss']:.2f} in infiltrated")
```

### Advanced Usage - Lower-Level API

For more control over input files, you can use the decoder/encoder directly:

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

# Decode from JSON or Parquet
json_model = decoder.decode_json("model.json")
parquet_model = decoder.decode_parquet("model.parquet")
```

## API Overview

### SwmmInput (Recommended for Input Files)

The high-level interface with typed properties and context manager support:

- **Constructor**: `SwmmInput(filepath=None)` - Load from .inp, .json, or .parquet file (optional)
- **Context Manager**: Use with `with` statement for clean resource management
- **Typed Properties**: Access sections like `input.title`, `input.junctions`, `input.conduits`, etc.
- **Output Methods**: 
  - `to_inp(filepath)` - Save to .inp format
  - `to_json(filepath, pretty=True)` - Save to JSON format
  - `to_parquet(filepath, single_file=False)` - Save to Parquet format

**Available Typed Properties:**
- `title` (str)
- `options` (dict)
- `junctions`, `outfalls`, `storage` (lists)
- `conduits`, `pumps`, `orifices`, `weirs` (lists)
- `subcatchments`, `raingages` (lists)
- `curves`, `timeseries`, `controls`, `pollutants`, `landuses` (lists)

### SwmmReport (For Report Files)

The high-level interface for reading SWMM simulation results:

- **Constructor**: `SwmmReport(filepath=None)` - Load from .rpt file (optional)
- **Context Manager**: Use with `with` statement for clean resource management
- **Typed Properties**: Access results like `report.node_depth`, `report.link_flow`, etc.

**Available Report Sections:**
- `header` - Version, build, title
- `element_count` - Count of model elements
- `analysis_options` - Simulation settings
- `continuity` - Mass balance (runoff, routing, quality)
- `subcatchment_runoff` - Runoff summary by subcatchment
- `node_depth` - Node depth statistics
- `node_inflow` - Node inflow statistics
- `node_flooding` - Flooded nodes
- `node_surcharge` - Surcharged nodes
- `storage_volume` - Storage unit performance
- `outfall_loading` - Outfall loading statistics
- `link_flow` - Link flow statistics
- `flow_classification` - Flow regime classification
- `conduit_surcharge` - Surcharged conduits
- `pumping_summary` - Pump performance
- `lid_performance` - LID control performance
- `groundwater_summary` - Groundwater continuity
- `quality_routing_continuity` - Water quality mass balance
- `subcatchment_washoff` - Pollutant washoff
- `link_pollutant_load` - Pollutant loads in links
- `analysis_time` - Simulation timing

### SwmmInputDecoder & SwmmInputEncoder

Lower-level API for more control over input files:

- **Decoder Methods**:
  - `decode_file(filepath)` - Decode .inp file to dict
  - `decode_json(filepath)` - Decode JSON file to dict
  - `decode_parquet(path)` - Decode Parquet file/directory to dict

- **Encoder Methods**:
  - `encode_to_inp_file(data, filepath)` - Encode dict to .inp file
  - `encode_to_json(data, filepath, pretty=True)` - Encode dict to JSON
  - `encode_to_parquet(data, path, single_file=False)` - Encode dict to Parquet

### SwmmReportDecoder

Lower-level API for report file parsing:

- **Decoder Methods**:
  - `decode_file(filepath)` - Decode .rpt file to dict

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
```

The architecture uses Python dictionaries as the in-memory data model:

1. **SwmmInput/SwmmReport**: High-level interfaces with typed properties and context managers
2. **Decoders**: Read .inp/.rpt/JSON/Parquet files into Python dict structures
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
- ✅ Comprehensive test suite (67 tests passing)
- ✅ Input file tests (28 tests)
- ✅ Report file tests (12 tests)
- ✅ Output file tests (27 tests)

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

### Example 7: Batch Processing

```python
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
