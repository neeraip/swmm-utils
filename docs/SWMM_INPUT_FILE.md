# SWMM Input File (.inp) Documentation

## Overview

EPA SWMM (Storm Water Management Model) input files are text-based configuration files with a `.inp` extension that define all the parameters, properties, and data needed to simulate urban drainage systems. These files describe the physical components of a drainage network, hydrologic processes, hydraulic characteristics, and water quality constituents.

**Key Characteristics:**
- **Format**: Plain text files organized into named sections
- **Structure**: Section-based with bracketed headers (e.g., `[TITLE]`, `[OPTIONS]`)
- **Comments**: Lines beginning with `;` are comments
- **Delimiters**: Data fields are typically space or tab-delimited
- **Case Sensitivity**: Generally case-insensitive for keywords

## File Structure

### General Format

```
[SECTION_NAME]
;;Column Headers (optional comment)
;;-------------- --------------- ----------------
DataRow1_Field1  DataRow1_Field2  DataRow1_Field3
DataRow2_Field1  DataRow2_Field2  DataRow2_Field3
```

### Comment Types

1. **Full-line comments**: Begin with `;` or `;;`
2. **Section headers**: Enclosed in square brackets `[SECTION]`
3. **Inline comments**: Can appear after data (implementation-dependent)

---

## Core Sections (Always Present)

### [TITLE]
**Purpose**: Project identification and description

**Format**: Free-form text describing the project

**Example**:
```
[TITLE]
;;Project Title/Notes
Storm Sewer System Analysis for Downtown District
Model Calibration: October 2023
```

**Details**:
- Multiple lines allowed
- Used for documentation purposes only
- Does not affect simulation results

---

### [OPTIONS]
**Purpose**: Global simulation settings and computational parameters

**Format**: `Option_Name  Value`

**Common Options**:

| Option                  | Values                           | Description                            |
| ----------------------- | -------------------------------- | -------------------------------------- |
| **FLOW_UNITS**          | CFS, GPM, MGD, CMS, LPS, MLD     | Flow rate units (determines US/SI)     |
| **INFILTRATION**        | HORTON, GREEN_AMPT, CURVE_NUMBER | Infiltration model                     |
| **FLOW_ROUTING**        | STEADY, KINWAVE, DYNWAVE         | Flow routing method                    |
| **LINK_OFFSETS**        | DEPTH, ELEVATION                 | How conduit offsets are measured       |
| **ALLOW_PONDING**       | YES, NO                          | Allow surface ponding at nodes         |
| **SKIP_STEADY_STATE**   | YES, NO                          | Skip initial steady-state periods      |
| **START_DATE**          | MM/DD/YYYY                       | Simulation start date                  |
| **START_TIME**          | HH:MM:SS                         | Simulation start time                  |
| **END_DATE**            | MM/DD/YYYY                       | Simulation end date                    |
| **END_TIME**            | HH:MM:SS                         | Simulation end time                    |
| **REPORT_START_DATE**   | MM/DD/YYYY                       | When to start reporting                |
| **REPORT_START_TIME**   | HH:MM:SS                         | When to start reporting                |
| **SWEEP_START**         | MM/DD                            | Annual street sweeping start           |
| **SWEEP_END**           | MM/DD                            | Annual street sweeping end             |
| **DRY_DAYS**            | Number                           | Antecedent dry days                    |
| **REPORT_STEP**         | HH:MM:SS                         | Reporting time step                    |
| **WET_STEP**            | HH:MM:SS                         | Runoff time step (wet weather)         |
| **DRY_STEP**            | HH:MM:SS                         | Runoff time step (dry weather)         |
| **ROUTING_STEP**        | HH:MM:SS                         | Routing time step                      |
| **RULE_STEP**           | HH:MM:SS                         | Time step for evaluating control rules |
| **INERTIAL_DAMPING**    | NONE, PARTIAL, FULL              | Damping of inertial terms              |
| **NORMAL_FLOW_LIMITED** | SLOPE, FROUDE, BOTH              | Normal flow limitation method          |
| **FORCE_MAIN_EQUATION** | H-W, D-W                         | Force main friction formula            |
| **SURCHARGE_METHOD**    | EXTRAN, SLOT                     | Method for handling surcharge          |
| **VARIABLE_STEP**       | 0-1                              | Variable time step safety factor       |
| **LENGTHENING_STEP**    | 0-?                              | Time step lengthening factor           |
| **MIN_SURFAREA**        | sq ft/sq m                       | Minimum nodal surface area             |
| **MAX_TRIALS**          | Number                           | Max trials per routing step            |
| **HEAD_TOLERANCE**      | Feet/meters                      | Head convergence tolerance             |
| **SYS_FLOW_TOL**        | Percent                          | System flow tolerance                  |
| **LAT_FLOW_TOL**        | Percent                          | Lateral inflow tolerance               |
| **MINIMUM_STEP**        | Seconds                          | Minimum routing time step              |
| **THREADS**             | Number                           | Number of parallel threads             |

**Example**:
```
[OPTIONS]
;;Option             Value
FLOW_UNITS           CFS
INFILTRATION         GREEN_AMPT
FLOW_ROUTING         DYNWAVE
LINK_OFFSETS         DEPTH
START_DATE           01/01/2020
START_TIME           00:00:00
END_DATE             01/05/2020
END_TIME             00:00:00
ROUTING_STEP         0:00:30
REPORT_STEP          00:15:00
WET_STEP             00:05:00
DRY_STEP             01:00:00
```

---

### [EVAPORATION]
**Purpose**: Evaporation data for surface moisture losses

**Format**: `Data_Source  Parameters`

**Data Sources**:
- **CONSTANT**: Single constant rate
- **MONTHLY**: 12 monthly values
- **TIMESERIES**: Reference to timeseries
- **TEMPERATURE**: Computed from air temperature
- **FILE**: External climate file

**Additional Parameter**:
- `DRY_ONLY` (YES/NO): Apply evaporation only during dry periods

**Example**:
```
[EVAPORATION]
;;Data Source    Parameters
;;-------------- ----------------
MONTHLY          0.0  0.0  0.04  0.15  0.20  0.22  0.24  0.20  0.15  0.08  0.02  0.0
DRY_ONLY         NO
```

---

## Hydrology Sections

### [RAINGAGES]
**Purpose**: Define rainfall measurement stations

**Format**: `Name  Format  Interval  SCF  Source  [SourceParams...]`

**Columns**:
1. **Name**: Rain gage identifier
2. **Format**: INTENSITY (in/hr, mm/hr) or VOLUME (in, mm) or CUMULATIVE
3. **Interval**: Recording time interval (decimal hours or HH:MM)
4. **SCF**: Snow catch deficiency correction factor (default 1.0)
5. **Source**: TIMESERIES, FILE
6. **Source Parameters**: 
   - For TIMESERIES: Timeseries name
   - For FILE: Filename  StationID  RainUnits

**Example**:
```
[RAINGAGES]
;;Name           Format    Interval SCF      Source
;;-------------- --------- -------- -------- ----------
RG1              INTENSITY 1:00     1.0      TIMESERIES TS_RAIN_1
RG2              VOLUME    0:15     1.0      FILE "rainfall.dat" RG2 IN
```

---

### [SUBCATCHMENTS]
**Purpose**: Define drainage sub-areas (subcatchments) that generate runoff

**Format**: `Name  RainGage  Outlet  Area  %Imperv  Width  %Slope  CurbLen  [SnowPack]`

