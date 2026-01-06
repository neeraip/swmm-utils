"""Test SWMM .inp file decoder (low-level API).

Tests the SwmmInputDecoder class for parsing .inp files.
"""

import pytest
import sys
from pathlib import Path
from io import StringIO

# Add parent directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "python"))

from swmm_utils import SwmmInputDecoder


# Sample SWMM input for testing - comprehensive with all section types
SAMPLE_INP = """
[TITLE]
Test SWMM Model
Comprehensive test model with all section types

[OPTIONS]
FLOW_UNITS           CFS
INFILTRATION         HORTON
FLOW_ROUTING         DYNWAVE
START_DATE           01/01/2020
END_DATE             01/02/2020
REPORT_START_DATE    01/01/2020
START_TIME           00:00:00
END_TIME             24:00:00
REPORT_STEP          00:15:00

[EVAPORATION]
;;Data Source    Parameters
CONSTANT         0.1

[RAINGAGES]
;;Name           Format    Interval SCF      Source    
RG1              INTENSITY 1:00     1.0      TIMESERIES TS1

[SUBCATCHMENTS]
;;Name           Rain Gage        Outlet           Area     %Imperv  Width    %Slope   CurbLen  
S1               RG1              J1               5.0      25.0     500.0    0.5      0        
S2               RG1              J2               3.0      15.0     300.0    0.3      0        

[SUBAREAS]
;;Subcatchment   N-Imperv   N-Perv     S-Imperv   S-Perv     PctZero    RouteTo    
S1               0.01       0.1        0.05       0.05       25.0       OUTLET     
S2               0.01       0.1        0.05       0.05       25.0       OUTLET     

[INFILTRATION]
;;Subcatchment   Param1     Param2     Param3     Param4     Param5    
S1               3.0        0.5        0.25       7          0         
S2               3.0        0.5        0.25       7          0         

[JUNCTIONS]
;;Name           Elevation  MaxDepth   InitDepth  SurDepth   Aponded   
J1               100.0      15.0       0          0          0         
J2               95.0       15.0       0          0          0         

[OUTFALLS]
;;Name           Elevation  Type       Stage Data       Gated    
OUT1             90.0       FREE                        NO       

[CONDUITS]
;;Name           From Node        To Node          Length     Roughness  InOffset   OutOffset  
C1               J1               J2               400.0      0.01       0          0          
C2               J2               OUT1             400.0      0.01       0          0          

[PUMPS]
;;Name           From Node        To Node          Curve        Status   StartDepth StopDepth
P1               J1               OUT1             PUMP1        ON       0          0

[ORIFICES]
;;Name           From Node        To Node          Type         CrestHgt   Disch.Coeff  FloodGate
OR1              J1               J2               BOTTOM       0          0.65         NO

[WEIRS]
;;Name           From Node        To Node          Type         CrestHgt   Disch.Coeff  Floodgate  EndCon  EndCoef
WR1              J1               J2               TRANSVERSE   0.0        1.0          NO         0       0

[STORAGE]
;;Name           Elev    MaxDepth    InitDepth   Shape        Curve  N/A  EvapFrac
STO1             90.0    20.0        0           TABULAR      STOR1  0    0

[LOSSES]
;;Link           Inlet    Outlet   Average   Floodgate
C1               0        0        0         NO
C2               0        0        0         NO

[CURVES]
;;Name           Type        X-Value   Y-Value
PUMP1            Pump        0         0
PUMP1                         1         1
PUMP1                         2         0.5
STOR1            Storage     0         0
STOR1                         2         100
STOR1                         4         300

[INFLOWS]
;;Node           Type        Rate   Scale  Baseline Pattern
J1               FLOW        1.0    1.0    0       

[DWF]
;;Node           Type        AvgFlow   Pattern
J1               FLOW        0.5       

[PATTERNS]
;;Name           Type    Multipliers
PAT1             HOURLY  0.5 0.6 0.7 0.8 0.9 1.0 1.0 1.0 1.0 0.9 0.8 0.7
PAT1                     0.6 0.5 0.5 0.6 0.7 0.8 0.9 1.0 1.0 0.9 0.8 0.7

[CONTROLS]
;;Type          Condition                        ThenAction                ElseAction
LINK            P1                               SETTING = 1.0             SETTING = 0

[XSECTIONS]
;;Link           Shape        Geom1            Geom2      Geom3      Geom4      Barrels    
C1               CIRCULAR     1.0              0          0          0          1          
C2               CIRCULAR     1.0              0          0          0          1          

[TIMESERIES]
C2               CIRCULAR     1.0              0          0          0          1          

[POLLUTANTS]
;;Name           Units  CRain    CGW      CRDII    KDecay   SnowOnly
POL1             mg/L   0        0        0        0        NO
POL2             ug/L   0.1      0.05     0        0        NO

[LANDUSES]
;;Name           PercentImperv
LAND1            25
LAND2            75

[COVERAGES]
;;Subcatchment   LandUse          Percent
S1               LAND1            100
S2               LAND2            100

[BUILDUP]
;;LandUse         Pollutant        Function   Coeff1   Coeff2   Coeff3
LAND1            POL1             LINEAR     10       0        0
LAND2            POL2             POWER      5        0.5      0

[WASHOFF]
;;LandUse         Pollutant        Function   Coeff1   Coeff2   Sweepable
LAND1            POL1             EMC        5        0        100
LAND2            POL2             RATING     0.01     0.5      50

[LID_CONTROLS]
;;Name           Type/Layer Parameters
LID1             BC

[LID_USAGE]
;;Subcatchment   LID Process      Number   Area     Width    InitSat  FromImp   ToPerv
S1               LID1             1        1000     10       0        0         0

[FILES]
;;Type            File Path
RAINFALL          /path/to/rain.dat

[HYDROGRAPHS]
;;Name           Response      R1-R2          Values
UH1              R   0

[RDII]
;;Node           UnitHydrograph  SewerArea   Factor
J1               UH1             0.5         1.0

[TIMESERIES]
;;Name           Date       Time       Value     
TS1                         0:00       0.0       
TS1                         1:00       0.5       
TS1                         2:00       0.2       

[COORDINATES]
;;Node           X-Coord            Y-Coord           
J1               0.0                100.0             
J2               100.0              100.0             
OUT1             200.0              100.0             

[VERTICES]
;;Link           X-Coord            Y-Coord           
C1               50.0               100.0             

[POLYGONS]
;;Subcatchment   X-Coord            Y-Coord           
S1               -50.0              150.0             
S1               -50.0              50.0              
S1               50.0               50.0              
S1               50.0               150.0             
S2               100.0             150.0             
S2               100.0             50.0              
S2               150.0             50.0              
S2               150.0             150.0             

[SYMBOLS]
;;Gage           X-Coord            Y-Coord           
RG1              -100.0             200.0             

[TAGS]
;;Type           Name             Tag              
Subcatchment     S1               RESIDENTIAL
Subcatchment     S2               COMMERCIAL

[LABELS]
;;X-Coord            Y-Coord             Text
-100.0              -50.0               Inflow_Area

[MAP]
;;Dimensions    Units  
0.0 250.0 0.0 250.0 1

[OUTLETS]
;;Name           Elev    Type       Stage Data       Curve
OL1              85.0    TIDAL      0                

[REPORT]
;;Reporting Options
INPUT YES

[BACKDROP]
;;Backdrop File Path and Dimensions
FILE             /path/to/backdrop.bmp
DIMENSIONS       0 0 250 250

[TRANSECTS]
;;Transect Name   X-Coord   Y-Coord   Z-Elev
TR1               0         0         10
TR1               10        0         9
TR1               20        0         8

[PROFILES]
;;Link      Profile_Name
C1          PROF1
"""


