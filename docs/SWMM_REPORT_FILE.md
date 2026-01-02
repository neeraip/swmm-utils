# SWMM Report File (.rpt) Documentation

## Overview

EPA SWMM (Storm Water Management Model) report files are text-based output files with a `.rpt` extension that contain the results of a drainage system simulation. These files present detailed analysis results including continuity checks, element statistics, hydrographs, and performance metrics in a human-readable format.

**Key Characteristics:**
- **Format**: Plain text files with formatted tables and summaries
- **Structure**: Multiple sections with clear headers and delimited data
- **Content**: Simulation results, statistics, and summary data
- **Case Sensitivity**: Generally case-insensitive for section headers
- **Width**: Typically formatted for 80-100 character width

## File Structure

Report files follow a consistent structure with:
1. **Header** - Version information and project title
2. **Element Count** - Number of nodes, links, and other elements
3. **Analysis Options** - Simulation settings and parameters
4. **Continuity** - Mass balance checks
5. **Results Sections** - Element-by-element simulation results
6. **Summary Sections** - Aggregated statistics and analysis
7. **Analysis Time** - Computational timing information

---

## Header and Metadata Sections

### Report Header
**Purpose**: Identifies the SWMM version, build number, and project title

**Format**: ASCII art with key information

**Example**:
```
EPA STORM WATER MANAGEMENT MODEL - VERSION 5.2
Build 5.2.4
```

**Includes**:
- SWMM Version number
- Build number
- Project title (from `.inp` file `[TITLE]` section)
- Report generation date/time

---

### Element Count
**Purpose**: Summarizes the number of network elements in the model

**Typical Contents**:

| Element Type      | Description                                                    |
| ----------------- | -------------------------------------------------------------- |
| **Subcatchments** | Number of drainage subcatchments                               |
| **Nodes**         | Total number of nodes (junctions, storage, outfalls, dividers) |
| **Links**         | Total number of links (conduits, pumps, orifices, weirs)       |
| **Outfalls**      | Number of outfall nodes                                        |
| **Pollutants**    | Number of water quality constituents                           |

**Example**:
```
Element Count
=============

Number of subcatchments ................ 42
Number of nodes ........................ 58
Number of links ........................ 65
Number of pollutants ................... 2
```

---

### Analysis Options
**Purpose**: Reports the simulation settings used in the analysis

**Common Options Reported**:

| Option                  | Description                     | Typical Values                   |
| ----------------------- | ------------------------------- | -------------------------------- |
| **Flow Units**          | Units for flow calculations     | CFS, GPM, LPS, etc.              |
| **Process Models**      | Hydrology and hydraulic methods | KINWAVE, DYNWAVE, etc.           |
| **Infiltration Model**  | Soil infiltration method        | HORTON, GREEN_AMPT, CURVE_NUMBER |
| **Flow Routing**        | Hydraulic routing scheme        | STEADY, KINWAVE, DYNWAVE         |
| **Starting Conditions** | Initial model state             | DRY, WET, USER                   |
| **Time Step**           | Computational time intervals    | Routing step, report step, etc.  |

**Example**:
```
Analysis Options
================

Flow Units ........................... CFS
Process Models:
  Hydrology .......................... AREA
  Infiltration ...................... GREEN_AMPT
  Flow Routing ...................... DYNWAVE
  Ponding Allowed ................... YES
Starting Conditions ................. DRY
  Start Date ........................ 01/01/2023
  Start Time ........................ 00:00:00
  End Date .......................... 12/31/2023
  End Time .......................... 23:59:59
```

---

## Continuity Sections

### Mass Balance / Continuity
**Purpose**: Verifies conservation of mass (runoff and routing continuity)

**Two Main Subsections**:

#### 1. Runoff Continuity (Hydrologic)
Checks water balance for runoff generation at subcatchments

**Typical Fields**:
- Total Precipitation: Rainfall input
- Evaporation Loss: Evaporated water
- Infiltration Loss: Water lost to infiltration
- Surface Runoff: Water leaving as runoff
- Final Storage: Water retained in surface storage
- Continuity Error: Percentage error in mass balance

**Example**:
```
Runoff Continuity
=================
                                      inches        inches
Initial Soil Moisture ..................  1.234        1.234
Runoff Area ...........................  50.000       50.000
...
Total Precipitation .................  15.432       15.432
```

#### 2. Flow Routing Continuity (Hydraulic)
Checks water balance for hydraulic routing through the network

