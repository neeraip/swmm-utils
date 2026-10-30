"""
SWMM 5.2 columns that 1.6 kept only as unnamed tokens, or lost:

- a subcatchment's own infiltration method, the last column of its
  [INFILTRATION] row, was under ``extra``;
- [ADJUSTMENTS]' per-subcatchment ``N-PERV`` / ``DSTORE`` / ``INFIL``
  rows were keyed by their first word, so all but the last of each type
  were lost;
- a storage unit's surcharge depth, evaporation factor and seepage were
  in ``curve_params`` with the shape's own values;
- a weir's coefficient curve (13th column) was under ``extra``.
"""
import io
from pathlib import Path

import pytest

from swmm_utils import SwmmInputDecoder, SwmmInputEncoder

EXAMPLES = Path(__file__).parent.parent / "examples"

INP = """[OPTIONS]
FLOW_UNITS           CFS
INFILTRATION         HORTON

[SUBCATCHMENTS]
S1  RG1  J1  10  50  500  1.0  0
S2  RG1  J1  10  50  500  1.0  0
S3  RG1  J1  10  50  500  1.0  0
S4  RG1  J1  10  50  500  1.0  0

[INFILTRATION]
;;Subcatchment   Param1     Param2     Param3     Param4     Param5     Method
S1               3.0        0.5        4          7          0
S2               3.5        0.5        0.25       0          0          GREEN_AMPT
S3               75         0.5        7          CURVE_NUMBER
S4               3.0        0.5        4          7          0          MODIFIED_HORTON

[ADJUSTMENTS]
TEMPERATURE  1 2 3 4 5 6 7 8 9 10 11 12
EVAPORATION  0 0 0 0 0 0 0 0 0 0 0 0
N-PERV       S1   NP1
N-PERV       S2   NP2
DSTORE       S1   DS1
INFIL        S3   IN1
INFIL        S4   IN2

[JUNCTIONS]
J1  100  4  0  0  0
J2  99   4  0  0  0

[STORAGE]
;;Name  Elev  MaxDepth  InitDepth  Shape  Params  SurDepth  Fevap  Psi  Ksat  IMD
ST1     90    10        0          TABULAR      SC1        2    0.5  3.5  0.2  0.3
ST2     90    10        0          FUNCTIONAL   1000 0 0   0    0
ST3     90    10        0          PYRAMIDAL    20 30 2    1.5
ST4     90    10        0          CONICAL      20 30 2    0    0    0.4
ST5     90    10        0          CYLINDRICAL  20 30 0
ST6     90    10        0          TABULAR      SC1

[WEIRS]
W1  J1  J2  TRANSVERSE  1  3.33  NO  0  0  YES
W2  J1  J2  ROADWAY     1  3.33  NO  0  0  YES  40  PAVED
W3  J1  J2  TRANSVERSE  1  3.33  NO  0  0  YES  *   *      WC1

[CURVES]
SC1  STORAGE  0  1000
SC1           10 1000
WC1  WEIR     0  3.33
WC1           2  3.0
"""


def _decode(text):
    return SwmmInputDecoder().decode(io.StringIO(text))


def _encode(model):
    buf = io.StringIO()
    SwmmInputEncoder().encode_to_inp(model, buf)
    return buf.getvalue()


def _rows(text):
    """Each section's data rows as token lists, keyed by section."""
    rows, section = {}, None
    for line in text.splitlines():
        if line.startswith("["):
            section = line.strip("[]")
            rows[section] = []
        elif line.strip() and not line.startswith(";"):
            rows[section].append(line.split())
    return rows


def test_infiltration_method_is_its_own_field():
    model = _decode(INP)
    s1, s2, s3, s4 = model["infiltrations"]
    assert "method" not in s1 and "extra" not in s1
    assert (s2["method"], s2["param3"], s2["param5"]) == ("GREEN_AMPT", "0.25", "0")
    assert "extra" not in s2
    assert s3 == {
        "subcatchment": "S3", "param1": "75", "param2": "0.5", "param3": "7",
        "method": "CURVE_NUMBER",
    }
    assert s4["method"] == "MODIFIED_HORTON"


def test_infiltration_method_is_written_in_the_last_column():
    out = _rows(_encode(_decode(INP)))["INFILTRATION"]
    assert out[0] == ["S1", "3.0", "0.5", "4", "7", "0"]
    assert out[1] == ["S2", "3.5", "0.5", "0.25", "0", "0", "GREEN_AMPT"]
    assert out[2] == ["S3", "75", "0.5", "7", "CURVE_NUMBER"]
    assert out[3][-1] == "MODIFIED_HORTON"


