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
    """Test full round-trip: decode → encode → decode with semantic equivalence."""
    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    # Decode original
    model1 = decoder.decode(StringIO(SAMPLE_INP))

    # Encode to file
    temp_file = tmp_path / "roundtrip.inp"
    encoder.encode_to_inp_file(model1, str(temp_file))

    # Decode again
    model2 = decoder.decode_file(str(temp_file))

    # Compare all sections that should be present
    assert model1["title"] == model2["title"], "Title mismatch"
    assert model1["options"] == model2["options"], "Options mismatch"

    # Compare list sections
    assert len(model1["raingages"]) == len(
        model2["raingages"]
    ), "Raingages count mismatch"
    assert len(model1["subcatchments"]) == len(
        model2["subcatchments"]
    ), "Subcatchments count mismatch"
    assert len(model1["junctions"]) == len(
        model2["junctions"]
    ), "Junctions count mismatch"
    assert len(model1["outfalls"]) == len(model2["outfalls"]), "Outfalls count mismatch"
    assert len(model1["conduits"]) == len(model2["conduits"]), "Conduits count mismatch"

    # Deep comparison of specific items
    for i, j1 in enumerate(model1["junctions"]):
        j2 = model2["junctions"][i]
        assert j1["name"] == j2["name"], f"Junction {i} name mismatch"
        assert j1["elevation"] == j2["elevation"], f"Junction {i} elevation mismatch"


def test_roundtrip_with_quality_sections(tmp_path):
    """Test round-trip with quality/pollution sections."""
    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    inp_with_quality = """
[TITLE]
Quality Model

[OPTIONS]
FLOW_UNITS    CFS

[JUNCTIONS]
;;Name           Elevation  MaxDepth   InitDepth  SurDepth   Aponded   
J1               100.0      15.0       0          0          0         

[OUTFALLS]
;;Name           Elevation  Type       Stage Data       Gated    
OUT1             90.0       FREE                        NO       

[CONDUITS]
;;Name           From Node        To Node          Length     Roughness  InOffset   OutOffset  
C1               J1               OUT1             400.0      0.01       0          0          

[XSECTIONS]
;;Link           Shape        Geom1            Geom2      Geom3      Geom4      Barrels    
C1               CIRCULAR     1.0              0          0          0          1          

[POLLUTANTS]
;;Name           Units  
POL1             mg/L   
POL2             ug/L   

[LANDUSES]
;;Name           PercentImperv
LAND1            25
LAND2            75

[COVERAGES]
;;Subcatchment   LandUse          Percent
S1               LAND1            50
S1               LAND2            50

[BUILDUP]
;;LandUse         Pollutant        Function   Coeff1   
LAND1            POL1             LINEAR     10       
LAND2            POL2             POWER      5        

[WASHOFF]
;;LandUse         Pollutant        Function   Coeff1   
LAND1            POL1             EMC        5        
LAND2            POL2             RATING     0.01     

[TIMESERIES]
;;Name           Date       Time       Value     
TS1                         0:00       0.0       
TS1                         1:00       0.5       
"""

    # Decode original
    model1 = decoder.decode(StringIO(inp_with_quality))

    # Encode to file
    temp_file = tmp_path / "roundtrip_quality.inp"
    encoder.encode_to_file(model1, str(temp_file))

    # Decode again
    model2 = decoder.decode_file(str(temp_file))

    # Verify quality sections round-trip with semantic equivalence
    # (re-encoded data may have additional default fields filled in)

    assert (
        "pollutants" in model1 and "pollutants" in model2
    ), "Missing pollutants section"
    assert len(model1["pollutants"]) == len(
        model2["pollutants"]
    ), "Pollutants count mismatch"
    # Check primary fields match
    for i, p1 in enumerate(model1["pollutants"]):
        p2 = model2["pollutants"][i]
        assert p1["name"] == p2["name"], f"Pollutant {i} name mismatch"
        assert p1["units"] == p2["units"], f"Pollutant {i} units mismatch"

    assert "landuses" in model1 and "landuses" in model2, "Missing landuses section"
    assert len(model1["landuses"]) == len(model2["landuses"]), "Landuses count mismatch"
    for i, l1 in enumerate(model1["landuses"]):
        l2 = model2["landuses"][i]
        assert l1["name"] == l2["name"], f"Landuse {i} name mismatch"
        assert (
            l1["percent_imperv"] == l2["percent_imperv"]
        ), f"Landuse {i} percent_imperv mismatch"

    assert "coverages" in model1 and "coverages" in model2, "Missing coverages section"
    assert len(model1["coverages"]) == len(
        model2["coverages"]
    ), "Coverages count mismatch"
    assert model1["coverages"] == model2["coverages"], "Coverages data mismatch"

    assert "buildup" in model1 and "buildup" in model2, "Missing buildup section"
    assert len(model1["buildup"]) == len(model2["buildup"]), "Buildup count mismatch"
    for i, b1 in enumerate(model1["buildup"]):
        b2 = model2["buildup"][i]
        assert b1["landuse"] == b2["landuse"], f"Buildup {i} landuse mismatch"
        assert b1["pollutant"] == b2["pollutant"], f"Buildup {i} pollutant mismatch"
        assert b1["function"] == b2["function"], f"Buildup {i} function mismatch"
        assert b1["coeff1"] == b2["coeff1"], f"Buildup {i} coeff1 mismatch"

    assert "washoff" in model1 and "washoff" in model2, "Missing washoff section"
    assert len(model1["washoff"]) == len(model2["washoff"]), "Washoff count mismatch"
    for i, w1 in enumerate(model1["washoff"]):
        w2 = model2["washoff"][i]
        assert w1["landuse"] == w2["landuse"], f"Washoff {i} landuse mismatch"
        assert w1["pollutant"] == w2["pollutant"], f"Washoff {i} pollutant mismatch"
        assert w1["function"] == w2["function"], f"Washoff {i} function mismatch"
        assert w1["coeff1"] == w2["coeff1"], f"Washoff {i} coeff1 mismatch"


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