**Columns**:
1. **Name**: Subcatchment identifier
2. **Rain Gage**: Associated rain gage name
3. **Outlet**: Node or subcatchment receiving runoff
4. **Area**: Area (acres or hectares)
5. **%Imperv**: Percent impervious (0-100)
6. **Width**: Characteristic width (feet or meters)
7. **%Slope**: Average surface slope (percent)
8. **CurbLen**: Curb length (for pollutant buildup, feet or meters)
9. **SnowPack**: (Optional) Snow pack object name

**Example**:
```
[SUBCATCHMENTS]
;;Name           Rain Gage        Outlet           Area     %Imperv  Width    %Slope   CurbLen
;;-------------- ---------------- ---------------- -------- -------- -------- -------- --------
S1               RG1              J1               5.5      45.0     400      0.5      0
S2               RG1              J2               3.2      38.0     350      0.8      0
```

---

### [SUBAREAS]
**Purpose**: Surface characteristics for subcatchment areas

**Format**: `Subcatchment  N-Imperv  N-Perv  S-Imperv  S-Perv  PctZero  RouteTo  [PctRouted]`

**Columns**:
1. **Subcatchment**: Subcatchment name
2. **N-Imperv**: Manning's n for impervious area
3. **N-Perv**: Manning's n for pervious area
4. **S-Imperv**: Depression storage on impervious area (in or mm)
5. **S-Perv**: Depression storage on pervious area (in or mm)
6. **PctZero**: Percent of impervious area with no depression storage
7. **RouteTo**: IMPERVIOUS, PERVIOUS, or OUTLET
8. **PctRouted**: (Optional) Percent routed to pervious area

**Example**:
```
[SUBAREAS]
;;Subcatchment   N-Imperv   N-Perv     S-Imperv   S-Perv     PctZero    RouteTo
;;-------------- ---------- ---------- ---------- ---------- ---------- ----------
S1               0.011      0.15       0.05       0.10       25         OUTLET
S2               0.013      0.20       0.06       0.15       30         OUTLET
```

---

### [INFILTRATION]
**Purpose**: Infiltration parameters for pervious areas

**Format**: Depends on infiltration model selected in [OPTIONS]

#### HORTON Model
`Subcatchment  MaxRate  MinRate  Decay  DryTime  MaxInfil`

**Parameters**:
- **MaxRate**: Maximum infiltration rate (in/hr or mm/hr)
- **MinRate**: Minimum infiltration rate (in/hr or mm/hr)
- **Decay**: Decay constant (1/hr)
- **DryTime**: Time for fully dried soil (days)
- **MaxInfil**: Maximum infiltration capacity (in or mm)

#### GREEN_AMPT Model
`Subcatchment  Suction  Ksat  IMD`

**Parameters**:
- **Suction**: Soil capillary suction (inches or mm)
- **Ksat**: Soil saturated hydraulic conductivity (in/hr or mm/hr)
- **IMD**: Initial moisture deficit (fraction)

#### CURVE_NUMBER Model
`Subcatchment  CurveNum  [HydCon]  [DryTime]`

**Parameters**:
- **CurveNum**: SCS Curve Number
- **HydCon**: (Optional) Hydraulic conductivity (in/hr or mm/hr)
- **DryTime**: (Optional) Drying time (days)

**Example (GREEN_AMPT)**:
```
[INFILTRATION]
;;Subcatchment   Suction    Ksat       IMD
;;-------------- ---------- ---------- ----------
S1               3.5        0.50       0.25
S2               4.0        0.40       0.28
```

---

## Conveyance Network Sections

### [JUNCTIONS]
**Purpose**: Junction nodes where conduits connect

**Format**: `Name  Elevation  MaxDepth  InitDepth  SurDepth  Aponded`

**Columns**:
1. **Name**: Junction identifier
2. **Elevation**: Invert elevation (feet or meters)
3. **MaxDepth**: Maximum water depth (feet or meters)
4. **InitDepth**: Initial water depth (feet or meters)
5. **SurDepth**: Depth of surcharge above MaxDepth (feet or meters)
6. **Aponded**: Ponded surface area when flooded (sq ft or sq m)

**Example**:
```
[JUNCTIONS]
;;Name           Elevation  MaxDepth   InitDepth  SurDepth   Aponded
;;-------------- ---------- ---------- ---------- ---------- ----------
J1               95.0       8.0        0.0        0.0        0
J2               92.5       10.0       0.0        0.0        0
```

---

### [OUTFALLS]
**Purpose**: Terminal nodes where water exits the system

**Format**: `Name  Elevation  Type  [StageData]  Gated  [RouteTo]`

**Columns**:
1. **Name**: Outfall identifier
2. **Elevation**: Invert elevation (feet or meters)
3. **Type**: Boundary condition type
   - **FREE**: Unrestricted discharge
   - **NORMAL**: Normal flow depth
   - **FIXED**: Fixed stage elevation
   - **TIDAL**: Time series of tidal elevations
   - **TIMESERIES**: Time series of stage elevations
4. **Stage Data**: Elevation or timeseries name (depends on Type)
5. **Gated**: YES or NO (tide gate present)
6. **Route To**: (Optional) Subcatchment or node name

**Example**:
```
[OUTFALLS]
;;Name           Elevation  Type       Stage Data       Gated
;;-------------- ---------- ---------- ---------------- --------
OUT1             85.0       FREE                        NO
OUT2             84.5       FIXED      86.0             NO
```

---

### [STORAGE]
**Purpose**: Storage units (e.g., detention ponds, tanks, reservoirs)

**Format**: `Name  Elev  MaxDepth  InitDepth  Shape  Curve/Params...  [Fevap]  [Psi]  [Ksat]  [IMD]`

**Columns**:
1. **Name**: Storage unit identifier
2. **Elev**: Invert elevation (feet or meters)
3. **MaxDepth**: Maximum depth (feet or meters)
4. **InitDepth**: Initial water depth (feet or meters)
5. **Shape**: Storage shape type
   - **FUNCTIONAL**: A(h) = a0 + a1·h^a2
   - **TABULAR**: Use curve of depth vs. area
   - **CYLINDRICAL**: Constant area
   - **CONICAL**: Conical shape
   - **PARABOLOID**: Paraboloid shape
   - **PYRAMIDAL**: Pyramid shape
6. **Curve/Params**: Curve name or shape coefficients
7. **Fevap**: (Optional) Fraction of evaporation
8. **Psi**: (Optional) Suction head for exfiltration (in or mm)
9. **Ksat**: (Optional) Hydraulic conductivity for exfiltration
10. **IMD**: (Optional) Initial moisture deficit

**Example**:
```
[STORAGE]
;;Name           Elev.    MaxDepth   InitDepth  Shape      Curve Name/Params
;;-------------- -------- ---------- ---------- ---------- --------------------
POND1            90.0     12.0       0.0        TABULAR    POND1_CURVE
TANK1            88.0     15.0       2.0        CYLINDRICAL 5000
```

---

### [CONDUITS]
**Purpose**: Pipes, channels, or other conveyance links

**Format**: `Name  FromNode  ToNode  Length  Roughness  InOffset  OutOffset  InitFlow  MaxFlow`

**Columns**:
1. **Name**: Conduit identifier
2. **FromNode**: Upstream node name
3. **ToNode**: Downstream node name
4. **Length**: Conduit length (feet or meters)
5. **Roughness**: Manning's roughness coefficient
6. **InOffset**: Inlet offset height (feet or meters)
7. **OutOffset**: Outlet offset height (feet or meters)
8. **InitFlow**: Initial flow (CFS or CMS)
9. **MaxFlow**: Maximum flow (0 = unlimited)