@pytest.fixture
def sample_model():
    """Decode the sample input and return the model."""
    decoder = SwmmInputDecoder()
    model = decoder.decode(StringIO(SAMPLE_INP))
    return model


def test_decoder_title(sample_model):
    """Test decoding of [TITLE] section."""
    assert "title" in sample_model
    assert "Test SWMM Model" in sample_model["title"]


def test_decoder_options(sample_model):
    """Test decoding of [OPTIONS] section."""
    assert "options" in sample_model
    options = sample_model["options"]
    assert options["FLOW_UNITS"] == "CFS"
    assert options["INFILTRATION"] == "HORTON"
    assert options["FLOW_ROUTING"] == "DYNWAVE"


def test_decoder_raingages(sample_model):
    """Test decoding of [RAINGAGES] section."""
    assert "raingages" in sample_model
    assert len(sample_model["raingages"]) == 1
    gage = sample_model["raingages"][0]
    assert gage["name"] == "RG1"
    assert gage["format"] == "INTENSITY"
    assert gage["interval"] == "1:00"


def test_decoder_subcatchments(sample_model):
    """Test decoding of [SUBCATCHMENTS] section."""
    assert "subcatchments" in sample_model
    assert len(sample_model["subcatchments"]) == 2
    sub = sample_model["subcatchments"][0]
    assert sub["name"] == "S1"
    assert sub["area"] == "5.0"
    assert sub["imperv"] == "25.0"