def test_encoder_writes_pollutants(tmp_path):
    """Test writing POLLUTANTS section to INP file."""
    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    inp_data = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[POLLUTANTS]
;;Name           Units  
POL1             mg/L   
POL2             ug/L   
"""

    # Decode
    model = decoder.decode(StringIO(inp_data))

    # Encode
    output_file = tmp_path / "output.inp"
    encoder.encode_to_file(model, str(output_file))

    assert output_file.exists()

    # Verify POLLUTANTS section exists
    with open(output_file) as f:
        content = f.read()
        assert "[POLLUTANTS]" in content
        assert "POL1" in content


def test_encoder_writes_landuses(tmp_path):
    """Test writing LANDUSES section to INP file."""
    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    inp_data = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[LANDUSES]
;;Name           PercentImperv
LAND1            25
"""

    model = decoder.decode(StringIO(inp_data))
    output_file = tmp_path / "output.inp"
    encoder.encode_to_file(model, str(output_file))

    assert output_file.exists()
    with open(output_file) as f:
        content = f.read()
        assert "[LANDUSES]" in content
        assert "LAND1" in content


def test_encoder_writes_coverages(tmp_path):
    """Test writing COVERAGES section to INP file."""
    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    inp_data = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[COVERAGES]
;;Subcatchment   LandUse          Percent
S1               LAND1            100
"""

    model = decoder.decode(StringIO(inp_data))
    output_file = tmp_path / "output.inp"
    encoder.encode_to_file(model, str(output_file))

    assert output_file.exists()
    with open(output_file) as f:
        content = f.read()
        assert "[COVERAGES]" in content


def test_encoder_writes_buildup(tmp_path):
    """Test writing BUILDUP section to INP file."""
    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    inp_data = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[BUILDUP]
;;LandUse         Pollutant        Function   Coeff1   
LAND1            POL1             LINEAR     10       
"""

    model = decoder.decode(StringIO(inp_data))
    output_file = tmp_path / "output.inp"
    encoder.encode_to_file(model, str(output_file))

    assert output_file.exists()
    with open(output_file) as f:
        content = f.read()
        assert "[BUILDUP]" in content


def test_encoder_writes_washoff(tmp_path):
    """Test writing WASHOFF section to INP file."""
    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    inp_data = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[WASHOFF]
