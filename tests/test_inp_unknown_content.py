"""
What the decoder has no field for survives decode → encode as written:
sections it has no handler for (OpenSWMM's [2D_*]), [OPTIONS] keys SWMM 5
doesn't know, and columns after a row's last known one. Before 1.6 the
[2D_*] headers weren't even read as sections (a name can't start with a
digit), so their rows ran into the section above and were lost.
"""
from swmm_utils import SwmmInput, SwmmInputDecoder, SwmmInputEncoder
from swmm_utils.exports import encode_with_overlay

INP = """[TITLE]
2D round trip

[OPTIONS]
;;Option             Value
FLOW_UNITS           CMS
FLOW_ROUTING         DYNWAVE
NODE_CONTINUITY      SEMI_IMPLICIT
ANDERSON_ACCEL       YES
CRS                  EPSG:32616
FV_CFL               0.9
DPS_ALPHA            0.5

[RAINGAGES]
RG1   INTENSITY 0:05  1.0  TIMESERIES  RAIN

[SUBCATCHMENTS]
;;Name Gage Outlet Area %Imperv Width %Slope CurbLen SnowPack RainScale SnowScale
S1     RG1  J1     10   50      500   1.0    0       *        1.2       0.8

[JUNCTIONS]
J1     100  4  0  0  0
J2     99   4  0  0  0  EXTRA_J

[OUTFALLS]
O1     98   FREE     NO

[CONDUITS]
C1     J1   J2  400  0.013  0  0  0  0  NEW_COL
C2     J2   O1  400  0.013  0  0  0  0

[XSECTIONS]
C1     CIRCULAR  1.0  0 0 0 1
C2     CIRCULAR  1.0  0 0 0 1

[TIMESERIES]
RAIN 0:00 1.0

[2D_OPTIONS]
;;Parameter             Value      ;; Notes
MAX_TIMESTEP            10.0       ;; Max marcher step (s)
OUTPUT_FILE             model.2d.h5

[2D_VERTICES]
;;X                Y                  Z              TAG
0.0                0.0                101.0
10.0               0.0                100.5

10.0               10.0               100.0

[2D_VERTEX_NODE_MAP]
1  J1  0.65  2.0

[COORDINATES]
J1  0  0
J2  10 0
O1  20 0

[2D_MESH_FILE]
FILE  model.2dm
"""


def _decode(text):
    import io
    return SwmmInputDecoder().decode(io.StringIO(text))


def _encode(model):
    import io
    buf = io.StringIO()
    SwmmInputEncoder().encode_to_inp(model, buf)
    return buf.getvalue()


def test_2d_sections_are_kept_verbatim_in_order():
    model = _decode(INP)
    unknown = model["unknown_sections"]
    assert list(unknown) == ["2D_OPTIONS", "2D_VERTICES", "2D_VERTEX_NODE_MAP", "2D_MESH_FILE"]
    assert unknown["2D_OPTIONS"] == [
        ";;Parameter             Value      ;; Notes",
        "MAX_TIMESTEP            10.0       ;; Max marcher step (s)",
        "OUTPUT_FILE             model.2d.h5",
    ]
    # Blank lines inside a section stay; the ones around it don't.
    assert unknown["2D_VERTICES"][-2:] == ["", "10.0               10.0               100.0"]
    # The sections around them are read as before.
    assert [c["node"] for c in model["coordinates"]] == ["J1", "J2", "O1"]
    assert "symbols" not in model


def test_2d_sections_are_written_back_unchanged():
    text = _encode(_decode(INP))
    for name in ("2D_OPTIONS", "2D_VERTICES", "2D_VERTEX_NODE_MAP", "2D_MESH_FILE"):
        assert f"\n[{name}]\n" in text
    assert (
        "[2D_OPTIONS]\n"
        ";;Parameter             Value      ;; Notes\n"
        "MAX_TIMESTEP            10.0       ;; Max marcher step (s)\n"
        "OUTPUT_FILE             model.2d.h5\n"
    ) in text
    assert text.index("[2D_OPTIONS]") < text.index("[2D_VERTICES]") < text.index("[2D_MESH_FILE]")
    # A second pass changes nothing.
    assert _encode(_decode(text)) == text


def test_unknown_options_keep_their_values_and_order():
    model = _decode(INP)
    assert list(model["options"]) == [
        "FLOW_UNITS", "FLOW_ROUTING", "NODE_CONTINUITY", "ANDERSON_ACCEL",
        "CRS", "FV_CFL", "DPS_ALPHA",
    ]
    assert model["options"]["CRS"] == "EPSG:32616"
    text = _encode(model)
    assert "NODE_CONTINUITY      SEMI_IMPLICIT\n" in text
    assert "FV_CFL               0.9\n" in text


def test_option_without_a_value_is_kept():
    model = _decode("[OPTIONS]\nFLOW_UNITS CFS\nIGNORE_2D\n")
    assert model["options"] == {"FLOW_UNITS": "CFS", "IGNORE_2D": ""}
    assert "IGNORE_2D" in _encode(model)


def test_trailing_columns_survive_the_round_trip():
    model = _decode(INP)
    sub = model["subcatchments"][0]
    assert sub["snowpack"] == "*" and sub["extra"] == ["1.2", "0.8"]
    j1, j2 = model["junctions"]
    assert "extra" not in j1 and j2["extra"] == ["EXTRA_J"]
    c1, c2 = model["conduits"]
    assert c1["extra"] == ["NEW_COL"] and "extra" not in c2

    rows, section = {}, None
    for line in _encode(model).splitlines():
        if line.startswith("["):
            section = line
        elif line and not line.startswith(";"):
            rows[(section, line.split()[0])] = line.split()
    assert rows[("[SUBCATCHMENTS]", "S1")][-3:] == ["*", "1.2", "0.8"]
    assert rows[("[JUNCTIONS]", "J2")][-1] == "EXTRA_J"
    assert rows[("[CONDUITS]", "C1")][-2:] == ["0", "NEW_COL"]
    assert rows[("[CONDUITS]", "C2")][-1] == "0"


def test_run_input_rendered_with_an_overlay_keeps_the_2d_sections(tmp_path):
    src = tmp_path / "model.inp"
    src.write_text(INP)
    rendered = encode_with_overlay(src, {"title": "edited"})
    assert "edited" in rendered
    assert "[2D_MESH_FILE]\nFILE  model.2dm\n" in rendered
    assert "NODE_CONTINUITY      SEMI_IMPLICIT" in rendered


def test_swmm_input_writes_the_sections_back(tmp_path):
    src = tmp_path / "model.inp"
    src.write_text(INP)
    dst = tmp_path / "out.inp"
    with SwmmInput(src) as model:
        model.to_inp(dst)
    assert "[2D_VERTEX_NODE_MAP]\n1  J1  0.65  2.0\n" in dst.read_text()