def test_decoder_junctions(sample_model):
    """Test decoding of [JUNCTIONS] section."""
    assert "junctions" in sample_model
    assert len(sample_model["junctions"]) == 2
    j1 = sample_model["junctions"][0]
    assert j1["name"] == "J1"
    assert j1["elevation"] == "100.0"
    assert j1["max_depth"] == "15.0"


def test_decoder_outfalls(sample_model):
    """Test decoding of [OUTFALLS] section."""
    assert "outfalls" in sample_model
    assert len(sample_model["outfalls"]) == 1
    out = sample_model["outfalls"][0]
    assert out["name"] == "OUT1"
    assert out["type"] == "FREE"


def test_decoder_conduits(sample_model):
    """Test decoding of [CONDUITS] section."""
    assert "conduits" in sample_model
    assert len(sample_model["conduits"]) == 2
    c1 = sample_model["conduits"][0]
    assert c1["name"] == "C1"
    assert c1["from_node"] == "J1"
    assert c1["to_node"] == "J2"


def test_decoder_xsections(sample_model):
    """Test decoding of [XSECTIONS] section."""
    assert "xsections" in sample_model
    assert len(sample_model["xsections"]) == 2
    xs = sample_model["xsections"][0]
    assert xs["link"] == "C1"
    assert xs["shape"] == "CIRCULAR"


def test_decoder_timeseries(sample_model):
    """Test decoding of [TIMESERIES] section."""
    assert "timeseries" in sample_model
    assert "TS1" in sample_model["timeseries"]
    ts = sample_model["timeseries"]["TS1"]
    assert len(ts) == 3
    assert ts[0]["time"] == "0:00"
    assert ts[0]["value"] == "0.0"


def test_decoder_coordinates(sample_model):
    """Test decoding of [COORDINATES] section."""
    assert "coordinates" in sample_model
    assert len(sample_model["coordinates"]) == 3


def test_decoder_sample_model_pollutants(sample_model):
    """Test pollutants in comprehensive sample model."""
    assert "pollutants" in sample_model
    assert len(sample_model["pollutants"]) == 2
    assert sample_model["pollutants"][0]["name"] == "POL1"
    assert sample_model["pollutants"][1]["name"] == "POL2"


def test_decoder_sample_model_landuses(sample_model):
    """Test landuses in comprehensive sample model."""
    assert "landuses" in sample_model
    assert len(sample_model["landuses"]) == 2
    assert sample_model["landuses"][0]["name"] == "LAND1"
    assert sample_model["landuses"][1]["name"] == "LAND2"


def test_decoder_sample_model_coverages(sample_model):
    """Test coverages in comprehensive sample model."""
    assert "coverages" in sample_model
    assert len(sample_model["coverages"]) == 2
    assert sample_model["coverages"][0]["subcatchment"] == "S1"
    assert sample_model["coverages"][0]["landuse"] == "LAND1"