**Typical Fields**:
- Dry Weather Inflow: Continuous baseflow
- Wet Weather Inflow: Stormwater inflow
- Groundwater Inflow: Subsurface water
- I/I Inflow: Infiltration/Inflow
- External Inflow: External sources
- Flooding Losses: Water lost to surface flooding
- Outfall Flows: Water leaving the system
- Continuity Error: Percentage error

**Example**:
```
Flow Routing Continuity
=======================
Dry Weather Inflow ..................  0.050 MG
Wet Weather Inflow ................. 12.345 MG
Groundwater Inflow .................. 0.012 MG
...
Total Outfall Flow ................. 12.350 MG
Continuity Error .................... 0.04%
```

---

## Element Results Sections

### Subcatchment Runoff Summary
**Purpose**: Results for each subcatchment showing precipitation, infiltration, and runoff

**Fields per Subcatchment**:
- Total Precip: Total precipitation (in/mm)
- Total Runoff: Total runoff volume
- Total Infiltr: Infiltration volume
- Avg Runoff Rate: Average runoff rate
- Peak Runoff Rate: Maximum runoff rate
- Runoff Coeff: Runoff coefficient (runoff/precip)

**Format**: Table with rows for each subcatchment

---

### Node Depth Summary
**Purpose**: Water depth statistics at each node throughout simulation

**Fields per Node**:
- Avg Depth: Average water depth
- Max Depth: Maximum water depth
- Max HGL: Maximum hydraulic grade line elevation
- Time of Max: Time when maximum occurred
- Reported?: Whether node depth was reported in results

**Format**: Table with rows for each node

---

### Node Inflow Summary
**Purpose**: Flow contributions to each node from various sources

**Fields per Node**:
- Lateral Inflow: Subcatchment runoff and external inflows
- Total Inflow: All sources combined
- Max Inflow: Maximum inflow during simulation
- Max %Full: Maximum percent of conduit capacity used when leaving node

---

### Node Flooding Summary
**Purpose**: Identifies nodes where capacity is exceeded (optional section)

**Indicates**:
- Nodes that flood to the surface
- Total flooding volume at each node
- Number of times flooding occurs
- Whether flooding causes surcharge or external overflow

---

### Outfall Loading Summary
**Purpose**: Pollutant and flow characteristics at outfall nodes

**Includes**:
- Flow volume exiting each outfall
- Pollutant concentrations and loads
- Mass balance verification

---

### Link Flow Summary
**Purpose**: Flow statistics for conduits, pumps, weirs, and orifices

**Fields per Link**:
- Flow Type: SUBCRITICAL, SUPERCRITICAL, etc.
- Avg Flow: Average flow rate
- Max Flow: Maximum flow rate
- Max %Full: Maximum percent of link capacity
- Max Depth: Maximum flow depth (for conduits)
- Time of Max: When maximum flow occurred

---

### Pumping Summary
**Purpose**: Detailed pump operation statistics

**Fields per Pump**:
- Percent Time On: What percentage of time the pump ran
- On/Off Cycles: Number of times pump started/stopped
- Min Flow: Minimum flow when pump was running
- Avg Flow: Average pump flow
- Max Flow: Maximum pump flow
- Total Volume: Total volume pumped
- Energy Usage: Power consumption (if applicable)

---

### Storage Volume Summary
**Purpose**: Statistics for storage nodes/basins

**Fields per Storage Node**:
- Avg Volume: Average stored water volume
- Max Volume: Maximum stored volume
- Evap Loss: Water lost to evaporation
- Seep Loss: Water lost to seepage
- Avg Depth: Average water depth
- Max Depth: Maximum water depth
- Initial Volume: Starting storage volume
- Final Volume: Ending storage volume

---

### Node Surcharge Summary
**Purpose**: Nodes that surcharge (exceed crown elevation)

**Indicates**:
- Which nodes exceed their maximum capacity
- Duration and extent of surcharge
- Maximum surcharge depth above crown elevation

---

### Conduit Surcharge Summary
**Purpose**: Conduits operating under pressure (optional section)

**Indicates**:
- Full-flow conduits operating under pressure/surcharged conditions
- Number of surcharge hours
- Whether surcharge is continuous or intermittent

---

## Water Quality Sections (Optional)

### LID Performance Summary
**Purpose**: Low Impact Development (LID) control performance

**Fields per LID**:
- Design Storm: Storm event evaluated
- Outflow Volume: Water exiting the LID
- Avg Outflow Rate: Average flow rate
- Pollutant Removal: Percentage of pollutants removed

