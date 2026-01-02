"""Test SWMM .inp file decoder and encoder (low-level API).

Tests the SwmmInputDecoder and SwmmInputEncoder classes for parsing
and generating .inp files.
"""

import pytest
import sys
from pathlib import Path
from io import StringIO

# Add parent directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "python"))

from swmm_utils import SwmmInputDecoder, SwmmInputEncoder


# Sample SWMM input for testing
SAMPLE_INP = """
[TITLE]
Test SWMM Model
Simple test model for parser validation

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

[RAINGAGES]
;;Name           Format    Interval SCF      Source    
RG1              INTENSITY 1:00     1.0      TIMESERIES TS1

[SUBCATCHMENTS]
;;Name           Rain Gage        Outlet           Area     %Imperv  Width    %Slope   CurbLen  
S1               RG1              J1               5.0      25.0     500.0    0.5      0        

[SUBAREAS]
;;Subcatchment   N-Imperv   N-Perv     S-Imperv   S-Perv     PctZero    RouteTo    
S1               0.01       0.1        0.05       0.05       25.0       OUTLET     

[INFILTRATION]
;;Subcatchment   Param1     Param2     Param3     Param4     Param5    
S1               3.0        0.5        0.25       7          0         

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

[XSECTIONS]
;;Link           Shape        Geom1            Geom2      Geom3      Geom4      Barrels    
C1               CIRCULAR     1.0              0          0          0          1          
C2               CIRCULAR     1.0              0          0          0          1          

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
"""


@pytest.fixture
def sample_model():
    """Parse the sample input and return the model."""
    parser = SwmmInputDecoder()
    model = parser.decode(StringIO(SAMPLE_INP))
    return model


def test_parser_title(sample_model):
    """Test parsing of [TITLE] section."""
    assert "title" in sample_model
    assert "Test SWMM Model" in sample_model["title"]


def test_parser_options(sample_model):
    """Test parsing of [OPTIONS] section."""
    assert "options" in sample_model
    options = sample_model["options"]
    assert options["FLOW_UNITS"] == "CFS"
    assert options["INFILTRATION"] == "HORTON"
    assert options["FLOW_ROUTING"] == "DYNWAVE"


def test_parser_raingages(sample_model):
    """Test parsing of [RAINGAGES] section."""
    assert "raingages" in sample_model
    assert len(sample_model["raingages"]) == 1
    gage = sample_model["raingages"][0]
    assert gage["name"] == "RG1"
    assert gage["format"] == "INTENSITY"
    assert gage["interval"] == "1:00"


def test_parser_subcatchments(sample_model):
    """Test parsing of [SUBCATCHMENTS] section."""
    assert "subcatchments" in sample_model
    assert len(sample_model["subcatchments"]) == 1
    sub = sample_model["subcatchments"][0]
    assert sub["name"] == "S1"
    assert sub["area"] == "5.0"
    assert sub["imperv"] == "25.0"


def test_parser_junctions(sample_model):
    """Test parsing of [JUNCTIONS] section."""
    assert "junctions" in sample_model
    assert len(sample_model["junctions"]) == 2
    j1 = sample_model["junctions"][0]
    assert j1["name"] == "J1"
    assert j1["elevation"] == "100.0"
    assert j1["max_depth"] == "15.0"


def test_parser_outfalls(sample_model):
    """Test parsing of [OUTFALLS] section."""
    assert "outfalls" in sample_model
    assert len(sample_model["outfalls"]) == 1
    out = sample_model["outfalls"][0]
    assert out["name"] == "OUT1"
    assert out["type"] == "FREE"


def test_parser_conduits(sample_model):
    """Test parsing of [CONDUITS] section."""
    assert "conduits" in sample_model
    assert len(sample_model["conduits"]) == 2
    c1 = sample_model["conduits"][0]
    assert c1["name"] == "C1"
    assert c1["from_node"] == "J1"
    assert c1["to_node"] == "J2"


def test_parser_xsections(sample_model):
    """Test parsing of [XSECTIONS] section."""
    assert "xsections" in sample_model
    assert len(sample_model["xsections"]) == 2
    xs = sample_model["xsections"][0]
    assert xs["link"] == "C1"
    assert xs["shape"] == "CIRCULAR"


def test_parser_timeseries(sample_model):
    """Test parsing of [TIMESERIES] section."""
    assert "timeseries" in sample_model
    assert "TS1" in sample_model["timeseries"]
    ts = sample_model["timeseries"]["TS1"]
    assert len(ts) == 3
    assert ts[0]["time"] == "0:00"
    assert ts[0]["value"] == "0.0"


def test_parser_coordinates(sample_model):
    """Test parsing of [COORDINATES] section."""
    assert "coordinates" in sample_model
    assert len(sample_model["coordinates"]) == 3


def test_converter_json(sample_model, tmp_path):
    """Test JSON conversion."""
    converter = SwmmInputEncoder()

    # Convert to JSON
    json_file = tmp_path / "test.json"
    json_str = converter.encode_to_json(sample_model, str(json_file))

    assert json_file.exists()
    assert "title" in json_str

    # Load back from JSON
    model_from_json = converter.from_json(str(json_file))
    assert model_from_json["options"]["FLOW_UNITS"] == "CFS"


def test_unparser(sample_model, tmp_path):
    """Test unparsing back to .inp format."""
    unparser = SwmmInputEncoder()

    output_file = tmp_path / "test_output.inp"
    unparser.encode_to_inp_file(sample_model, str(output_file))

    assert output_file.exists()

    # Read the output and check for key sections
    content = output_file.read_text()
    assert "[TITLE]" in content
    assert "[OPTIONS]" in content
    assert "[JUNCTIONS]" in content
    assert "[CONDUITS]" in content


def test_roundtrip(tmp_path):
    """Test full round-trip: parse → unparse → parse."""
    parser = SwmmInputDecoder()
    unparser = SwmmInputEncoder()

    # Parse original
    model1 = parser.decode(StringIO(SAMPLE_INP))

    # Unparse to file
    temp_file = tmp_path / "roundtrip.inp"
    unparser.encode_to_inp_file(model1, str(temp_file))

    # Parse again
    model2 = parser.decode_file(str(temp_file))

    # Compare key sections
    assert model1["options"]["FLOW_UNITS"] == model2["options"]["FLOW_UNITS"]
    assert len(model1["junctions"]) == len(model2["junctions"])
    assert len(model1["conduits"]) == len(model2["conduits"])


def test_parser_comments_and_whitespace():
    """Test that parser handles comments and whitespace correctly."""
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

    parser = SwmmInputDecoder()
    model = parser.decode(StringIO(inp_with_comments))

    assert "title" in model
    assert "Test Model" in model["title"]
    assert len(model["junctions"]) == 2


def test_parser_empty_sections():
    """Test parser with minimal input."""
    minimal_inp = """
[TITLE]
Minimal Model

[OPTIONS]
FLOW_UNITS    CFS
"""

    parser = SwmmInputDecoder()
    model = parser.decode(StringIO(minimal_inp))

    assert "title" in model
    assert "options" in model
    assert model["options"]["FLOW_UNITS"] == "CFS"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
