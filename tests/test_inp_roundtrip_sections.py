"""
Sections the SWMM 5.2 engine rejected or silently lost after a decode →
encode round trip (found by running the re-encoded corpus through the
engine): AQUIFERS lost its last column, BUILDUP its per-unit flag,
HYDROGRAPHS ran padded numbers together, and EVENTS / GWF / LOADINGS
had no handler at all.
"""
from swmm_utils import SwmmInput
from swmm_utils.exports import NON_SPATIAL_SECTIONS

INP = """[TITLE]
round trip

[OPTIONS]
FLOW_UNITS CFS

[EVENTS]
;;Start Date  Start Time  End Date  End Time
06/30/2016  00:00  06/30/2016  12:00

[AQUIFERS]
;;Name  Por  WP  FC  Ks  Kslp  Tslp  ETu  ETs  Seep  Ebot  Egw  Umc  Epat
AQ1   0.5  0.15  0.30  0.1  12  15.0  0.35  14.0  0.002  0.0  3.5  0.40
AQ2   0.5  0.15  0.30  0.1  12  15.0  0.35  14.0  0.002  0.0  3.5  0.40  EVAP_PAT

[GWF]
CA-1  DEEP  Ksat*Hgw/Hsw
CA-2  LATERAL  0.001 * (Hgw - Hcb)

[BUILDUP]
A  SF1  POW  0.000000  1.000000  1.000000  AREA
B  SF1  EXP  1.5  0.2  0  CURB

[LOADINGS]
100  SF1  40.000000  SF2  2.5

[POLLUTANTS]
TSS  MG/L  10.000000  0.000000  0.000000  0.000000  NO  *  0.000000  10.000000  0.000000
TP   MG/L  1  0  0  0  NO

[OUTLETS]
HIGHFLOW  80608A  82309A  0.000000  FUNCTIONAL/DEPTH  10.000000  0.500000  YES
TAB1      80608A  82309A  0.000000  TABULAR/HEAD      RATING1  NO

[INFLOWS]
0    FLOW  1
N2   FLOW  TS2  FLOW  1.0  1.0  0  P1

[LID_USAGE]
S1  RAINBARRELS  32  6193.687500  12.000000  0.000000  17.000000  1  *
S2  BIOCELL      1   100  10  0  50  0  *  S3  0

[HYDROGRAPHS]
HYDRO1  GAGE1
RDII_Pattern_197  GAGE1
RDII_Pattern_197  All  Short  0.1  1.5  2.5  0  0  0
HYDRO1  All  Short  .1  1.000000  1.000000  0.000000  0.000000  0.000000
HYDRO1  All  Medium  .1  2  2  0.000000  0.000000  0.000000
"""


def _sections(text):
    out, cur = {}, None
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("["):
            cur = s.strip("[]"); out[cur] = []
        elif cur and s and not s.startswith(";"):
            out[cur].append(s.split())
    return out


def _roundtrip(tmp_path):
    src = tmp_path / "in.inp"; src.write_text(INP)
    model = SwmmInput(src)
    dst = tmp_path / "out.inp"; model.to_inp(dst)
    return model.to_dict(), _sections(dst.read_text())


def test_aquifer_keeps_all_twelve_numbers_and_the_pattern(tmp_path):
    model, out = _roundtrip(tmp_path)
    aq1, aq2 = model["aquifers"]
    assert aq1["umc"] == "0.40" and aq1["egw"] == "3.5" and "epat" not in aq1
    assert aq2["epat"] == "EVAP_PAT"
    assert out["AQUIFERS"][0] == ["AQ1", "0.5", "0.15", "0.30", "0.1", "12", "15.0", "0.35", "14.0", "0.002", "0.0", "3.5", "0.40"]
    assert out["AQUIFERS"][1][-1] == "EVAP_PAT" and len(out["AQUIFERS"][1]) == 14


def test_aquifer_rows_decoded_by_older_versions_still_render(tmp_path):
    from swmm_utils.inp_encoder import SwmmInputEncoder
    legacy = {"aquifers": [{"name": "AQ", "por": "0.5", "wp": "0.15", "fc": "0.3", "hydcon": "0.1", "condslp": "12",
                            "tension": "15", "upevap": "0.35", "losrate": "14", "gw_height": "0.002", "water_table": "0",
                            "upm_field": "3.5"}]}
    text = SwmmInputEncoder().encode_to_inp_string(legacy) if hasattr(SwmmInputEncoder, "encode_to_inp_string") else None
    if text is None:
        p = tmp_path / "legacy.inp"; SwmmInputEncoder().encode_to_inp_file(legacy, str(p)); text = p.read_text()
    row = _sections(text)["AQUIFERS"][0]
    assert row == ["AQ", "0.5", "0.15", "0.3", "0.1", "12", "15", "0.35", "14", "0.002", "0", "3.5", "0"]


def test_buildup_keeps_the_per_unit_flag(tmp_path):
    model, out = _roundtrip(tmp_path)
    assert [b["per_unit"] for b in model["buildup"]] == ["AREA", "CURB"]
    assert out["BUILDUP"][0] == ["A", "SF1", "POW", "0.000000", "1.000000", "1.000000", "AREA"]
    assert out["BUILDUP"][1][-1] == "CURB"


def test_buildup_without_the_flag_defaults_to_area(tmp_path):
    src = tmp_path / "b.inp"; src.write_text("[BUILDUP]\nA  SF1  POW  0  1  1\n")
    dst = tmp_path / "b_out.inp"; SwmmInput(src).to_inp(dst)
    assert _sections(dst.read_text())["BUILDUP"][0][-1] == "AREA"