def test_infiltration_row_decoded_by_1_6_still_writes_its_method():
    model = {"infiltrations": [{
        "subcatchment": "S2", "param1": "3.5", "param2": "0.5", "param3": "0.25",
        "param4": "0", "param5": "0", "extra": ["GREEN_AMPT"],
    }]}
    out = _rows(_encode(model))["INFILTRATION"]
    assert out == [["S2", "3.5", "0.5", "0.25", "0", "0", "GREEN_AMPT"]]
    assert _decode(_encode(model))["infiltrations"][0]["method"] == "GREEN_AMPT"


def test_adjustments_keep_every_subcatchment_pattern():
    adj = _decode(INP)["adjustments"]
    assert adj["temperature"] == "1 2 3 4 5 6 7 8 9 10 11 12"
    assert adj["evaporation"] == "0 0 0 0 0 0 0 0 0 0 0 0"
    assert adj["subcatchment_patterns"] == [
        {"type": "N-PERV", "subcatchment": "S1", "pattern": "NP1"},
        {"type": "N-PERV", "subcatchment": "S2", "pattern": "NP2"},
        {"type": "DSTORE", "subcatchment": "S1", "pattern": "DS1"},
        {"type": "INFIL", "subcatchment": "S3", "pattern": "IN1"},
        {"type": "INFIL", "subcatchment": "S4", "pattern": "IN2"},
    ]
    assert "n-perv" not in adj and "infil" not in adj
    out = _rows(_encode(_decode(INP)))["ADJUSTMENTS"]
    assert out[0][0] == "TEMPERATURE" and out[1][0] == "EVAPORATION"
    assert out[2:] == [
        ["N-PERV", "S1", "NP1"], ["N-PERV", "S2", "NP2"], ["DSTORE", "S1", "DS1"],
        ["INFIL", "S3", "IN1"], ["INFIL", "S4", "IN2"],
    ]


def test_monthly_adjustments_alone_decode_as_before():
    adj = _decode("[ADJUSTMENTS]\nRAINFALL 1 1 1 1 1 1 1 1 1 1 1 1\n")["adjustments"]
    assert adj == {"rainfall": "1 1 1 1 1 1 1 1 1 1 1 1"}


def test_adjustments_decoded_by_1_6_still_render():
    out = _rows(_encode({"adjustments": {"temperature": "1 2 3", "n-perv": "S2 NP2"}}))
    assert out["ADJUSTMENTS"] == [["TEMPERATURE", "1", "2", "3"], ["N-PERV", "S2", "NP2"]]


def test_storage_tail_columns_are_named():
    st1, st2, st3, st4, st5, st6 = _decode(INP)["storage"]
    assert st1 == {
        "name": "ST1", "elevation": "90", "max_depth": "10", "init_depth": "0",
        "curve_type": "TABULAR", "curve_params": ["SC1"],
        "surcharge_depth": "2", "evap_factor": "0.5",
        "seepage_suction": "3.5", "seepage_ksat": "0.2", "seepage_imd": "0.3",
    }
    assert (st2["curve_params"], st2["surcharge_depth"], st2["evap_factor"]) == (
        ["1000", "0", "0"], "0", "0")
    assert "seepage_ksat" not in st2
    assert st3["curve_params"] == ["20", "30", "2"] and st3["surcharge_depth"] == "1.5"
    assert "evap_factor" not in st3
    # One value after Fevap is Ksat alone, as the engine reads it.
    assert st4["seepage_ksat"] == "0.4" and "seepage_suction" not in st4
    assert st5["curve_params"] == ["20", "30", "0"] and "surcharge_depth" not in st5
    assert st6["curve_params"] == ["SC1"] and "surcharge_depth" not in st6


def test_storage_rows_are_written_back_as_read():
    src = _rows(INP)["STORAGE"]
    out = _rows(_encode(_decode(INP)))["STORAGE"]
    assert out == src