def test_decoder_sample_model_buildup(sample_model):
    """Test buildup in comprehensive sample model."""
    assert "buildup" in sample_model
    assert len(sample_model["buildup"]) == 2
    assert sample_model["buildup"][0]["landuse"] == "LAND1"
    assert sample_model["buildup"][0]["pollutant"] == "POL1"
    assert sample_model["buildup"][0]["function"] == "LINEAR"


def test_decoder_sample_model_washoff(sample_model):
    """Test washoff in comprehensive sample model."""
    assert "washoff" in sample_model
    assert len(sample_model["washoff"]) == 2
    assert sample_model["washoff"][0]["landuse"] == "LAND1"
    assert sample_model["washoff"][0]["pollutant"] == "POL1"
    assert sample_model["washoff"][0]["function"] == "EMC"


def test_decoder_sample_model_lid_controls(sample_model):
    """Test lid_controls in comprehensive sample model."""
    assert "lid_controls" in sample_model
    assert len(sample_model["lid_controls"]) >= 1


def test_decoder_sample_model_lid_usage(sample_model):
    """Test lid_usage in comprehensive sample model."""
    assert "lid_usage" in sample_model
    assert len(sample_model["lid_usage"]) >= 1


def test_decoder_sample_model_files(sample_model):
    """Test files in comprehensive sample model."""
    assert "files" in sample_model
    assert len(sample_model["files"]) >= 1


def test_decoder_sample_model_hydrographs(sample_model):
    """Test hydrographs in comprehensive sample model."""
    assert "hydrographs" in sample_model


def test_decoder_sample_model_rdii(sample_model):
    """Test rdii in comprehensive sample model."""
    assert "rdii" in sample_model
    assert len(sample_model["rdii"]) >= 1


def test_decoder_pollutants():
    """Test decoding of [POLLUTANTS] section."""
    inp_with_pollutants = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[POLLUTANTS]
;;Name           Units  ConcInit  ConcPpt   ConcSnow  ConcGW   
POL1             mg/L   0         0         0         0
POL2             ug/L   0.1       0.2       0.3       0.4
"""

    decoder = SwmmInputDecoder()
    model = decoder.decode(StringIO(inp_with_pollutants))

    assert "pollutants" in model
    assert len(model["pollutants"]) == 2
    pol1 = model["pollutants"][0]
    assert pol1["name"] == "POL1"
    assert pol1["units"] == "mg/L"

    pol2 = model["pollutants"][1]
    assert pol2["name"] == "POL2"
    assert pol2["units"] == "ug/L"


def test_decoder_landuses():
    """Test decoding of [LANDUSES] section."""
    inp_with_landuses = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[LANDUSES]
;;Name           PercentImperv
LAND1            25
LAND2            75
"""

    decoder = SwmmInputDecoder()
    model = decoder.decode(StringIO(inp_with_landuses))

    assert "landuses" in model
    assert len(model["landuses"]) == 2
    land1 = model["landuses"][0]
    assert land1["name"] == "LAND1"
    assert land1["percent_imperv"] == "25"


def test_decoder_coverages():
    """Test decoding of [COVERAGES] section."""
    inp_with_coverages = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[COVERAGES]
;;Subcatchment   LandUse          Percent
S1               LAND1            100
S2               LAND2            50
"""

    decoder = SwmmInputDecoder()
    model = decoder.decode(StringIO(inp_with_coverages))

    assert "coverages" in model
    assert len(model["coverages"]) == 2
    cov1 = model["coverages"][0]
    assert cov1["subcatchment"] == "S1"
    assert cov1["landuse"] == "LAND1"


def test_decoder_buildup():
    """Test decoding of [BUILDUP] section."""
    inp_with_buildup = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[BUILDUP]
;;LandUse         Pollutant        Function   Coeff1   Coeff2   Coeff3   
LAND1            POL1             LINEAR     10       0        0        
LAND2            POL2             POWER      5        0.5      0        
"""

    decoder = SwmmInputDecoder()
    model = decoder.decode(StringIO(inp_with_buildup))

    assert "buildup" in model
    assert len(model["buildup"]) == 2
    b1 = model["buildup"][0]
    assert b1["landuse"] == "LAND1"
    assert b1["pollutant"] == "POL1"
    assert b1["function"] == "LINEAR"


