# SWMM Output File (.out) Documentation

## Overview

EPA SWMM output files are binary files with a `.out` extension that contain time series data from a drainage system simulation. These files store detailed computational results for all network elements at each time step, including depths, flows, velocities, volumes, and water quality parameters. The binary format provides efficient storage and fast access to large quantities of simulation data.

**Key Characteristics:**
- **Format**: Binary file with fixed-width records and specific data type encoding
- **Structure**: Header section followed by metadata and time series data records
- **Content**: Node depths, link flows, subcatchment runoff, and pollutant concentrations
- **Efficiency**: Compact storage enables quick data retrieval without text parsing overhead
- **Version**: SWMM 5.0+ binary format specification

## File Structure Overview

SWMM output files follow this structure:

```
┌─────────────────────────────────────┐
│      File Header (4-byte records)   │
│  - Magic number (verification)      │
│  - Version & flow unit info         │
│  - Element counts (nodes, links)    │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│    Metadata Section                 │
│  - Element labels (names)           │
│  - Element properties               │
│  - Time index info                  │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│    Time Series Data Records         │
│  - One record per time step         │
│  - All element values per record    │
│  - 4-byte float values per property │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│    File Footer                      │
│  - Ending magic number              │
│  - Statistics (if available)        │
└─────────────────────────────────────┘
```

---

## Binary Format Details

### Data Types and Encoding

All numeric values in the binary file are stored as **4-byte integers or floats**:

| Data Type  | Size | Format            | Range                            |
| ---------- | ---- | ----------------- | -------------------------------- |
| **INT**    | 4    | Little-endian int | -2,147,483,648 to +2,147,483,647 |
| **FLOAT**  | 4    | IEEE 754 float    | ±3.4×10⁻³⁸ to ±3.4×10³⁸          |
| **STRING** | Var. | Null-terminated   | Max 32 chars typically           |

### Byte Order

- **Endianness**: Little-endian (Intel x86 standard)
- **Alignment**: 4-byte word alignment throughout
- **Padding**: No padding between records

---

## File Header Section

### Magic Number Validation

The file begins with a **magic number** used to identify and verify the output file format:

```
Byte Offset: 0-3
Value:       516,114,522 (0x1EC2A13A)
Data Type:   4-byte integer (little-endian)
Purpose:     File format identification and endianness verification
```

**Purpose**: 
- Confirms the file is a valid SWMM binary output file
- Detects endianness mismatches (if read as different value)
- Flags corrupted or non-output files

**Verification in Code**:
```python
magic_number = struct.unpack('<I', file.read(4))[0]
if magic_number != 516114522:  # 0x1EC2A13A
    raise ValueError("Invalid SWMM output file")
```

---

### Version and Configuration

Following the magic number, the header contains version and configuration information:

```
Position    Size    Type        Field Name              Description
────────────────────────────────────────────────────────────────
4-7         4       INT         VERSION                 SWMM version (e.g., 51200 = 5.1.20)
8-11        4       INT         FLOW_UNITS              Flow unit encoding:
                                                        0=CFS, 1=GPM, 2=MPS, 3=MGD,
                                                        4=IMGD, 5=AFD, 6=LPS, 7=MLD,
                                                        8=CMH, 9=CMD
12-15       4       INT         N_SUBCATCH              Number of subcatchments
16-19       4       INT         N_NODES                 Number of nodes
20-23       4       INT         N_LINKS                 Number of links
24-27       4       INT         N_POLLUTANTS            Number of water quality constituents
28-31       4       INT         POLLUT_CODE             Pollutant code/version
32-35       4       INT         FLOW_CODE               Flow routing code
36-39       4       INT         SWEEP_OUT               Street sweeping indicator
```

**Example Header Dump**:
```
Magic Number:      516114522
Version:           51200 (SWMM 5.1.20)
Flow Units:        0 (CFS - Cubic Feet per Second)
Subcatchments:     15
Nodes:             28
Links:             32
Pollutants:        2 (TSS, Heavy Metals)
```

---

### Reporting Parameters

Additional metadata about the simulation reporting:

```
Position    Size    Type        Field Name              Description
────────────────────────────────────────────────────────────────
40-43       4       INT         N_VARIABLES             Total properties per element type
44-47       4       INT         START_DATE_INT          Start date as integer
48-51       4       INT         START_TIME_INT          Start time as integer
52-55       4       FLOAT       REPORT_INTERVAL         Reporting time interval (seconds)
56-59       4       INT         END_DATE_INT            End date as integer
60-63       4       INT         END_TIME_INT            End time as integer
64-67       4       INT         N_PERIODS               Number of reporting periods/time steps
```

**Date/Time Encoding**:
- Dates stored as: `(year-1900)*10000 + month*100 + day`
- Times stored as: `hour*3600 + minute*60 + second`

**Example**:
```
Start Date: 120001 → January 1, 2020
Start Time: 0      → 00:00:00
End Date:   120105 → January 5, 2020
End Time:   86399  → 23:59:59
Periods:    2880   → 2880 time steps = 5 days at hourly reporting
```

---

## Metadata Section

### Element Names (Labels)

Following the header, element names are stored sequentially:

```
Structure per Element:
  - Length byte (1 byte): Number of characters in name (N)
  - Name (N bytes): ASCII string without null terminator
  - Padding (varies): To align to 4-byte boundary if needed

Order of Names:
  1. All subcatchment names
  2. All node names
  3. All link names

Total Names: N_SUBCATCH + N_NODES + N_LINKS
```

**Example Format**:
```
[8]"SubArea1"
[12]"Junction_001"
[4]"Pipe1"
[6]"Outlet"
...
```

**Parsing Logic**:
```python
names = []
for i in range(n_subcatch + n_nodes + n_links):
    name_len = struct.unpack('B', file.read(1))[0]
    name = file.read(name_len).decode('ascii')
    names.append(name)
    # Align to next 4-byte boundary if needed
```

---

### Element Properties

After names, element properties are defined for nodes, links, and pollutants:

```
For Nodes:
  - Property count (4 bytes): INT
  - For each property:
    * Code (4 bytes): INT (usually -1 or node property code)
    * Unit code (4 bytes): INT (elevation units, etc.)

For Links:
  - Property count (4 bytes): INT
  - Similar structure for link properties

For Pollutants:
  - Property count (4 bytes): INT
  - For each pollutant:
    * Name (variable): ASCII string with length prefix
    * Units code (4 bytes): INT
```

**Property Codes**:
- Nodes: Depth, Elevation, Head, Quality, Lateral Inflow
- Links: Flow, Depth, Volume, Velocity, Quality
- Subcatchments: Runoff, Infiltration, Quality

---

### Time Index

The metadata section concludes with timing information:

```
Time Index Structure:
  - Simulation start date/time (already in header)
  - Reporting interval in seconds (already in header)
  - Number of periods (already in header)
  - Computed Time Index:
    * Period 1: Start time + 0 × Interval
    * Period 2: Start time + 1 × Interval
    * Period 3: Start time + 2 × Interval
    * ...
    * Period N: Start time + (N-1) × Interval
```

**Example Time Index** (hourly reporting from Jan 1, 2020):
```
2020-01-01 00:00:00
2020-01-01 01:00:00
2020-01-01 02:00:00
2020-01-01 03:00:00
...
2020-01-05 23:00:00
```

---

## Time Series Data Records

### Record Structure

The bulk of the file contains time series data organized as **fixed-width records**, one per reporting period:

```
Per Time Step Record:
  ┌─────────────────────────────────────────────┐
  │ Time Step: 1                                │
  │ - Subcatchment 1, Variable 1: 4 bytes       │
  │ - Subcatchment 1, Variable 2: 4 bytes       │
  │ - ... (all subcatchment variables)          │
  │ - Node 1, Variable 1: 4 bytes               │
  │ - Node 1, Variable 2: 4 bytes               │
  │ - ... (all node variables)                  │
  │ - Link 1, Variable 1: 4 bytes               │
  │ - Link 1, Variable 2: 4 bytes               │
  │ - ... (all link variables)                  │
  │ - System Variable 1: 4 bytes                │
  │ - System Variable 2: 4 bytes                │
  │ - ... (system-level variables)              │
  └─────────────────────────────────────────────┘

Record Size: (N_SUBCATCH + N_NODES + N_LINKS) × Variables × 4 bytes
```

### Data Values by Element Type