;;LandUse         Pollutant        Function   Coeff1   
LAND1            POL1             EMC        5        
"""

    model = decoder.decode(StringIO(inp_data))
    output_file = tmp_path / "output.inp"
    encoder.encode_to_file(model, str(output_file))

    assert output_file.exists()
    with open(output_file) as f:
        content = f.read()
        assert "[WASHOFF]" in content


def test_encoder_writes_lid_controls(tmp_path):
    """Test writing LID_CONTROLS section to INP file."""
    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    inp_data = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[LID_CONTROLS]
;;Name           Type/Layer Parameters
LID1             BC
"""

    model = decoder.decode(StringIO(inp_data))
    output_file = tmp_path / "output.inp"
    encoder.encode_to_file(model, str(output_file))

    assert output_file.exists()
    with open(output_file) as f:
        content = f.read()
        assert "[LID_CONTROLS]" in content


def test_encoder_writes_lid_usage(tmp_path):
    """Test writing LID_USAGE section to INP file."""
    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    inp_data = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[LID_USAGE]
;;Subcatchment   LID Process      Number   
S1               LID1             1        
"""

    model = decoder.decode(StringIO(inp_data))
    output_file = tmp_path / "output.inp"
    encoder.encode_to_file(model, str(output_file))

    assert output_file.exists()
    with open(output_file) as f:
        content = f.read()
        assert "[LID_USAGE]" in content


def test_encoder_writes_files(tmp_path):
    """Test writing FILES section to INP file."""
    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    inp_data = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[FILES]
;;Type            File Path
RAINFALL          /path/to/rain.dat
"""

    model = decoder.decode(StringIO(inp_data))
    output_file = tmp_path / "output.inp"
    encoder.encode_to_file(model, str(output_file))

    assert output_file.exists()
    with open(output_file) as f:
        content = f.read()
        assert "[FILES]" in content


def test_encoder_writes_hydrographs(tmp_path):
    """Test writing HYDROGRAPHS section to INP file."""
    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    inp_data = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[HYDROGRAPHS]
;;Name           Response      R1-R2          Values
UH1              R   0
"""

    model = decoder.decode(StringIO(inp_data))
    output_file = tmp_path / "output.inp"
    encoder.encode_to_file(model, str(output_file))

    assert output_file.exists()
    with open(output_file) as f:
        content = f.read()
        assert "[HYDROGRAPHS]" in content


def test_encoder_writes_rdii(tmp_path):
    """Test writing RDII section to INP file."""
    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    inp_data = """
[TITLE]
Test Model

[OPTIONS]
FLOW_UNITS    CFS

[RDII]
;;Node           UnitHydrograph  SewerArea   Factor
J1               UH1             0.5         1.0
"""

    model = decoder.decode(StringIO(inp_data))
    output_file = tmp_path / "output.inp"
    encoder.encode_to_file(model, str(output_file))

    assert output_file.exists()
    with open(output_file) as f:
        content = f.read()
        assert "[RDII]" in content


def test_roundtrip_real_example_file_with_quality():
    """Test round-trip with real example file containing quality sections."""
    from pathlib import Path
    import tempfile

    # Use example2.inp which has quality sections
    example_file = (
        Path(__file__).parent.parent / "examples" / "example2" / "example2.inp"
    )

    if not example_file.exists():
        pytest.skip(f"Example file not found: {example_file}")

    decoder = SwmmInputDecoder()
    encoder = SwmmInputEncoder()

    # Load real example file
    model1 = decoder.decode_file(str(example_file))

    # Check that it has quality sections
    has_quality_sections = any(
        key in model1
        for key in ["pollutants", "landuses", "coverages", "buildup", "washoff"]
    )

    if not has_quality_sections:
        pytest.skip("Example file doesn't have quality sections")

    # Encode to temporary file
    with tempfile.TemporaryDirectory() as tmp:
        temp_file = Path(tmp) / "roundtrip.inp"
        encoder.encode_to_file(model1, str(temp_file))

        # Decode again
        model2 = decoder.decode_file(str(temp_file))

        # Verify all sections are present
        for section in model1:
            assert section in model2, f"Section {section} missing after round-trip"

            # For list sections, verify counts match
            if isinstance(model1[section], list):
                assert len(model1[section]) == len(
                    model2[section]
                ), f"Section {section} count mismatch: {len(model1[section])} vs {len(model2[section])}"
