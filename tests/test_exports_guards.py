"""
Two guards the Console smoke test asked for.

A node without coordinates used to take every link touching it out of the
import; and an overlay written at import kept rows for elements the network
no longer had, which the engine refused as undefined objects.
"""

from swmm_utils.exports import _drop_dangling_references, emit_geojson_layers, encode_with_overlay
from swmm_utils import SwmmInput

INP = """[TITLE]
guards

[OPTIONS]
FLOW_UNITS CFS

[JUNCTIONS]
J1 100 10 0 0 0
J2 95 8 0 0 0

[STORAGE]
ST1 90 5 0 FUNCTIONAL 100 0 0

[OUTFALLS]
O1 85 FREE

[CONDUITS]
C1 J1 J2 100 0.013 0 0 0
C2 J2 ST1 50 0.013 0 0 0
C3 ST1 O1 50 0.013 0 0 0

[XSECTIONS]
C1 CIRCULAR 1 0 0 0
C2 CIRCULAR 1 0 0 0
C3 CIRCULAR 1 0 0 0

[DWF]
J1 FLOW 1.5

[COORDINATES]
J1 0 0
J2 100 0
O1 300 0
"""


def _layers(path):
    return {s["role"]: s["feature_collection"]["features"] for s in emit_geojson_layers(path)}


def test_a_node_without_coordinates_is_still_imported(tmp_path):
    path = tmp_path / "g.inp"
    path.write_text(INP)
    by_role = _layers(path)
    storage = by_role["storage"]
    assert [f["id"] for f in storage] == ["ST1"]
    # Placed below the located nodes, not on top of one of them.
    x, y = storage[0]["geometry"]["coordinates"]
    assert y < 0 and 0 <= x <= 300
    # And the conduits touching it are kept, drawn to that place.
    conduits = {f["id"]: f for f in by_role["conduit"]}
    assert set(conduits) == {"C1", "C2", "C3"}
    assert conduits["C2"]["geometry"]["coordinates"][-1] == [x, y]
    assert conduits["C3"]["geometry"]["coordinates"][0] == [x, y]


def test_placement_without_any_coordinates_at_all(tmp_path):
    path = tmp_path / "g.inp"
    path.write_text(INP.split("[COORDINATES]")[0])
    by_role = _layers(path)
    assert len(by_role["junction"]) == 2 and len(by_role["conduit"]) == 3
    xs = sorted(f["geometry"]["coordinates"][0] for f in by_role["junction"] + by_role["storage"] + by_role["outfall"])
    assert len(set(xs)) == 4  # spaced out, not stacked


def test_overlay_drops_rows_for_elements_the_model_lacks(tmp_path):
    path = tmp_path / "g.inp"
    path.write_text(INP)
    overlay = {
        "xsections": [
            {"link": "C1", "shape": "CIRCULAR", "geom1": "2", "geom2": "0", "geom3": "0", "geom4": "0"},
            {"link": "GONE", "shape": "CIRCULAR", "geom1": "9", "geom2": "0", "geom3": "0", "geom4": "0"},
        ],
        "dwf": [{"node": "J1", "constituent": "FLOW", "baseline": "2.5"}, {"node": "NOWHERE", "constituent": "FLOW", "baseline": "1"}],
    }
    text = encode_with_overlay(path, overlay)
    xs = text.split("[XSECTIONS]")[1].split("[")[0]
    assert "GONE" not in xs and "C1" in xs and " 2 " in xs.replace("2.0", "2 ")
    dwf = text.split("[DWF]")[1].split("[")[0]
    assert "NOWHERE" not in dwf and "J1" in dwf


def test_drop_dangling_reports_what_it_removed(tmp_path):
    path = tmp_path / "g.inp"
    path.write_text(INP)
    with SwmmInput(path) as model:
        model["xsections"] = list(model["xsections"]) + [{"link": "GONE", "shape": "CIRCULAR", "geom1": "1"}]
        assert _drop_dangling_references(model) == {"xsections": 1}
        assert _drop_dangling_references(model) == {}