#### Subcatchment Variables (per subcatchment, per time step)

| Variable Index | Name              | Units          | Description                   |
| -------------- | ----------------- | -------------- | ----------------------------- |
| 0              | Rainfall          | in/hr or mm/hr | Precipitation rate            |
| 1              | Snowmelt          | in/hr or mm/hr | Snowmelt rate                 |
| 2              | Infiltration      | in/hr or mm/hr | Infiltration rate             |
| 3              | Runoff            | CFS/LPS/etc.   | Surface runoff flow rate      |
| 4              | Groundwater Flow  | CFS/LPS/etc.   | Subsurface flow rate          |
| 5              | Pollutant Quality | mg/L or units  | Water quality at subcatchment |

**Example Interpretation**:
```
Subcatchment "S1" at time step 5 (1 hour into simulation):
  Rainfall:        0.25 in/hr
  Snowmelt:        0.0 in/hr
  Infiltration:    0.08 in/hr
  Runoff:          12.5 CFS
  Groundwater:     0.3 CFS
  Quality TSS:     150 mg/L
```

#### Node Variables (per node, per time step)

| Variable Index | Name           | Units         | Description                              |
| -------------- | -------------- | ------------- | ---------------------------------------- |
| 0              | Depth          | ft or m       | Water depth above invert                 |
| 1              | Head           | ft or m       | Hydraulic grade line (elevation + depth) |
| 2              | Volume         | acre-ft or m³ | Water volume stored                      |
| 3              | Lateral Inflow | CFS/LPS/etc.  | External flow input                      |
| 4              | Total Inflow   | CFS/LPS/etc.  | All sources combined                     |
| 5              | Quality        | mg/L or units | Water quality concentration              |

**Example Interpretation**:
```
Node "J1" at time step 10 (during peak storm):
  Depth:          4.5 ft
  Head:           99.5 ft (elevation 95 + depth 4.5)
  Volume:         12,500 acre-ft
  Lateral Inflow: 5.2 CFS (subcatchment runoff)
  Total Inflow:   15.8 CFS (includes upstream flow)
  Quality TSS:    85 mg/L
```

#### Link Variables (per link, per time step)

| Variable Index | Name     | Units         | Description                    |
| -------------- | -------- | ------------- | ------------------------------ |
| 0              | Flow     | CFS/LPS/etc.  | Flow rate through link         |
| 1              | Depth    | ft or m       | Flow depth (for open channels) |
| 2              | Velocity | ft/s or m/s   | Average flow velocity          |
| 3              | Volume   | acre-ft or m³ | Water volume in link           |
| 4              | Quality  | mg/L or units | Water quality in flow          |

**Example Interpretation**:
```
Link "C1" at time step 15:
  Flow:           25.3 CFS
  Depth:          1.8 ft (within 2-ft diameter pipe)
  Velocity:       3.2 ft/s
  Volume:         250 acre-ft
  Quality TSS:    120 mg/L
```

#### System Variables (whole system, per time step)

| Variable | Name                | Description                    |
| -------- | ------------------- | ------------------------------ |
| 0        | Total Outfall Flow  | Combined discharge from system |
| 1        | Total Flooding Loss | Water overflowing surface      |
| 2        | Total Infiltration  | Total infiltration in system   |
| 3        | Total Evaporation   | Total evaporation losses       |

---

### Record Access Pattern

To read a specific value from a time series record:

```python
def get_value_at_time_step(file_obj, time_step, element_type, element_index, variable_index):
    """
    Read a single value from the output file.
    
    Args:
        file_obj: Open file handle
        time_step: 0-based time step index
        element_type: 'subcatchment', 'node', or 'link'
        element_index: 0-based element index
        variable_index: 0-based variable index
    """
    # Calculate offset in bytes
    record_size = (N_SUBCATCH + N_NODES + N_LINKS) * N_VARIABLES * 4
    record_offset = METADATA_SIZE + time_step * record_size
    
    # Calculate position within record
    if element_type == 'subcatchment':
        element_offset = element_index * N_VARIABLES + variable_index
    elif element_type == 'node':
        element_offset = (N_SUBCATCH + element_index) * N_VARIABLES + variable_index
    else:  # link
        element_offset = (N_SUBCATCH + N_NODES + element_index) * N_VARIABLES + variable_index
    
    # Read value
    file_obj.seek(record_offset + element_offset * 4)
    value = struct.unpack('<f', file_obj.read(4))[0]
    return value
```