def test_decoder_washoff():
    """Test decoding of [WASHOFF] section."""
    inp_with_washoff = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[WASHOFF]
;;LandUse         Pollutant        Function   Coeff1   Coeff2   Sweepable
LAND1            POL1             EMC        5        0        100
LAND2            POL2             RATING     0.01     0.5      50
"""

    decoder = SwmmInputDecoder()
    model = decoder.decode(StringIO(inp_with_washoff))

    assert "washoff" in model
    assert len(model["washoff"]) == 2
    w1 = model["washoff"][0]
    assert w1["landuse"] == "LAND1"
    assert w1["pollutant"] == "POL1"


def test_decoder_lid_controls():
    """Test decoding of [LID_CONTROLS] section."""
    inp_with_lids = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[LID_CONTROLS]
;;Name           Type/Layer Parameters
LID1             BC
"""

    decoder = SwmmInputDecoder()
    model = decoder.decode(StringIO(inp_with_lids))

    assert "lid_controls" in model
    assert len(model["lid_controls"]) >= 1


def test_decoder_lid_usage():
    """Test decoding of [LID_USAGE] section."""
    inp_with_lid_usage = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[LID_USAGE]
;;Subcatchment   LID Process      Number   Area     Width    InitSat  FromImp   ToPerv   RptFile     DrainTo
S1               LID1             1        1000     10       0        0         0                    
"""

    decoder = SwmmInputDecoder()
    model = decoder.decode(StringIO(inp_with_lid_usage))

    assert "lid_usage" in model
    assert len(model["lid_usage"]) >= 1


def test_decoder_files():
    """Test decoding of [FILES] section."""
    inp_with_files = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[FILES]
;;Type            File Path
RAINFALL          /path/to/rain.dat
TEMPERATURE       /path/to/temp.dat
"""

    decoder = SwmmInputDecoder()
    model = decoder.decode(StringIO(inp_with_files))

    assert "files" in model
    assert len(model["files"]) >= 1


def test_decoder_hydrographs():
    """Test decoding of [HYDROGRAPHS] section."""
    inp_with_hydro = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[HYDROGRAPHS]
;;Name           Response      R1-R2          Values
UH1              R   0
"""

    decoder = SwmmInputDecoder()
    model = decoder.decode(StringIO(inp_with_hydro))

    assert "hydrographs" in model
    # Hydrographs may be empty in this simple case


def test_decoder_rdii():
    """Test decoding of [RDII] section."""
    inp_with_rdii = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[RDII]
;;Node           UnitHydrograph  SewerArea   Factor
J1               UH1             0.5         1.0
"""

    decoder = SwmmInputDecoder()
    model = decoder.decode(StringIO(inp_with_rdii))

    assert "rdii" in model
    assert len(model["rdii"]) >= 1
    rdii1 = model["rdii"][0]
    assert rdii1["node"] == "J1"
    assert rdii1["unithydrograph"] == "UH1"


def test_decoder_comments_and_whitespace():
    """Test that decoder handles comments and whitespace correctly."""
    inp_with_comments = """
[TITLE]
;; This is a comment
Test Model

[OPTIONS]
FLOW_UNITS    CFS  ; inline comment
  ; Another comment
INFILTRATION  HORTON

[JUNCTIONS]
;; Junction data
J1    100.0    15.0    0    0    0
; Comment line
J2    95.0     15.0    0    0    0  ; inline
"""

    decoder = SwmmInputDecoder()
    model = decoder.decode(StringIO(inp_with_comments))

    assert "title" in model
    assert "Test Model" in model["title"]
    assert len(model["junctions"]) == 2


def test_decoder_empty_sections():
    """Test decoder with minimal input."""
    minimal_inp = """
[TITLE]
Minimal Model

[OPTIONS]
FLOW_UNITS    CFS
"""

    decoder = SwmmInputDecoder()
    model = decoder.decode(StringIO(minimal_inp))

    assert "title" in model
    assert "options" in model
    assert model["options"]["FLOW_UNITS"] == "CFS"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