def test_hydrograph_values_stay_separate_tokens(tmp_path):
    _, out = _roundtrip(tmp_path)
    rows = out["HYDROGRAPHS"]
    assert rows[0] == ["HYDRO1", "GAGE1"]
    assert rows[1] == ["HYDRO1", "All", "Short", ".1", "1.000000", "1.000000", "0.000000", "0.000000", "0.000000"]
    assert rows[2] == ["HYDRO1", "All", "Medium", ".1", "2", "2", "0.000000", "0.000000", "0.000000"]
    # a name that fills the 16-wide column keeps a separator before the gage
    assert rows[3] == ["RDII_Pattern_197", "GAGE1"]
    assert rows[4][:3] == ["RDII_Pattern_197", "All", "Short"]


def test_events_gwf_and_loadings_survive(tmp_path):
    model, out = _roundtrip(tmp_path)
    assert model["events"] == [{"start": "06/30/2016 00:00", "end": "06/30/2016 12:00"}]
    assert out["EVENTS"] == [["06/30/2016", "00:00", "06/30/2016", "12:00"]]
    assert model["gwf"] == [{"subcatchment": "CA-1", "type": "DEEP", "expression": "Ksat*Hgw/Hsw"},
                            {"subcatchment": "CA-2", "type": "LATERAL", "expression": "0.001 * (Hgw - Hcb)"}]
    assert out["GWF"][1] == ["CA-2", "LATERAL", "0.001", "*", "(Hgw", "-", "Hcb)"]
    assert model["loadings"] == [{"subcatchment": "100", "pollutant": "SF1", "buildup": "40.000000"},
                                 {"subcatchment": "100", "pollutant": "SF2", "buildup": "2.5"}]
    assert out["LOADINGS"] == [["100", "SF1", "40.000000"], ["100", "SF2", "2.5"]]


def test_data_json_carries_the_sections_the_render_needs():
    for section in ("events", "gwf", "loadings", "adjustments", "streets", "inlets", "inlet_usage", "profiles"):
        assert section in NON_SPATIAL_SECTIONS, section


def test_pollutant_keeps_the_dwf_and_initial_concentrations(tmp_path):
    model, out = _roundtrip(tmp_path)
    tss = model["pollutants"][0]
    assert (tss["co_pollutant"], tss["co_fraction"], tss["cdwf"], tss["cinit"]) == ("*", "0.000000", "10.000000", "0.000000")
    assert out["POLLUTANTS"][0] == ["TSS", "MG/L", "10.000000", "0.000000", "0.000000", "0.000000", "NO", "*", "0.000000", "10.000000", "0.000000"]
    # a seven-column row writes back whole with the engine's defaults
    assert out["POLLUTANTS"][1] == ["TP", "MG/L", "1", "0", "0", "0", "NO", "*", "0.0", "0.0", "0.0"]


def test_outlet_keeps_its_gate_flag_for_both_shapes(tmp_path):
    model, out = _roundtrip(tmp_path)
    fun, tab = model["outlets"]
    assert (fun["qcoeff"], fun["qexpon"], fun["gated"]) == ("10.000000", "0.500000", "YES")
    assert (tab["curve_name"], tab["gated"]) == ("RATING1", "NO")
    assert out["OUTLETS"][0] == ["HIGHFLOW", "80608A", "82309A", "0.000000", "FUNCTIONAL/DEPTH", "10.000000", "0.500000", "YES"]
    assert out["OUTLETS"][1] == ["TAB1", "80608A", "82309A", "0.000000", "TABULAR/HEAD", "RATING1", "NO"]


def test_outlet_rows_decoded_by_older_versions_still_render(tmp_path):
    from swmm_utils.inp_encoder import SwmmInputEncoder
    legacy = {"outlets": [{"name": "F", "from_node": "A", "to_node": "B", "offset": "0", "type": "FUNCTIONAL/DEPTH",
                           "curve_name": "10.0", "gated": "0.5"}]}
    p = tmp_path / "legacy.inp"; SwmmInputEncoder().encode_to_inp_file(legacy, str(p))
    assert _sections(p.read_text())["OUTLETS"][0] == ["F", "A", "B", "0", "FUNCTIONAL/DEPTH", "10.0", "0.5", "NO"]


def test_inflow_of_three_columns_is_kept(tmp_path):
    model, out = _roundtrip(tmp_path)
    assert model["inflows"][0] == {"node": "0", "constituent": "FLOW", "timeseries": "1"}
    assert out["INFLOWS"][0][:3] == ["0", "FLOW", "1"]
    assert out["INFLOWS"][1] == ["N2", "FLOW", "TS2", "FLOW", "1.0", "1.0", "0", "P1"]


def test_lid_usage_keeps_the_drain_to_columns(tmp_path):
    model, out = _roundtrip(tmp_path)
    assert model["lid_usage"][0]["rpt_file"] == "*" and "drain_to" not in model["lid_usage"][0]
    assert (model["lid_usage"][1]["drain_to"], model["lid_usage"][1]["from_pervious"]) == ("S3", "0")
    assert out["LID_USAGE"][0] == ["S1", "RAINBARRELS", "32", "6193.687500", "12.000000", "0.000000", "17.000000", "1", "*"]
    assert out["LID_USAGE"][1] == ["S2", "BIOCELL", "1", "100", "10", "0", "50", "0", "*", "S3", "0"]