---

## File Footer Section

### Ending Magic Number

The file concludes with another **magic number** for verification:

```
Position:   File size - 4 bytes
Value:      516114522 (0x1EC2A13A, same as start)
Data Type:  4-byte integer (little-endian)
Purpose:    Confirms file completeness and no truncation
```

---

## Flow Unit Codes

The output file encodes flow units as integer codes:

```python
FLOW_UNITS = {
    0: 'CFS',    # Cubic Feet per Second (US)
    1: 'GPM',    # Gallons per Minute (US)
    2: 'MPS',    # Meters per Second (Metric)
    3: 'MGD',    # Million Gallons per Day (US)
    4: 'IMGD',   # Imperial Million Gallons per Day
    5: 'AFD',    # Acre-Feet per Day
    6: 'LPS',    # Liters per Second (Metric)
    7: 'MLD',    # Million Liters per Day (Metric)
    8: 'CMH',    # Cubic Meters per Hour (Metric)
    9: 'CMD'     # Cubic Meters per Day (Metric)
}
```

---

## Parsing with SwmmOutputDecoder

The `SwmmOutputDecoder` class extracts binary data from output files:

```python
from swmm_utils import SwmmOutputDecoder

# Create decoder for binary file parsing
decoder = SwmmOutputDecoder("simulation.out")

# Access parsed data
header = decoder.header                # Version, counts, units
metadata = decoder.metadata            # Labels, properties
time_index = decoder.time_index        # Timestamps for each period

# Low-level data access (4-byte values per time step)
node_flow = decoder.get_node_data("Node_001", "depth")
link_flow = decoder.get_link_data("Conduit_01", "flow")
```

---

## High-Level Interface with SwmmOutput

The `SwmmOutput` class provides user-friendly access to output data:

### Properties Available

```python
from swmm_utils import SwmmOutput

output = SwmmOutput("simulation.out")

# Version and configuration
print(output.version)                  # "5.2.0"
print(output.flow_unit)                # "CFS"
print(output.start_date)               # datetime object
print(output.start_time)               # time object
print(output.end_date)                 # datetime object
print(output.end_time)                 # time object

# Simulation periods
print(output.report_interval)          # timedelta for reporting interval
print(output.n_periods)                # Number of time steps
print(output.time_index)               # List of all timestamps

# Element counts
print(output.n_subcatch)               # Number of subcatchments
print(output.n_nodes)                  # Total nodes
print(output.n_links)                  # Total links
print(output.n_pollutants)             # Number of water quality constituents

# Element labels
print(output.subcatch_labels)          # List of subcatchment names
print(output.node_labels)              # List of node names
print(output.link_labels)              # List of link names
print(output.pollutant_labels)         # List of pollutant names
print(output.pollutant_units)          # Units for each pollutant

# Access all properties at once
props = output.properties              # Dictionary of all above
```

### Methods for Data Access

```python
# Get time series data for specific elements
node_data = output.get_node("Junction_001")           # Depth, head, volume, etc.
link_data = output.get_link("Pipe_001")               # Flow, depth, velocity, etc.
subcatch_data = output.get_subcatchment("Sub_Area_1") # Rainfall, runoff, etc.

# Summary statistics
summary = output.summary()             # Summary statistics across simulation

# Metadata
print(output.properties)               # All accessible properties
```

---

## Export Capabilities

### JSON Export

Convert output file data to JSON format for compatibility with other tools. You control what gets loaded at initialization with the `load_time_series` parameter:

```python
from swmm_utils import SwmmOutput

# Option 1: Load metadata only (default, fast, small file)
output = SwmmOutput("simulation.out")
output.to_json("output.json", pretty=True)
# Output size: ~4-10 KB
# Export speed: <100ms

# Option 2: Load with full time series data (comprehensive analysis)
output = SwmmOutput("simulation.out", load_time_series=True)
output.to_json("output_full.json", pretty=True)
# Output size: 100-1000x larger (can be 10-100+ MB)
# Export speed: 0.1-5 seconds (proportional to time steps)
```