**Example**:
```
[CONDUITS]
;;Name           From Node        To Node          Length     Roughness  InOffset   OutOffset
;;-------------- ---------------- ---------------- ---------- ---------- ---------- ----------
C1               J1               J2               400        0.013      0          0
C2               J2               OUT1             500        0.015      0          0
```

---

### [PUMPS]
**Purpose**: Pumping stations that lift water

**Format**: `Name  FromNode  ToNode  PumpCurve  Status  Startup  Shutoff`

**Columns**:
1. **Name**: Pump identifier
2. **FromNode**: Inlet node
3. **ToNode**: Outlet node
4. **PumpCurve**: Name of pump curve (Type1-Type4, or *Ideal*)
5. **Status**: Initial pump status (ON, OFF)
6. **Startup**: Startup depth at inlet node (feet or meters)
7. **Shutoff**: Shutoff depth at inlet node (feet or meters)

**Example**:
```
[PUMPS]
;;Name           From Node        To Node          Pump Curve       Status   Startup  Shutoff
;;-------------- ---------------- ---------------- ---------------- -------- -------- --------
PUMP1            WET_WELL         J5               PUMP1_CURVE      OFF      5.0      2.0
```

---

### [ORIFICES]
**Purpose**: Outlet structures in storage units or diversions

**Format**: `Name  FromNode  ToNode  Type  Offset  Qcoeff  Gated  CloseTime`

**Columns**:
1. **Name**: Orifice identifier
2. **FromNode**: Upstream node
3. **ToNode**: Downstream node
4. **Type**: SIDE or BOTTOM
5. **Offset**: Offset height above inlet node invert (feet or meters)
6. **Qcoeff**: Discharge coefficient (typically 0.65)
7. **Gated**: YES or NO
8. **CloseTime**: Time to open/close (seconds)

**Geometry defined in [XSECTIONS]**

**Example**:
```
[ORIFICES]
;;Name           From Node        To Node          Type         Offset     Qcoeff     Gated
;;-------------- ---------------- ---------------- ------------ ---------- ---------- --------
OR1              POND1            J3               SIDE         2.0        0.65       NO
```

---

### [WEIRS]
**Purpose**: Overflow structures

**Format**: `Name  FromNode  ToNode  Type  CrestHt  Qcoeff  Gated  EndCon  EndCoeff  Surcharge  [RoadWidth]  [RoadSurf]`

**Columns**:
1. **Name**: Weir identifier
2. **FromNode**: Upstream node
3. **ToNode**: Downstream node
4. **Type**: Weir type
   - **TRANSVERSE**: Transverse weir
   - **SIDEFLOW**: Side flow weir
   - **V-NOTCH**: V-notch weir
   - **TRAPEZOIDAL**: Trapezoidal weir
   - **ROADWAY**: Road overtopping
5. **CrestHt**: Crest height above inlet invert (feet or meters)
6. **Qcoeff**: Discharge coefficient
7. **Gated**: YES or NO
8. **EndCon**: Number of end contractions (0, 1, or 2)
9. **EndCoeff**: End contraction coefficient
10. **Surcharge**: YES (allow surcharge) or NO
11. **RoadWidth**: (Optional) Road width for ROADWAY type
12. **RoadSurf**: (Optional) Road surface for ROADWAY type

**Example**:
```
[WEIRS]
;;Name           From Node        To Node          Type         CrestHt    Qcoeff     Gated
;;-------------- ---------------- ---------------- ------------ ---------- ---------- --------
W1               POND1            J4               TRANSVERSE   3.5        3.33       NO
```

---

### [OUTLETS]
**Purpose**: Flow control/diversion structures with custom rating curves

**Format**: `Name  FromNode  ToNode  Offset  Type  [QTable/CurveData]  Qcoeff  Gated`

**Columns**:
1. **Name**: Outlet identifier
2. **FromNode**: Upstream node
3. **ToNode**: Downstream node
4. **Offset**: Offset height (feet or meters)
5. **Type**: Rating curve type
   - **TABULAR/DEPTH**: Depth vs. flow curve
   - **TABULAR/HEAD**: Head vs. flow curve
   - **FUNCTIONAL/DEPTH**: Q = C·h^n
   - **FUNCTIONAL/HEAD**: Q = C·H^n
6. **Curve Name or Coefficients**: Depends on type
7. **Qcoeff**: Coefficient C (for functional types)
8. **Gated**: YES or NO

**Example**:
```
[OUTLETS]
;;Name           From Node        To Node          Offset     Type            QTable/Curve
;;-------------- ---------------- ---------------- ---------- --------------- ----------------
OUT_CTRL         TANK1            J6               0.0        TABULAR/DEPTH   OUTLET_CURVE
```

---

### [XSECTIONS]
**Purpose**: Cross-sectional geometry for conduits and regulator links

**Format**: `Link  Shape  Geom1  Geom2  Geom3  Geom4  Barrels  [Culvert]`

**Common Shapes**:

| Shape               | Geom1         | Geom2        | Geom3           | Geom4       | Description                 |
| ------------------- | ------------- | ------------ | --------------- | ----------- | --------------------------- |
| **CIRCULAR**        | Diameter      | -            | -               | -           | Circular pipe               |
| **FILLED_CIRCULAR** | Height        | Filled Depth | -               | -           | Partially filled circular   |
| **RECT_CLOSED**     | Height        | Width        | -               | -           | Rectangular closed          |
| **RECT_OPEN**       | Height        | Width        | -               | -           | Rectangular open            |
| **TRAPEZOIDAL**     | Height        | Bottom Width | Left Slope      | Right Slope | Trapezoidal                 |
| **TRIANGULAR**      | Height        | Top Width    | -               | -           | Triangular                  |
| **EGG**             | Height        | -            | -               | -           | Egg-shaped                  |
| **HORSESHOE**       | Height        | -            | -               | -           | Horseshoe                   |
| **PARABOLIC**       | Height        | Top Width    | -               | -           | Parabolic                   |
| **POWER**           | Height        | Top Width    | Exponent        | -           | Power function              |
| **RECT_TRIANGULAR** | Height        | Top Width    | Triangle Height | -           | Rect. with tri. bottom      |
| **RECT_ROUND**      | Height        | Top Width    | Bottom Radius   | -           | Rect. with round bottom     |
| **MODBASKETHANDLE** | Height        | Top Width    | -               | -           | Modified basket handle      |
| **HORIZ_ELLIPSE**   | Height        | Max Width    | -               | -           | Horizontal ellipse          |
| **VERT_ELLIPSE**    | Height        | Max Width    | -               | -           | Vertical ellipse            |
| **ARCH**            | Height        | Max Width    | -               | -           | Arch                        |
| **FORCE_MAIN**      | Diameter      | Roughness    | -               | -           | Force main (pumped)         |
| **CUSTOM**          | -             | -            | -               | -           | Custom (use [TRANSECTS])    |
| **IRREGULAR**       | Transect Name | -            | -               | -           | Irregular (use [TRANSECTS]) |

**Additional Columns**:
- **Barrels**: Number of barrels (default 1)
- **Culvert**: Culvert code (optional)

**Example**:
```
[XSECTIONS]
;;Link           Shape            Geom1      Geom2      Geom3      Geom4      Barrels
;;-------------- ---------------- ---------- ---------- ---------- ---------- ----------
C1               CIRCULAR         2.0        0          0          0          1
C2               RECT_CLOSED      3.0        4.0        0          0          1
OR1              CIRCULAR         1.5        0          0          0
W1               RECT_OPEN        0          6.0        0          0
```

---

### [LOSSES]
**Purpose**: Minor entrance/exit/average losses for conduits

**Format**: `Link  Kentry  Kexit  Kavg  FlapGate  Seepage`

