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
- ✅ Export to Pandas DataFrames for data analysis and manipulation
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
- ✅ Export to Pandas DataFrames for time series analysis
- ✅ Three-level DataFrame export: full data, sections, or individual elements
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

## Scenarios

### Scenario 1: Input File - Decode and Analyze

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

### Scenario 2: Report File - Analyze Simulation Results

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

### Scenario 3: Export Input Files to Pandas DataFrames

```python
from swmm_utils import SwmmInput

with SwmmInput("model.inp") as inp:
    # Export all sections as dictionary of DataFrames
    all_dfs = inp.to_dataframe()
    
    # Access specific section
    junctions_df = all_dfs['junctions']
    print(f"Model has {len(junctions_df)} junctions")
    print(junctions_df[['name', 'elevation', 'max_depth']])
    
    # Analyze with pandas operations
    conduits_df = all_dfs['conduits']
    avg_length = conduits_df['length'].astype(float).mean()
    print(f"Average conduit length: {avg_length:.2f}")
    
    # Or export specific section directly
    subcatchments_df = inp.to_dataframe('subcatchments')
    total_area = subcatchments_df['area'].astype(float).sum()
    print(f"Total subcatchment area: {total_area:.2f}")
    
    # Export to CSV for external analysis
    junctions_df.to_csv("junctions.csv", index=False)
    conduits_df.to_csv("conduits.csv", index=False)
```

### Scenario 4: Export Specific Section to DataFrame

```python
from swmm_utils import SwmmInput
import matplotlib.pyplot as plt

with SwmmInput("model.inp") as inp:
    # Export specific section to DataFrame
    junctions_df = inp.to_dataframe('junctions')
    
    print("Junctions Summary:")
    print(junctions_df[['name', 'elevation', 'max_depth', 'init_depth']])
    
    # Perform analysis on the section
    print(f"\nStatistics:")
    print(f"Number of junctions: {len(junctions_df)}")
    print(f"Average elevation: {junctions_df['elevation'].astype(float).mean():.2f}")
    print(f"Min/Max elevation: {junctions_df['elevation'].astype(float).min():.2f} / "
          f"{junctions_df['elevation'].astype(float).max():.2f}")
    
    # Filter and analyze subset
    high_junctions = junctions_df[junctions_df['elevation'].astype(float) > 100]
    print(f"\nHigh-elevation junctions (>100): {len(high_junctions)}")
    
    # Export filtered results
    high_junctions.to_csv("high_elevation_junctions.csv", index=False)
    
    # Visualize if matplotlib available
    try:
        junctions_df['elevation'].astype(float).hist(bins=20)
        plt.xlabel('Elevation')
        plt.ylabel('Count')
        plt.title('Junction Elevation Distribution')
        plt.savefig('elevation_distribution.png')
    except ImportError:
        pass
```

### Scenario 5: Convert Input Files for Analytics

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

### Scenario 6: Complete Workflow - Simulate and Analyze

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

### Scenario 8: Output File - Time Series Analysis with DataFrames

```python
from swmm_utils import SwmmOutput
import pandas as pd

# Load output file with full time series
output = SwmmOutput("simulation.out", load_time_series=True)

# Export full time series to dict of DataFrames
full_data = output.to_dataframe()

# Metadata for this simulation
print(f"Version: {full_data['metadata']['version'].iloc[0]}")
print(f"Flow units: {full_data['metadata']['flow_unit'].iloc[0]}")
print(f"Total periods: {full_data['metadata']['n_periods'].iloc[0]}")

# Access each section - MultiIndex DataFrames (timestamp, element_name)
nodes_df = full_data['nodes']        # All nodes, all timesteps
links_df = full_data['links']        # All links, all timesteps
subcatchments_df = full_data['subcatchments']  # All subcatchments, all timesteps

print(f"\nNodes: {nodes_df.shape[0]} rows, {nodes_df.shape[1]} columns")
print(f"Links: {links_df.shape[0]} rows, {links_df.shape[1]} columns")
print(f"Subcatchments: {subcatchments_df.shape[0]} rows, {subcatchments_df.shape[1]} columns")

# Find peak inflow across all timesteps (if available)
if 'value_0' in links_df.columns:
    peak_by_link = links_df.groupby(level='element_name')['value_0'].max()
    print(f"\nPeak flows by link:")
    print(peak_by_link.nlargest(5))
```

### Scenario 9: Output File - Export Specific Section

```python
from swmm_utils import SwmmOutput

output = SwmmOutput("simulation.out", load_time_series=True)

# Export only subcatchments section (no metadata)
subcatchments_df = output.to_dataframe('subcatchments')

print(f"Subcatchment Time Series Data:")
print(f"Shape: {subcatchments_df.shape} (timesteps × elements × properties)")
print(f"Index levels: {subcatchments_df.index.names}")

# Filter: all timesteps for a specific subcatchment
subcatch_name = subcatchments_df.index.get_level_values('element_name')[0]
single_subcatch = output.to_dataframe('subcatchments', subcatch_name)

print(f"\nSingle Subcatchment ({subcatch_name}):")
print(f"Time period: {single_subcatch.index.min()} to {single_subcatch.index.max()}")
print(f"Properties measured: {single_subcatch.shape[1]} values")
print(single_subcatch.head())

# Export to CSV for external analysis
single_subcatch.to_csv(f"subcatchment_{subcatch_name}.csv")
```

### Scenario 10: Output File - Single Element Time Series

```python
from swmm_utils import SwmmOutput
import matplotlib.pyplot as plt

output = SwmmOutput("simulation.out", load_time_series=True)

# Get time series for a specific link
link_name = "Conduit1"
link_df = output.to_dataframe('links', link_name)

print(f"Conduit {link_name} time series:")
print(f"Simulation period: {link_df.index.min()} to {link_df.index.max()}")
print(f"Number of timesteps: {len(link_df)}")
print("\nFirst 5 timesteps:")
print(link_df.head())

# Analyze the flow data
if 'value_0' in link_df.columns:
    flow = link_df['value_0']
    print(f"\nFlow Statistics:")
    print(f"  Peak: {flow.max():.2f}")
    print(f"  Mean: {flow.mean():.2f}")
    print(f"  Min: {flow.min():.2f}")
    
    # Plot time series if matplotlib available
    try:
        flow.plot(figsize=(12, 5))
        plt.xlabel('Time')
        plt.ylabel('Flow (CFS)')
        plt.title(f'Conduit {link_name} Flow Time Series')
        plt.tight_layout()
        plt.savefig(f'{link_name}_flow_timeseries.png')
    except ImportError:
        pass
```

### Scenario 11: Batch Processing

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

### Scenario 12: LID Performance Analysis

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

### Scenario 13: Round-Trip Conversion

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

## Running Scenarios

_Before running these scenarios, make sure you have the built SWMM binary executable `runswmm` in the `/bin` directory._

```bash
# Scenario 1: Basic input file operations
python examples/example1/example1.py

# Scenario 5: Report parsing with water quality
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
- **[examples/](examples/)** - Working scenarios with real SWMM models
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
