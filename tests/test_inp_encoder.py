"""Test SWMM .inp file encoder (low-level API).

Tests the SwmmInputEncoder class for generating .inp files.
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
Simple test model for decoder validation

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
    """Decode the sample input and return the model."""
    decoder = SwmmInputDecoder()
    model = decoder.decode(StringIO(SAMPLE_INP))
    return model


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


def test_encoder_writes_inp(sample_model, tmp_path):
    """Test encoding to .inp file."""
    encoder = SwmmInputEncoder()

    output_file = tmp_path / "test_output.inp"
    encoder.encode_to_inp_file(sample_model, str(output_file))

    assert output_file.exists()

    # Read the output and check for key sections
    content = output_file.read_text()
    assert "[TITLE]" in content
    assert "[OPTIONS]" in content
    assert "[JUNCTIONS]" in content
    assert "[CONDUITS]" in content


def test_roundtrip(tmp_path):
    """Test full round-trip: decode → encode → decode."""
    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    # Decode original
    model1 = decoder.decode(StringIO(SAMPLE_INP))

    # Encode to file
    temp_file = tmp_path / "roundtrip.inp"
    encoder.encode_to_inp_file(model1, str(temp_file))

    # Decode again
    model2 = decoder.decode_file(str(temp_file))

    # Compare key sections
    assert model1["options"]["FLOW_UNITS"] == model2["options"]["FLOW_UNITS"]
    assert len(model1["junctions"]) == len(model2["junctions"])
    assert len(model1["conduits"]) == len(model2["conduits"])


# DATAFRAME TESTS
def test_encoder_to_dataframe_single_section():
    """Test encoding a single section to DataFrame."""
    pd = pytest.importorskip("pandas")
    encoder = SwmmInputEncoder()
    
    model = {
        "junctions": [
            {"name": "J1", "elevation": 100, "max_depth": 5},
            {"name": "J2", "elevation": 95, "max_depth": 6},
        ]
    }
    
    df = encoder.encode_to_dataframe(model, section="junctions")
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["name", "elevation", "max_depth"]
    assert df["name"].tolist() == ["J1", "J2"]


def test_encoder_to_dataframe_all_sections():
    """Test encoding all sections to DataFrame dictionary."""
    pd = pytest.importorskip("pandas")
    encoder = SwmmInputEncoder()
    
    model = {
        "junctions": [
            {"name": "J1", "elevation": 100},
            {"name": "J2", "elevation": 95},
        ],
        "outfalls": [
            {"name": "O1", "elevation": 80},
        ],
        "title": "Test Model",
    }
    
    dfs = encoder.encode_to_dataframe(model)
    
    assert isinstance(dfs, dict)
    assert "junctions" in dfs
    assert "outfalls" in dfs
    assert "title" not in dfs  # String sections excluded
    assert len(dfs["junctions"]) == 2
    assert len(dfs["outfalls"]) == 1


def test_encoder_to_dataframe_empty_section():
    """Test encoding empty section returns empty DataFrame."""
    pd = pytest.importorskip("pandas")
    encoder = SwmmInputEncoder()
    
    model = {"junctions": []}
    
    df = encoder.encode_to_dataframe(model, section="junctions")
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_encoder_to_dataframe_nonexistent_section():
    """Test error when section doesn't exist."""
    encoder = SwmmInputEncoder()
    
    model = {"junctions": []}
    
    with pytest.raises(ValueError, match="not found in model"):
        encoder.encode_to_dataframe(model, section="nonexistent")


def test_encoder_to_dataframe_non_list_section():
    """Test error when section is not a list."""
    encoder = SwmmInputEncoder()
    
    model = {"title": "Test Model"}
    
    with pytest.raises(ValueError, match="is not a list"):
        encoder.encode_to_dataframe(model, section="title")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