**Columns**:
1. **Link**: Conduit name
2. **Kentry**: Entrance loss coefficient
3. **Kexit**: Exit loss coefficient
4. **Kavg**: Average loss coefficient
5. **FlapGate**: YES or NO (flap gate present)
6. **Seepage**: Seepage loss rate (in/hr or mm/hr)

**Example**:
```
[LOSSES]
;;Link           Kentry     Kexit      Kavg       FlapGate   Seepage
;;-------------- ---------- ---------- ---------- ---------- ----------
C1               0.5        1.0        0          NO         0
C2               0.2        0.8        0          NO         0
```

---

### [TRANSECTS]
**Purpose**: Irregular cross-section geometry (e.g., natural channels)

**Format**: Multi-line format with NC (name/comment), X1 (coordinates), and GR (station-elevation) lines

**Structure**:
```
NC  modifiers  Name  nLeft  nRight  nChannel
X1  Name  nSta  leftBank  rightBank  0  0  0  channelFactor  0
GR  Elevation  Station  Elevation  Station  ...
GR  Elevation  Station  Elevation  Station  ...
```

**Example**:
```
[TRANSECTS]
NC  0.035  0.035  0.035
X1  CHANNEL1  12  5  7
GR  105.0  0    103.0  50   102.0  100  103.0  150  105.0  200
GR  102.5  75   102.0  100  102.5  125
```

---

## Flow Input Sections

### [INFLOWS]
**Purpose**: External inflows into nodes (dry weather flow, wastewater, etc.)

**Format**: `Node  Constituent  TimeSeries  Type  Mfactor  Sfactor  Baseline  Pattern`

**Columns**:
1. **Node**: Node receiving inflow
2. **Constituent**: FLOW or pollutant name
3. **TimeSeries**: Timeseries name or FLOW value
4. **Type**: FLOW, CONCEN (concentration), or MASS
5. **Mfactor**: Multiplication factor
6. **Sfactor**: Scale factor
7. **Baseline**: Baseline value
8. **Pattern**: Time pattern name

**Example**:
```
[INFLOWS]
;;Node           Constituent      Time Series      Type     Mfactor  Sfactor  Baseline Pattern
;;-------------- ---------------- ---------------- -------- -------- -------- -------- --------
J1               FLOW             INFLOW_TS        FLOW     1.0      1.0      0.0
J2               FLOW             ""               FLOW     1.0      1.0      2.5      DWF_PATTERN
```

---

### [DWF]
**Purpose**: Dry weather flow (sanitary sewage, base flow)

**Format**: `Node  Constituent  AvgValue  Pat1  Pat2  Pat3  Pat4`

**Columns**:
1. **Node**: Node with dry weather inflow
2. **Constituent**: FLOW or pollutant name
3. **AvgValue**: Average dry weather value
4. **Pat1**: (Optional) Monthly pattern
5. **Pat2**: (Optional) Daily pattern
6. **Pat3**: (Optional) Hourly pattern
7. **Pat4**: (Optional) Weekend pattern

**Example**:
```
[DWF]
;;Node           Constituent      AvgValue   Pat1       Pat2       Pat3       Pat4
;;-------------- ---------------- ---------- ---------- ---------- ---------- ----------
J3               FLOW             0.05       MONTHLY    DAILY      HOURLY
J4               TSS              50.0
```

---

### [RDII]
**Purpose**: Rainfall-Dependent Infiltration/Inflow (sewer system leakage)

**Format**: `Node  UHgroup  SewerArea`

**Columns**:
1. **Node**: Node receiving RDII
2. **UHgroup**: Unit hydrograph group name
3. **SewerArea**: Sewershed area (acres or hectares)

**Example**:
```
[RDII]
;;Node           UHgroup          SewerArea
;;-------------- ---------------- ----------
J5               UH_GROUP_1       25.5
J6               UH_GROUP_1       18.3
```

---

### [HYDROGRAPHS]
**Purpose**: RDII unit hydrograph groups

**Format**: `Name  Month/ALL  R  T  K  [IA_max  IA_rec  IA_ini]`

**Columns**:
1. **Name**: Unit hydrograph group name
2. **Month**: Month (1-12) or ALL
3. **R**: Response ratio (fraction of rainfall that enters sewer)
4. **T**: Time to peak (hours)
5. **K**: Recession limb ratio
6. **IA_max**: (Optional) Max initial abstraction (in or mm)
7. **IA_rec**: (Optional) IA recovery rate (in/day or mm/day)
8. **IA_ini**: (Optional) Initial IA depth (in or mm)

**Up to 3 unit hydrographs per group (Short, Medium, Long)**

**Example**:
```
[HYDROGRAPHS]
;;Name           Month/ALL  R          T          K
;;-------------- ---------- ---------- ---------- ----------
UH_GROUP_1       ALL        0.002      1.5        2.0
UH_GROUP_1       ALL        0.005      6.0        2.0
UH_GROUP_1       ALL        0.010      18.0       2.0
```

---

## Control and Operation Sections

### [CONTROLS]
**Purpose**: Simple rule-based controls for pumps and regulators

**Format**: `RULE rule_name`

**Structure**:
```
RULE RuleName
IF      condition1
AND/OR  condition2
THEN    action1
AND     action2
ELSE    action3
PRIORITY value
```

**Conditions**:
- `NODE node DEPTH|HEAD >|<|= value`
- `LINK link FLOW|DEPTH|STATUS >|<|= value`
- `SIMULATION TIME >|<|= value`
- `SIMULATION DATE = month/day`

**Actions**:
- `PUMP|ORIFICE|WEIR link STATUS = ON|OFF`
- `PUMP link SETTING = value`
- `ORIFICE|WEIR link SETTING = value`

**Example**:
```
[CONTROLS]
RULE PUMP1_CONTROL
IF NODE WET_WELL DEPTH > 6.0
THEN PUMP PUMP1 STATUS = ON
ELSE PUMP PUMP1 STATUS = OFF
PRIORITY 5
```

---

## Time Series and Patterns

### [TIMESERIES]
**Purpose**: Time series data for rainfall, inflows, etc.

**Format**: `Name  [Date]  Time  Value`

**Types**:
- **Relative**: No date, time is hours from simulation start
- **Absolute**: Date and time specified

**Example**:
```
[TIMESERIES]
;;Name           Date       Time       Value
;;-------------- ---------- ---------- ----------
INFLOW_TS                   0:00       0.0
INFLOW_TS                   1:00       2.5
INFLOW_TS                   2:00       5.0
INFLOW_TS                   3:00       3.0
RAIN_EVENT       01/15/2020 08:00      0.0
RAIN_EVENT       01/15/2020 09:00      0.5
RAIN_EVENT       01/15/2020 10:00      1.2
```

Alternatively, reference external file:
```
[TIMESERIES]
;;Name           Filename
;;-------------- ----------------
RAIN_DATA        "rainfall.dat"
```

---

### [PATTERNS]
**Purpose**: Multiplier patterns for temporal variations

**Format**: `Name  Type  Multiplier1  Multiplier2  ...`

**Types**:
- **MONTHLY**: 12 values (one per month)
- **DAILY**: 7 values (one per day of week)
- **HOURLY**: 24 values (one per hour)
- **WEEKEND**: 24 values (weekend hourly pattern)

**Example**:
```
[PATTERNS]
;;Name           Type       Multipliers
;;-------------- ---------- ----------------------------------------------
HOURLY           HOURLY     0.5  0.4  0.3  0.3  0.4  0.6  0.8  1.0  1.1  1.2
HOURLY           HOURLY     1.2  1.1  1.0  1.0  1.1  1.2  1.3  1.3  1.2  1.0
HOURLY           HOURLY     0.9  0.8  0.7  0.6
MONTHLY          MONTHLY    0.9  0.9  1.0  1.1  1.2  1.3  1.3  1.2  1.1  1.0  0.9  0.9
```