def test_storage_blank_before_a_filled_column_is_written_as_zero():
    model = {"storage": [
        {"name": "A", "elevation": "0", "max_depth": "5", "init_depth": "0",
         "curve_type": "TABULAR", "curve_params": ["C"], "evap_factor": "0.5"},
        {"name": "B", "elevation": "0", "max_depth": "5", "init_depth": "0",
         "curve_type": "TABULAR", "curve_params": ["C"], "seepage_ksat": "0.2",
         "seepage_imd": "0.3"},
    ]}
    out = _rows(_encode(model))["STORAGE"]
    assert out[0][5:] == ["C", "0", "0.5"]
    assert out[1][5:] == ["C", "0", "0", "0", "0.2", "0.3"]


def test_storage_row_decoded_by_1_6_still_renders():
    old = {"storage": [{
        "name": "ST1", "elevation": "90", "max_depth": "10", "init_depth": "0",
        "curve_type": "TABULAR", "curve_params": ["SC1", "2", "0.5", "3.5", "0.2", "0.3"],
    }]}
    out = _rows(_encode(old))["STORAGE"]
    assert out == [["ST1", "90", "10", "0", "TABULAR", "SC1", "2", "0.5", "3.5", "0.2", "0.3"]]


def test_storage_shape_the_decoder_does_not_know_keeps_every_column():
    st = _decode("[STORAGE]\nX 0 5 0 NEWSHAPE 1 2 3 4 5\n")["storage"][0]
    assert st["curve_params"] == ["1", "2", "3", "4", "5"] and "surcharge_depth" not in st


@pytest.mark.parametrize("shape", ["PARABOLIC", "PARABOLOID", "paraboloid"])
def test_paraboloid_storage_tail_is_named_and_written_back_as_read(shape):
    # The engine reads PARABOLIC (text.h); the 5.2 manual writes PARABOLOID.
    row = f"ST7 90 10 0 {shape} 20 30 4 1.5 0.8 3.5 0.2 0.3"
    st = _decode(f"[STORAGE]\n{row}\n")["storage"][0]
    assert st["curve_type"] == shape
    assert st["curve_params"] == ["20", "30", "4"]
    assert (st["surcharge_depth"], st["evap_factor"]) == ("1.5", "0.8")
    assert (st["seepage_suction"], st["seepage_ksat"], st["seepage_imd"]) == (
        "3.5", "0.2", "0.3")
    assert _rows(_encode({"storage": [st]}))["STORAGE"] == [row.split()]


def test_weir_coefficient_curve_is_its_own_field():
    w1, w2, w3 = _decode(INP)["weirs"]
    assert "coeff_curve" not in w1 and "extra" not in w2
    assert (w3["road_width"], w3["road_surf"], w3["coeff_curve"]) == ("*", "*", "WC1")
    assert "extra" not in w3
    assert _rows(_encode(_decode(INP)))["WEIRS"][2][-3:] == ["*", "*", "WC1"]


def test_weir_curve_without_road_columns_gets_placeholders():
    base = {"from_node": "J1", "to_node": "J2", "crest_height": "1",
            "discharge_coeff": "3.33", "coeff_curve": "WC1"}
    model = {"weirs": [{"name": "T", "type": "TRANSVERSE", **base},
                       {"name": "R", "type": "ROADWAY", **base}]}
    out = _rows(_encode(model))["WEIRS"]
    assert out[0][10:] == ["*", "*", "WC1"]
    # A ROADWAY weir reads its road width as a number.
    assert out[1][10:] == ["0", "*", "WC1"]


def test_decode_encode_decode_is_stable():
    first = _decode(INP)
    text = _encode(first)
    assert _decode(text) == first
    assert _encode(_decode(text)) == text


def test_swmm_5_1_storage_rows_are_unchanged():
    """example1 is a 5.1 file: its column after the shape is the ponded area."""
    path = EXAMPLES / "example1" / "example1.inp"
    model = SwmmInputDecoder().decode_file(str(path))
    st = model["storage"][0]
    assert (st["curve_params"], st["surcharge_depth"], st["evap_factor"]) == (
        ["100", "0", "0"], "0", "0")
    src = _rows(path.read_text())["STORAGE"]
    assert _rows(_encode(model))["STORAGE"] == src
    assert _decode(_encode(model)) == _decode(_encode(_decode(_encode(model))))


def test_rows_without_the_new_columns_are_written_as_before():
    path = EXAMPLES / "example2" / "example2.inp"
    model = SwmmInputDecoder().decode_file(str(path))
    assert all("method" not in row for row in model["infiltrations"])
    src = _rows(path.read_text())["INFILTRATION"]
    assert _rows(_encode(model))["INFILTRATION"] == src