---

### Groundwater Summary
**Purpose**: Groundwater/infiltration results (if GWF model used)

**Includes**:
- Total groundwater flow
- Evaporation from groundwater
- Lateral groundwater flow
- Deep percolation

---

### Quality Routing Continuity
**Purpose**: Mass balance check for water quality constituents

**For Each Pollutant**:
- Wet Weather Inflow: Input mass
- Groundwater Inflow: Subsurface input
- Surface Runoff: Mass leaving as runoff
- Pollutant Loss: Mass removed (settling, decay, etc.)
- Continuity Error: Percentage error in mass balance

---

### Subcatchment Washoff
**Purpose**: Pollutant washoff from subcatchments

**Fields per Pollutant/Subcatchment**:
- Pollutant Name
- Total Buildup: Accumulated pollutant before storm
- Total Washoff: Pollutant removed during simulation
- Avg Buildup: Average during simulation

---

### Link Pollutant Load
**Purpose**: Pollutant transport through links

**Fields per Pollutant/Link**:
- Total Inflow: Input pollutant mass
- Total Outflow: Exiting pollutant mass
- Mass Decay: Pollutant degradation
- Positive/Negative Adjustment: Calibration adjustments

---

## Summary Sections

### Analysis Time
**Purpose**: Computational statistics

**Typical Contents**:
- Total Elapsed Time: Wall-clock execution time
- Simulation Time: Simulated time period
- Time Steps: Number of computational steps
- Average Time/Step: Computational efficiency

**Example**:
```
Analysis Time
=============
Elapsed Time ........ 0:00:15 (seconds)
Simulation Time ..... 365 days
Time Steps .......... 52560
Avg. Time/Step ...... 0.02 seconds
```

---

## Parsing with SwmmReportDecoder

The `SwmmReportDecoder` class extracts all report sections into structured data:

```python
from swmm_utils import SwmmReportDecoder

decoder = SwmmReportDecoder()
report_data = decoder.decode_file("simulation.rpt")

# Access parsed sections
print(report_data["header"])                    # Version and title
print(report_data["element_count"])              # Element numbers
print(report_data["continuity"])                 # Mass balance
print(report_data["subcatchment_runoff"])        # Subcatchment results
print(report_data["node_depth"])                 # Node depth stats
print(report_data["pumping_summary"])            # Pump operation
print(report_data["storage_volume"])             # Storage stats
print(report_data["lid_performance"])            # LID performance
```

---

## Tips for Interpreting Results

### Continuity Errors
- **Good**: Less than 5% error
- **Acceptable**: 5-10% error
- **Poor**: Greater than 10% error
- High errors may indicate model instability or very short time steps

### Node Flooding
- Flooding indicates capacity exceedance
- Check weir/outlet structures and may need to increase conduit sizes
- High flood volumes suggest system inadequacy

### Pump Status
- Low "Percent Time On" suggests adequate system capacity
- High "On/Off Cycles" suggests intermittent surcharge
- Runaway pumping may indicate upstream flooding

### LID Performance
- Shows effectiveness of green infrastructure
- Low removal rates suggest insufficient LID area or design

---

## Common Report Variations

Different SWMM models generate different report sections based on:

1. **Model Components**
   - Models with pumps show Pumping Summary
   - Models with storage nodes show Storage Volume Summary
   - Models with LID controls show LID Performance

2. **Analysis Type**
   - Quality analysis adds water quality sections
   - Continuous simulation shows daily/monthly results
   - Event simulation shows event results

3. **SWMM Version**
   - SWMM 5.2 includes additional sections vs. 5.0/5.1
   - Build numbers may affect output format slightly

---

## File Encoding and Special Characters

- **Encoding**: UTF-8 with fallback to ASCII
- **Special Characters**: Degree symbols (°), Greek letters may appear
- **Separator**: Lines of equals signs (=) or dashes (-) separate sections
- **Whitespace**: Fixed-width columns for alignment

---

## Troubleshooting

### Missing Sections
If expected sections don't appear:
- Check that model contains those element types
- Verify analysis options enabled those results
- Ensure simulation completed without errors

### Unusual Values
- Check input file units (CFS vs. LPS)
- Verify simulation time period covers desired period
- Check time step settings affect output detail

### File Corruption
- Re-run simulation if file appears truncated
- Verify sufficient disk space during simulation
- Check file permissions and encoding