---

## Curve Data

### [CURVES]
**Purpose**: X-Y relationship curves (pump curves, rating curves, etc.)

**Format**: `Name  Type  X-value  Y-value`

**Curve Types**:
- **STORAGE**: Depth vs. Area (for storage units)
- **DIVERSION**: Flow vs. Diverted flow
- **TIDAL**: Hour vs. Stage
- **PUMP1**: Volume vs. Flow
- **PUMP2**: Depth vs. Flow
- **PUMP3**: Head vs. Flow
- **PUMP4**: Depth vs. Flow
- **RATING**: Head vs. Flow (for outlets)
- **CONTROL**: Controller setting curve
- **SHAPE**: Width vs. Height fraction (for custom shapes)
- **WEIR**: Height vs. Discharge coefficient

**Example**:
```
[CURVES]
;;Name           Type       X-Value    Y-Value
;;-------------- ---------- ---------- ----------
PUMP1_CURVE      PUMP3      0.0        0.0
PUMP1_CURVE      PUMP3      5.0        100.0
PUMP1_CURVE      PUMP3      10.0       150.0
PUMP1_CURVE      PUMP3      15.0       180.0
POND1_CURVE      STORAGE    0.0        5000.0
POND1_CURVE      STORAGE    2.0        6500.0
POND1_CURVE      STORAGE    4.0        8000.0
POND1_CURVE      STORAGE    6.0        9500.0
```

---

## Water Quality Sections

### [POLLUTANTS]
**Purpose**: Define water quality constituents

**Format**: `Name  Units  Crain  Cgw  Crdii  Kdecay  SnowOnly  Co-Pollutant  Co-Frac  Cdwf  Cinit`