**Key API Point**: The `load_time_series` parameter is specified at **initialization**, not at export time. This gives you explicit control over when data is loaded and avoids hidden I/O operations during export.

**Metadata Only Export** (default, `load_time_series=False`):
- Contains: Header, metadata, labels, properties, summary
- Size: ~4-10 KB
- Speed: <100ms
- Best for: Quick inspection, metadata queries, web/API usage
- Example: `output = SwmmOutput("file.out")`

**Full Export with Time Series** (`load_time_series=True`):
- Contains: Everything above + all time step values for every element
- Size: 100-1000x larger (can be 10-100+ MB)
- Speed: 0.1-5 seconds (depends on simulation length)
- Best for: Complete data analysis, archival, external tools, data science
- Example: `output = SwmmOutput("file.out", load_time_series=True)`
- Trade-off: Larger files but complete simulation data

**JSON Structure with Time Series**:
```json
{
  "header": {...},
  "metadata": {...},
  "summary": {...},
  "time_series": {
    "nodes": {
      "J1": [{"timestamp": "...", "values": [...]}, ...],
      "J2": [...]
    },
    "links": {...},
    "subcatchments": {...},
    "system": [...]
  }
}
```

**Conditional Loading Example**:
```python
from pathlib import Path

out_file = Path("simulation.out")
file_size = out_file.stat().st_size

# Only load time series for smaller files
load_ts = file_size < 10_000_000  # < 10 MB

output = SwmmOutput(out_file, load_time_series=load_ts)
output.to_json("output.json")
```

### Parquet Export (Single-File Mode)

Export to Apache Parquet columnar format for efficient storage and analysis:

```python
# Single-file mode (simple, compact)
output.to_parquet("output.parquet", single_file=True)

# Output size: ~2-4 KB for typical models
# Best for: Simple storage, compatibility with pandas/dask
```

### Parquet Export (Multi-File Mode)

Export to separate Parquet files for large datasets:

```python
# Multi-file mode (organized by element type)
output.to_parquet("output_parquet/", single_file=False)

# Creates separate files:
#   - nodes.parquet: Node metadata and statistics
#   - links.parquet: Link metadata and statistics
#   - subcatchments.parquet: Subcatchment metadata
#   - summary.parquet: System-level summary
```

---

## Common Usage Patterns

### Loading and Inspecting an Output File (Metadata Only)

```python
from swmm_utils import SwmmOutput

# Load output file - metadata only by default (fast, lightweight)
output = SwmmOutput("simulation.out")

# Basic information
print(f"Simulation: {output.start_date} to {output.end_date}")
print(f"Elements: {output.n_nodes} nodes, {output.n_links} links")
print(f"Time steps: {output.n_periods}")

# Export for quick analysis
output.to_json("output.json", pretty=True)           # Small file (~4 KB)
output.to_parquet("output.parquet", single_file=True)
```

### Complete Analysis with Time Series Data

```python
from swmm_utils import SwmmOutput

# Load with full time series data - specify at initialization
output = SwmmOutput("simulation.out", load_time_series=True)

# Now you have access to all timestep values
print(f"Elements: {output.n_nodes} nodes, {output.n_links} links")
print(f"Time steps: {output.n_periods}")

# Export complete data for external analysis
output.to_json("output_complete.json", pretty=True)  # Large file (~500x)

# The JSON now includes time_series data for nodes, links, subcatchments, system
```

### Finding Peak Conditions

```python
# Not directly available from metadata, but can be inferred from:
# - Node counts and names
# - Reporting intervals
# - Element property codes

summary = output.summary()
print(f"Peak flow: {summary.get('max_link_flow')} CFS")
print(f"Peak depth: {summary.get('max_node_depth')} ft")
```

### Water Quality Analysis

```python
# Check pollutants
print(f"Pollutants: {output.pollutant_labels}")
print(f"Units: {output.pollutant_units}")

# Export for detailed quality analysis
output.to_parquet("output_parquet/")
```

---

## Binary File Size Estimation

Approximate file sizes based on model complexity:

```
Small Model (5 nodes, 5 links, 100 time steps):
  Header:        ~200 bytes
  Metadata:      ~500 bytes
  Data:          100 × 5 × 5 × 4 × 6 = ~60 KB
  Total:         ~61 KB

Medium Model (30 nodes, 40 links, 1000 time steps):
  Header:        ~200 bytes
  Metadata:      ~2 KB
  Data:          1000 × 70 × 4 × 6 = ~1.7 MB
  Total:         ~1.7 MB

Large Model (100 nodes, 150 links, 5000 time steps):
  Header:        ~200 bytes
  Metadata:      ~5 KB
  Data:          5000 × 250 × 4 × 6 = ~30 MB
  Total:         ~30 MB
```

---

## Error Handling

### Common Issues and Solutions

| Issue                    | Cause                        | Solution                                       |
| ------------------------ | ---------------------------- | ---------------------------------------------- |
| **Invalid magic number** | Corrupted or non-output file | Re-run simulation, verify file is .out format  |
| **Version mismatch**     | Different SWMM version       | Check simulation version matches parser        |
| **Truncated file**       | Incomplete simulation        | Re-run simulation to completion                |
| **Out of bounds**        | Invalid element index        | Verify element name matches available elements |
| **Missing pollutants**   | Quality analysis not run     | Enable quality analysis in simulation          |

### Validation

```python
from swmm_utils import SwmmOutput

try:
    output = SwmmOutput("simulation.out")
except ValueError as e:
    print(f"Error: {e}")
    # File may be corrupted or invalid format

# Verify data integrity
if output.n_periods == 0:
    print("Warning: No time series data found")

if output.n_pollutants > 0 and not output.pollutant_labels:
    print("Warning: Pollutants reported but labels missing")
```

---

## Performance Considerations

### File Access Speed

- **Sequential read**: ~100 MB/s (entire file)
- **Random access to single value**: ~1-5 ms
- **Full metadata parse**: ~10-50 ms for typical files

### Memory Usage

- **In-memory storage**: Minimal (only metadata loaded)
- **Time series access**: On-demand from file
- **Export to JSON/Parquet**: Temporary buffer ~1-2 MB per operation

### Optimization Tips

1. **Use single-file Parquet export** for quick analysis
2. **Stream data** rather than loading entire time series
3. **Filter time periods** before export for large simulations
4. **Use multi-file Parquet** for parallel processing workflows

---

## Appendix: Binary Format Summary

### Header Layout (68 bytes minimum)

```
Offset  Size  Type    Field
──────────────────────────────────────
0-3     4     INT     Magic Number (516114522)
4-7     4     INT     SWMM Version
8-11    4     INT     Flow Units Code
12-15   4     INT     Number of Subcatchments
16-19   4     INT     Number of Nodes
20-23   4     INT     Number of Links
24-27   4     INT     Number of Pollutants
28-31   4     INT     Pollutant Code
32-35   4     INT     Flow Code
36-39   4     INT     Sweep Out Flag
40-43   4     INT     Number of Variables
44-47   4     INT     Start Date (integer)
48-51   4     INT     Start Time (integer)
52-55   4     FLOAT   Report Interval (seconds)
56-59   4     INT     End Date (integer)
60-63   4     INT     End Time (integer)
64-67   4     INT     Number of Time Periods
```

### Record Access Formula

```
Record Position = HeaderSize + MetadataSize + (TimeStep × RecordSize)
Value Offset = (ElementIndex × VariablesPerElement + VariableIndex) × 4

RecordSize = (N_SUBCATCH + N_NODES + N_LINKS) × VariablesPerElement × 4
```

---

## References and Tools

- **SWMM Documentation**: https://www.epa.gov/water-research/storm-water-management-model-swmm
- **Binary Format Reference**: SWMM source code (output.c)
- **Analysis Tools**: Pandas, NumPy, Apache Spark

---

## Version History

| Version | Date | Changes                             |
| ------- | ---- | ----------------------------------- |
| 5.2     | 2023 | Current standard SWMM version       |
| 5.1     | 2015 | Added advanced infiltration models  |
| 5.0     | 2011 | Initial binary format specification |

---

## Conclusion

The SWMM output file format provides an efficient binary storage mechanism for simulation time series data. Understanding its structure enables programmatic access to simulation results, integration with data analysis workflows, and development of custom analysis tools. The `SwmmOutput` and `SwmmOutputDecoder` classes abstract away binary format complexity, providing intuitive Python interfaces for working with output files.