**Columns**:
1. **Name**: Pollutant identifier
2. **Units**: Concentration units (MG/L, UG/L, or #/L)
3. **Crain**: Concentration in rainfall
4. **Cgw**: Concentration in groundwater
5. **Crdii**: Concentration in RDII
6. **Kdecay**: First-order decay coefficient (1/days)
7. **SnowOnly**: YES or NO (pollutant only in snowmelt)
8. **Co-Pollutant**: Name of co-pollutant
9. **Co-Frac**: Fraction of co-pollutant concentration
10. **Cdwf**: Concentration in dry weather flow
11. **Cinit**: Initial concentration throughout system

**Example**:
```
[POLLUTANTS]
;;Name           Units  Crain      Cgw        Crdii      Kdecay     SnowOnly   CoPollutant
;;-------------- ------ ---------- ---------- ---------- ---------- ---------- ------------
TSS              MG/L   5.0        0.0        0.0        0.0        NO         *
BOD              MG/L   0.0        0.0        0.0        0.05       NO         TSS          0.15
```

---

### [LANDUSES]
**Purpose**: Land use categories for pollutant buildup

**Format**: `Name  SweepInterval  Availability  LastSweep`

**Columns**:
1. **Name**: Land use name
2. **SweepInterval**: Days between street sweeping
3. **Availability**: Fraction available for sweeping (0-1)
4. **LastSweep**: Days since last swept

**Example**:
```
[LANDUSES]
;;Name           SweepInterval  Availability  LastSweep
;;-------------- -------------- ------------- ----------
RESIDENTIAL      0              0             0
COMMERCIAL       7              0.5           0
INDUSTRIAL       14             0.3           0
```

---

### [COVERAGES]
**Purpose**: Assignment of land uses to subcatchments

**Format**: `Subcatchment  LandUse  Percent`

**Columns**:
1. **Subcatchment**: Subcatchment name
2. **LandUse**: Land use name
3. **Percent**: Percent of subcatchment area (0-100)

**Example**:
```
[COVERAGES]
;;Subcatchment   LandUse          Percent
;;-------------- ---------------- ----------
S1               RESIDENTIAL      70
S1               COMMERCIAL       30
S2               RESIDENTIAL      50
S2               COMMERCIAL       40
S2               INDUSTRIAL       10
```

---

### [BUILDUP]
**Purpose**: Pollutant buildup functions

**Format**: `LandUse  Pollutant  Function  C1  C2  C3  PerUnit`

**Columns**:
1. **LandUse**: Land use name
2. **Pollutant**: Pollutant name
3. **Function**: Buildup function type
   - **NONE**: No buildup
   - **POW**: Power: M = C1 · t^C2 · C3
   - **EXP**: Exponential: M = C1 · (1 - e^(-C2·t)) · C3
   - **SAT**: Saturation: M = C1 · t / (C2 + t) · C3
   - **EXT**: External time series
4. **C1, C2, C3**: Function coefficients
5. **PerUnit**: AREA (per unit area) or CURB (per curb length)

**Example**:
```
[BUILDUP]
;;LandUse        Pollutant        Function   C1         C2         C3         PerUnit
;;-------------- ---------------- ---------- ---------- ---------- ---------- ----------
RESIDENTIAL      TSS              POW        10.0       0.5        1.0        AREA
COMMERCIAL       TSS              SAT        15.0       2.0        1.0        AREA
```

---

### [WASHOFF]
**Purpose**: Pollutant washoff functions

**Format**: `LandUse  Pollutant  Function  C1  C2  SweepRmvl  BmpRmvl`

**Columns**:
1. **LandUse**: Land use name
2. **Pollutant**: Pollutant name
3. **Function**: Washoff function type
   - **NONE**: No washoff
   - **EXP**: Exponential: W = C1 · (Runoff)^C2 · M
   - **RC**: Rating curve: W = C1 · (Runoff)^C2
   - **EMC**: Event mean concentration: W = C1
4. **C1, C2**: Function coefficients
5. **SweepRmvl**: Sweeping removal efficiency (0-100%)
6. **BmpRmvl**: BMP removal efficiency (0-100%)

**Example**:
```
[WASHOFF]
;;LandUse        Pollutant        Function   C1         C2         SweepRmvl  BmpRmvl
;;-------------- ---------------- ---------- ---------- ---------- ---------- ----------
RESIDENTIAL      TSS              EXP        0.15       1.8        60         0
COMMERCIAL       TSS              EMC        80.0       0.0        70         0
```

---

### [LOADINGS]
**Purpose**: Initial pollutant buildup on subcatchments

**Format**: `Subcatchment  Pollutant  InitBuildup`

**Example**:
```
[LOADINGS]
;;Subcatchment   Pollutant        InitBuildup
;;-------------- ---------------- ----------
S1               TSS              50.0
S2               TSS              75.0
```

---

### [TREATMENT]
**Purpose**: Pollutant treatment/removal at nodes

**Format**: `Node  Pollutant  Expression`

**Expression**: Can use standard math operators and these variables:
- `R_pol`: Pollutant removal fraction (0-1)
- `C_pol`: Pollutant concentration
- `FLOW`: Flow rate
- `DEPTH`: Water depth
- `HRT`: Hydraulic retention time

**Example**:
```
[TREATMENT]
;;Node           Pollutant        Expression
;;-------------- ---------------- ------------------------------
POND1            TSS              R = 0.8 * (1 - EXP(-0.5 * HRT))
POND1            BOD              C = 0.5 * TSS
```

---

## Low Impact Development (LID) Sections

### [LID_CONTROLS]
**Purpose**: Define green infrastructure/LID control types

**Format**: Multi-line format with control name, type, and layer-specific parameters

**LID Types**:
- **BC**: Bioretention Cell
- **RG**: Rain Garden
- **GR**: Green Roof
- **IT**: Infiltration Trench
- **PP**: Permeable Pavement
- **RB**: Rain Barrel
- **VS**: Vegetative Swale
- **RD**: Rooftop Disconnection

**Layer Types and Parameters**:

Each LID control has multiple lines:
1. First line: `Name  Type` (e.g., `RainGarden  BC`)
2. Subsequent lines: `Name  LAYER  param1  param2  ...`

**Common Layers**:
- **SURFACE**: Berm height, vegetation volume, surface roughness, surface slope, swale side slope
- **SOIL**: Thickness, porosity, field capacity, wilting point, conductivity, suction head, conductivity slope
- **STORAGE**: Thickness (height), void ratio, seepage rate, clogging factor
- **DRAIN**: Coefficient, exponent, offset, delay time (hours)
- **DRAINMAT**: Thickness, void fraction, roughness
- **PAVEMENT**: Thickness, void ratio, impervious surface fraction, permeability, clogging factor (for PP only)

**Example**:
```
[LID_CONTROLS]
;;Name           Type/Layer  Parameters
;;-------------- ----------  ----------
RainGarden       BC
RainGarden       SURFACE     6.0   0.0   0.1   1.0   5.0
RainGarden       SOIL        12.0  0.5   0.2   0.1   0.5   3.5   10.0
RainGarden       STORAGE     12.0  0.75  0.5   0.0
RainGarden       DRAIN       0.5   0.5   6.0   0.0
PP               PP
PP               SURFACE     0.0   0.0   0.0   1.0   5.0
PP               PAVEMENT    6.0   0.15  0.0   100.0 0.0
PP               STORAGE     12.0  0.75  0.5   0.0
PP               DRAIN       0.5   0.5   6.0   0.0
```

---

### [LID_USAGE]
**Purpose**: Assignment of LID controls to subcatchments

**Format**: `Subcatchment  LIDProcess  Number  Area  Width  InitSat  FromImp  ToPerv  [RptFile]  [DrainTo]  [FromPerv]`

**Columns**:
1. **Subcatchment**: Subcatchment name
2. **LIDProcess**: LID control name
3. **Number**: Number of replicate units
4. **Area**: Area of each unit (sq ft or sq m)
5. **Width**: Width of each unit (ft or m)
6. **InitSat**: Initial saturation (%)
7. **FromImp**: % of impervious area treated
8. **ToPerv**: 1 if outflow sent to pervious area, 0 for impervious
9. **RptFile**: (Optional) Report file name
10. **DrainTo**: (Optional) Subcatchment or node receiving underdrain flow
11. **FromPerv**: (Optional) % of pervious area treated

**Example**:
```
[LID_USAGE]
;;Subcatchment   LIDProcess       Number  Area       Width      InitSat    FromImp    ToPerv
;;-------------- ---------------- ------- ---------- ---------- ---------- ---------- ----------
S1               RainGarden       5       500        25         0          50         1
S2               RainGarden       3       400        20         0          60         0
```

---

## Groundwater Section

### [AQUIFERS]
**Purpose**: Groundwater aquifer properties

**Format**: `Name  Por  WP  FC  Ksat  Kslope  Tslope  ETu  ETs  Seep  Ebot  Egw  Umc  [ETupat]`

**Columns**:
1. **Name**: Aquifer name
2. **Por**: Porosity (volume fraction)
3. **WP**: Wilting point moisture content
4. **FC**: Field capacity moisture content
5. **Ksat**: Saturated hydraulic conductivity (in/hr or mm/hr)
6. **Kslope**: Slope of log(K) vs. moisture deficit
7. **Tslope**: Slope of tension vs. moisture content
8. **ETu**: Fraction of  ET from unsaturated zone
9. **ETs**: Fraction of ET from saturated zone
10. **Seep**: Seepage rate to deep aquifer (in/hr or mm/hr)
11. **Ebot**: Elevation of bottom of aquifer (ft or m)
12. **Egw**: Initial water table elevation (ft or m)
13. **Umc**: Initial unsaturated zone moisture content
14. **ETupat**: (Optional) ET pattern

**Example**:
```
[AQUIFERS]
;;Name           Por    WP     FC     Ksat   Kslope Tslope ETu    ETs    Seep   Ebot   Egw    Umc
;;-------------- ------ ------ ------ ------ ------ ------ ------ ------ ------ ------ ------ ------
AQUIFER1         0.5    0.15   0.30   1.0    5.0    10.0   0.35   0.0    0.002  0.0    5.0    0.25
```

---

### [GROUNDWATER]
**Purpose**: Groundwater parameters for subcatchments

**Format**: `Subcatchment  Aquifer  Node  Esurf  A1  B1  A2  B2  A3  Dsw  [Egwt]  [Ebot]  [Wgr]  [Umc]`

**Columns**:
1. **Subcatchment**: Subcatchment name
2. **Aquifer**: Aquifer name
3. **Node**: Node receiving groundwater flow
4. **Esurf**: Surface elevation (ft or m)
5. **A1**: Groundwater flow coefficient
6. **B1**: Groundwater flow exponent
7. **A2**: Surface water flow coefficient
8. **B2**: Surface water flow exponent
9. **A3**: Surface-groundwater interaction coefficient
10. **Dsw**: Fixed depth of surface water (ft or m)
11-14: Optional override parameters

**Example**:
```
[GROUNDWATER]
;;Subcatchment   Aquifer          Node             Esurf      A1         B1         A2         B2
;;-------------- ---------------- ---------------- ---------- ---------- ---------- ---------- ----------
S1               AQUIFER1         J1               100.0      0.001      2.0        0.0        0.0
```

---

## Mapping and Visualization Sections

### [COORDINATES]
**Purpose**: X-Y coordinates for nodes

**Format**: `Node  X-Coord  Y-Coord`

**Example**:
```
[COORDINATES]
;;Node           X-Coord            Y-Coord
;;-------------- ------------------ ------------------
J1               2500.000           5000.000
J2               3000.000           5000.000
OUT1             3500.000           5000.000
```

---

### [VERTICES]
**Purpose**: Interior vertex points for curved links

**Format**: `Link  X-Coord  Y-Coord`

**Example**:
```
[VERTICES]
;;Link           X-Coord            Y-Coord
;;-------------- ------------------ ------------------
C1               2600.000           5100.000
C1               2700.000           5050.000
```

---

### [Polygons]
**Purpose**: Subcatchment boundary polygon vertices

**Format**: `Subcatchment  X-Coord  Y-Coord`

**Example**:
```
[Polygons]
;;Subcatchment   X-Coord            Y-Coord
;;-------------- ------------------ ------------------
S1               2000.000           4800.000
S1               2400.000           4800.000
S1               2400.000           5200.000
S1               2000.000           5200.000
```

---

### [SYMBOLS]
**Purpose**: X-Y coordinates for rain gages and other symbols

**Format**: `Gage  X-Coord  Y-Coord`

**Example**:
```
[SYMBOLS]
;;Gage           X-Coord            Y-Coord
;;-------------- ------------------ ------------------
RG1              1500.000           5500.000
```

---

### [LABELS]
**Purpose**: Map labels

**Format**: `X-Coord  Y-Coord  "Label"  [Anchor]  [Font]  [Size]  [Bold]  [Italic]`

**Example**:
```
[LABELS]
;;X-Coord          Y-Coord            Label
2750.000           5250.000           "Zone A"
```

---

### [BACKDROP]
**Purpose**: Background image for map display

**Format**: 
```
FILE      "filename"
DIMENSIONS  LLx  LLy  URx  URy
```

---

## Reporting and Output Sections

### [REPORT]
**Purpose**: Control output reporting options

**Format**: `Option  Value`

**Options**:
- **INPUT**: YES or NO (echo input to report)
- **CONTROLS**: YES or NO (list control actions)
- **SUBCATCHMENTS**: ALL, NONE, or list of IDs
- **NODES**: ALL, NONE, or list of IDs
- **LINKS**: ALL, NONE, or list of IDs
- **CONTINUITY**: YES or NO
- **FLOWSTATS**: YES or NO
- **AVERAGES**: YES or NO (time-averaged results)
- **LID**: Name (report specific LID)

**Example**:
```
[REPORT]
INPUT      NO
CONTROLS   YES
SUBCATCHMENTS ALL
NODES ALL
LINKS ALL
CONTINUITY YES
FLOWSTATS YES
```

---

### [TAGS]
**Purpose**: Assign category tags to objects

**Format**: `ObjectType  Name  Tag`

**Object Types**: Node, Link, Subcatch

**Example**:
```
[TAGS]
Node         J1               "Priority_1"
Link         C1               "Critical"
Subcatch     S1               "Residential"
```

---

### [MAP]
**Purpose**: Map display dimensions and units

**Format**: `Option  Value`

**Options**:
- **DIMENSIONS**: LLx LLy URx URy (bounding box)
- **UNITS**: FEET, METERS, DEGREES, NONE

**Example**:
```
[MAP]
DIMENSIONS 0.000 0.000 10000.000 10000.000
Units      FEET
```

---

### [PROFILES]
**Purpose**: Define profile plots for visualization

**Format**: `"Name"  Link1  Link2  Link3  ...`

**Columns**:
1. **Name**: Profile name (in quotes)
2. **Links**: Space-separated list of link names to include in profile

**Example**:
```
[PROFILES]
;;Name           Links
;;-------------- ----------
"Main_Line"      C1 C2 C3 C4 C5
"Tributary_A"    C10 C11 C12
```

**Details**:
- Used by SWMM GUI to create profile plots showing elevation changes along a sequence of links
- Links should form a continuous path through the drainage network
- Profiles are visualization tools and don't affect simulation results

---

### [STREETS]
**Purpose**: Street cross-section parameters for inlet capture modeling (SWMM 5.2+)

**Format**: `Name  Tcrown  Hcurb  Sroad  nRoad  Hdep  Wdep  Sides  Wback  Sback  nBack`

**Columns**:
1. **Name**: Street cross-section identifier
2. **Tcrown**: Distance from curb to street crown (ft or m)
3. **Hcurb**: Curb height (ft or m)
4. **Sroad**: Street cross slope (%)
5. **nRoad**: Manning's n for street surface
6. **Hdep**: Height of gutter depression (ft or m)
7. **Wdep**: Width of gutter depression (ft or m)
8. **Sides**: 1 for one-sided street, 2 for two-sided
9. **Wback**: Width of back slope (ft or m)
10. **Sback**: Back slope (%)
11. **nBack**: Manning's n for back slope

**Example**:
```
[STREETS]
;;Name           Tcrown  Hcurb   Sroad   nRoad   Hdep    Wdep    Sides   Wback   Sback   nBack
;;-------------- ------- ------- ------- ------- ------- ------- ------- ------- ------- -------
Street1          20      0.5     2.0     0.016   0.167   2.0     1       0       0       0
Residential      15      0.5     2.5     0.016   0.125   2.0     2       5.0     4.0     0.05
```

**Details**:
- Used with inlet modeling to determine street flow depth and spread
- Back slope represents grassed area or other surface behind the curb
- Required for street inlet capture calculations

---

### [INLETS]
**Purpose**: Define street inlet capture devices (SWMM 5.2+)

**Format**: `Name  Type  Parameters...`

**Inlet Types and Parameters**:

**GRATE Inlets**: `Name  GRATE  Length  Width  Type`
- **Length**: Grate length (ft or m)
- **Width**: Grate width (ft or m)  
- **Type**: Grate type (P_BAR, P_BAR_50, CURVED_VANE, etc.)

**CURB Inlets**: `Name  CURB  Length  Height  Throat`
- **Length**: Opening length (ft or m)
- **Height**: Opening height (ft or m)
- **Throat**: Throat angle (degrees)

**SLOTTED Inlets**: `Name  SLOTTED  Length  Width`
- **Length**: Slot length (ft or m)
- **Width**: Slot width (ft or m)

**DROP_GRATE Inlets**: `Name  DROP_GRATE  Length  Width  Type`
- **Length**: Grate length (ft or m)
- **Width**: Grate width (ft or m)
- **Type**: Grate type

**DROP_CURB Inlets**: `Name  DROP_CURB  Length  Height`
- **Length**: Opening length (ft or m)
- **Height**: Opening height (ft or m)

**CUSTOM Inlets**: `Name  CUSTOM  CurveName`
- **CurveName**: Rating curve relating flow depth to capture efficiency

**Example**:
```
[INLETS]
;;Name           Type            Parameters
;;-------------- --------------- ---------------------------------
CurvedVaneGrate  GRATE           2.0  2.0  CURVED_VANE
CurbOpening      CURB            3.0  0.5  90
SlottedDrain     SLOTTED         4.0  0.5
CustomInlet      CUSTOM          INLET_CURVE
```

**Details**:
- Grate types include: P_BAR (parallel bar), CURVED_VANE, 45_DEGREE, 30_DEGREE, etc.
- Rating curves for CUSTOM inlets give capture efficiency vs. flow depth
- Used to model inlet capture efficiency on streets and in gutters

---

### [INLET_USAGE]
**Purpose**: Assignment of inlets to conduits (SWMM 5.2+)

**Format**: `Conduit  InletType  Node  Number  %Clogged  MaxFlow  LocalDepression  CustomWidth`

**Columns**:
1. **Conduit**: Conduit receiving captured flow
2. **InletType**: Name of inlet from [INLETS] section
3. **Node**: Node on street where inlet is located
4. **Number**: Number of inlet units
5. **%Clogged**: Percent of inlet area clogged (0-100)
6. **MaxFlow**: Maximum captured flow (0 = unlimited)
7. **LocalDepression**: Additional ponding depth at inlet (ft or m)
8. **CustomWidth**: (Optional) Custom width for on-sag inlets (ft or m)

**Example**:
```
[INLET_USAGE]
;;Conduit        InletType        Node             Number  %Clogged MaxFlow  LocalDepression
;;-------------- ---------------- ---------------- ------- -------- -------- --------
C1               CurvedVaneGrate  J5               1       0        0        0
C2               CurbOpening      J8               2       10       0        0.167
C3               CustomInlet      J12              1       0        5.0      0
```

**Details**:
- Captures runoff from street surface into drainage system
- Multiple inlets can be assigned to the same conduit
- Clogging reduces effective inlet area
- Local depression creates additional storage at the inlet location

---

## Specialized Sections

### [FILES]
**Purpose**: Reference to external interface files

**Format**: `FileType  "Filename"`

**File Types**:
- **RAINFALL**: Rainfall interface file
- **RUNOFF**: Runoff interface file
- **HOTSTART**: Hot start file to read
- **RDII**: RDII interface file
- **INFLOWS**: Inflows interface file
- **OUTFLOWS**: Outflows interface file

**Example**:
```
[FILES]
USE RAINFALL   "rainfall.dat"
SAVE HOTSTART  "hotstart.hsf"
```

---

### [TEMPERATURE]
**Purpose**: Temperature and climate data

**Format**: Multi-line with keywords

**Keywords**:
- **TIMESERIES**: Reference to temperature time series
- **FILE**: External climate file
- **WINDSPEED**: Wind speed options
- **SNOWMELT**: Snow melt parameters
- **ADC**: Areal depletion curve

**Example**:
```
[TEMPERATURE]
TIMESERIES TEMP_DATA
WINDSPEED  FILE
SNOWMELT   32.0  0.0  50.0  0.6  0.0  0.0  0.0
```

---

### [ADJUSTMENTS]
**Purpose**: Monthly climate adjustment factors

**Format**: `Parameter  Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov  Dec`

**Parameters**:
- **TEMPERATURE**: Temperature adjustment (degrees F or C)
- **EVAPORATION**: Evaporation factor
- **RAINFALL**: Rainfall factor
- **CONDUCTIVITY**: Soil hydraulic conductivity factor

**Example**:
```
[ADJUSTMENTS]
;;Parameter   Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov  Dec
TEMPERATURE   0.0  0.0  0.0  0.0  0.0  2.0  3.0  3.0  2.0  0.0  0.0  0.0
RAINFALL      1.0  1.0  1.0  1.0  1.0  1.2  1.2  1.2  1.0  1.0  1.0  1.0
```

---

### [SNOWPACKS]
**Purpose**: Snow accumulation and melt parameters

**Format**: Multi-line format with keywords PLOWABLE and IMPERV/PERV

**Example**:
```
[SNOWPACKS]
;;Name           Surface    Parameters
;;-------------- ---------- --------------------------------------
SNOWPACK1        PLOWABLE   0.001  0.001  32.0   0.10   0.00   0.00   0.0
SNOWPACK1        IMPERVIOUS 0.001  0.001  32.0   0.10   0.00   0.00   0.00  0.0
SNOWPACK1        PERVIOUS   0.001  0.001  32.0   0.10   0.00   0.00   0.00  0.0
SNOWPACK1        REMOVAL    1.0    0.0    0.0    0.0    0.0    0.0    1.0
```

---

### [DIVIDERS]
**Purpose**: Flow dividers (split flow between two outlets)

**Format**: `Name  Link  Type  [DivCurve/Parameters]  [Qmax]  [dHmax]  [Qcoeff]`

**Divider Types**:
- **CUTOFF**: Diverts flow above cutoff value
- **TABULAR**: Uses rating curve
- **WEIR**: Weir formula
- **OVERFLOW**: Diverts overflow above capacity

**Example**:
```
[DIVIDERS]
;;Name           Link             Type       Parameters
;;-------------- ---------------- ---------- --------------------
DIV1             C10              CUTOFF     5.0
DIV2             C15              TABULAR    DIV_CURVE
```

---

### [GWF]
**Purpose**: Groundwater flow equations (custom groundwater flow)

**Format**: Multi-line expressions

**Example**:
```
[GWF]
;;Subcatchment   Type       Expression
;;-------------- ---------- ------------------------------
S1               LATERAL    0.001 * (Hgw - Hsw)
S1               DEEP       0.0001 * Hgw
```

---

### [EVENTS]
**Purpose**: Event-based simulation controls

**Format**: `Start  [End]  [DryDays]`

**Example**:
```
[EVENTS]
;;Start Date      End Date        Dry Days
01/15/2020        01/20/2020      3
02/10/2020        02/15/2020      5
```

---

## Common File Patterns and Best Practices

### 1. **Minimum Viable Input File**

A basic SWMM file requires at minimum:
- `[TITLE]`
- `[OPTIONS]`
- `[EVAPORATION]`
- `[JUNCTIONS]` or `[OUTFALLS]` (at least one node)
- `[COORDINATES]` (for visualization)

### 2. **Typical Hydrology + Hydraulics File**

For rainfall-runoff with drainage system:
- `[TITLE]`, `[OPTIONS]`, `[EVAPORATION]`
- `[RAINGAGES]`, `[TIMESERIES]`
- `[SUBCATCHMENTS]`, `[SUBAREAS]`, `[INFILTRATION]`
- `[JUNCTIONS]`, `[OUTFALLS]`, `[STORAGE]`
- `[CONDUITS]`, `[XSECTIONS]`
- `[COORDINATES]`, `[VERTICES]`, `[Polygons]`
- `[REPORT]`

### 3. **Water Quality Modeling**

Add to basic file:
- `[POLLUTANTS]`
- `[LANDUSES]`, `[COVERAGES]`
- `[BUILDUP]`, `[WASHOFF]`
- `[TREATMENT]` (if treatment at nodes)
- `[DWF]` (for sanitary pollutant loads)

### 4. **Control Systems**

For pump controls and operations:
- `[PUMPS]`, `[CURVES]` (pump curves)
- `[CONTROLS]` (rule-based controls)
- `[PATTERNS]` (operational patterns)

### 5. **LID/Green Infrastructure**

For LID modeling:
- `[LID_CONTROLS]` (define LID types)
- `[LID_USAGE]` (assign to subcatchments)

---

## Data Units

Units are determined by the **FLOW_UNITS** option:

### US Customary (CFS, GPM, MGD)
- **Flow**: CFS, GPM, or MGD
- **Length**: feet
- **Area**: acres (subcatchments), sq ft (nodes)
- **Volume**: cubic feet
- **Rainfall**: inches
- **Concentration**: mg/L, μg/L, or #/L

### SI Metric (CMS, LPS, MLD)
- **Flow**: CMS, LPS, or MLD
- **Length**: meters
- **Area**: hectares (subcatchments), sq m (nodes)
- **Volume**: cubic meters
- **Rainfall**: millimeters
- **Concentration**: mg/L, μg/L, or #/L

---

## Important Notes

### File Processing Order
SWMM reads sections in any order, but processes them in a specific sequence during simulation setup.

### ID Naming Conventions
- **Maximum length**: Typically 31 characters
- **Allowed characters**: Letters, numbers, underscores
- **Avoid**: Spaces (use underscores), special characters
- **Case**: Case-insensitive

### Common Errors
1. **Missing required sections**: OPTIONS, EVAPORATION
2. **Mismatched references**: Rain gage not defined, curve not found
3. **Invalid cross-section geometry**: Negative dimensions
4. **Disconnected network**: Nodes with no outlets
5. **Circular references**: Subcatchment outlets to each other
6. **Unit inconsistency**: Mixing US/SI units

### Version Compatibility
- **SWMM 5.0+**: Most modern features
- **SWMM 5.1+**: LID controls, improved hydraulics, enhanced reporting
- **SWMM 5.2+**: Street/inlet modeling ([STREETS], [INLETS], [INLET_USAGE]), API improvements, real-time controls

Different versions may support additional sections or parameters. The most current version is SWMM 5.2.4 (as of 2023).

---

## Resources

- **EPA SWMM Official**: https://www.epa.gov/water-research/storm-water-management-model-swmm
- **User's Manual**: Comprehensive guide to all options
- **Reference Manuals**: 
  - Volume I: Hydrology
  - Volume II: Hydraulics
  - Volume III: Water Quality
- **Applications Manual**: Real-world modeling examples

---

## Summary

SWMM input files are comprehensive text-based specifications that describe:
1. **Physical system**: Nodes, links, subcatchments
2. **Hydrologic processes**: Rainfall, infiltration, runoff
3. **Hydraulic routing**: Flow through conduits and structures
4. **Water quality**: Pollutant buildup, washoff, and routing
5. **Controls**: Operational rules for pumps and gates
6. **LID**: Green infrastructure practices
7. **Time-varying inputs**: Rainfall, inflows, boundary conditions

The modular section-based format allows for flexible model construction, from simple drainage networks to complex integrated systems with detailed water quality simulation.
