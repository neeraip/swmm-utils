"""
Tests for the producer-side helpers in swmm_utils.exports.

Mirrors the EPANET equivalent. Pure-.inp tests run unconditionally;
.rpt and .out tests skip when fixtures aren't present (consistent with
the existing test_out / test_rpt modules in this repo).
"""

from pathlib import Path

import pytest

from swmm_utils.exports import (
    LAYER_ROLE_MAP,
    NON_SPATIAL_SECTIONS,
    SPATIAL_SECTIONS,
    decode_to_data_json,
    emit_geojson_layers,
    emit_report_json,
    emit_results_parquet,
    encode_with_overlay,
)


REPO_ROOT = Path(__file__).parent.parent
INP_EXAMPLE1 = REPO_ROOT / "examples" / "example1" / "example1.inp"
RPT_EXAMPLE1 = REPO_ROOT / "examples" / "example1" / "example1.rpt"
OUT_EXAMPLE1 = REPO_ROOT / "examples" / "example1" / "example1.out"


@pytest.fixture
def example1_inp() -> Path:
    if not INP_EXAMPLE1.exists():
        pytest.skip(f"fixture missing: {INP_EXAMPLE1}")
    return INP_EXAMPLE1


# ---------------------------------------------------------------------------
# decode_to_data_json
# ---------------------------------------------------------------------------

def test_decode_to_data_json_only_non_spatial(example1_inp):
    data = decode_to_data_json(example1_inp)

    assert all(k in NON_SPATIAL_SECTIONS for k in data), \
        f"spatial leak: {set(data) - NON_SPATIAL_SECTIONS}"
    assert not (set(data) & SPATIAL_SECTIONS), \
        f"spatial section in data.json: {set(data) & SPATIAL_SECTIONS}"
    assert len(data) > 0


def test_decode_to_data_json_serializable(example1_inp):
    import json
    data = decode_to_data_json(example1_inp)
    text = json.dumps(data, default=str)
    assert isinstance(text, str)
    assert len(text) > 0


# ---------------------------------------------------------------------------
# encode_with_overlay
# ---------------------------------------------------------------------------

def test_encode_with_overlay_passthrough_renders_inp(example1_inp):
    """No edits in overlay → output still parses as a valid .inp shape."""
    data = decode_to_data_json(example1_inp)
    rendered = encode_with_overlay(example1_inp, data)
    assert isinstance(rendered, str)
    # Spatial sections from source should still be present.
    assert "[JUNCTIONS]" in rendered
    assert "[CONDUITS]" in rendered or "[OPTIONS]" in rendered


def test_encode_with_overlay_ignores_spatial_keys(example1_inp):
    """A caller cannot smuggle spatial edits through the overlay."""
    data = decode_to_data_json(example1_inp)
    sentinel = "JUNCTION-NEVER-RENDERED"
    data["junctions"] = [{"id": sentinel, "invert_elev": 0}]  # type: ignore[index]
    rendered = encode_with_overlay(example1_inp, data)
    assert sentinel not in rendered, \
        "spatial section in overlay leaked into rendered .inp"


def test_encode_with_overlay_applies_non_spatial_edit(example1_inp):
    """Mutate a TITLE and expect it to appear in the rendered .inp."""
    data = decode_to_data_json(example1_inp)
    data["title"] = "Edited via overlay — sentinel-92834"
    rendered = encode_with_overlay(example1_inp, data)
    assert "sentinel-92834" in rendered


# ---------------------------------------------------------------------------
# emit_report_json
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not RPT_EXAMPLE1.exists(), reason="example1.rpt not found")
def test_emit_report_json_shape():
    r = emit_report_json(RPT_EXAMPLE1)

    expected_top_keys = {
        "header", "element_count", "analysis_options", "continuity",
        "subcatchment_runoff", "node_depth", "node_inflow", "link_flow",
        "metrics",
    }
    assert expected_top_keys.issubset(r.keys())

    metrics = r["metrics"]
    assert "node" in metrics and "link" in metrics and "subcatchment" in metrics


@pytest.mark.skipif(
    not (RPT_EXAMPLE1.exists() and OUT_EXAMPLE1.exists()),
    reason="example1.rpt or example1.out not found",
)
def test_emit_report_json_with_per_feature_summary():
    r = emit_report_json(RPT_EXAMPLE1, OUT_EXAMPLE1)
    assert "per_feature_summary" in r
    pfs = r["per_feature_summary"]
    assert {"nodes", "links", "subcatchments"} <= pfs.keys()


# ---------------------------------------------------------------------------
# emit_results_zarr
# ---------------------------------------------------------------------------

def _has_xarray_zarr() -> bool:
    try:
        import xarray  # noqa: F401
        import zarr  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not OUT_EXAMPLE1.exists(), reason="example1.out not found")
@pytest.mark.skipif(not _has_xarray_zarr(), reason="xarray + zarr not installed")
def test_emit_results_zarr_writes_and_reopens(tmp_path):
    from swmm_utils.exports import emit_results_zarr
    import xarray as xr

    store = tmp_path / "results.zarr"
    desc = emit_results_zarr(OUT_EXAMPLE1, INP_EXAMPLE1, str(store), chunk_features=200)

    assert desc["n_periods"] >= 1
    assert "node_metrics" in desc
    assert "link_metrics" in desc
    assert "sub_metrics" in desc

    ds = xr.open_zarr(str(store), consolidated=True)
    # At least one of the three roles must be present.
    assert any(name in ds.data_vars for name in ("nodes", "links", "subcatchments"))


# ---------------------------------------------------------------------------
# emit_results_parquet
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not OUT_EXAMPLE1.exists(), reason="example1.out not found")
def test_emit_results_parquet_shape_and_types(tmp_path):
    import pyarrow.parquet as pq

    pq_path = tmp_path / "results.parquet"
    desc = emit_results_parquet(OUT_EXAMPLE1, INP_EXAMPLE1, str(pq_path))

    expected_head = ["fid", "role", "element_type", "period_idx", "period_ts", "period_seconds"]
    assert desc["columns"][:6] == expected_head

    table = pq.read_table(str(pq_path))
    assert table.num_rows > 0

    t_schema = {f.name: str(f.type) for f in table.schema}
    assert t_schema["fid"] == "string"
    assert t_schema["role"] == "string"
    assert t_schema["element_type"] == "string"
    assert t_schema["period_idx"] == "int32"
    assert t_schema["period_seconds"] == "int32"
    assert t_schema["period_ts"].startswith("timestamp")
    # All SWMM metric columns must be float32.
    for m in (
        "depth", "head", "flow_rate", "flow_velocity", "rainfall", "runoff",
    ):
        assert t_schema[m] == "float"


@pytest.mark.skipif(not OUT_EXAMPLE1.exists(), reason="example1.out not found")
def test_emit_results_parquet_null_across_roles(tmp_path):
    import pyarrow.parquet as pq

    pq_path = tmp_path / "results.parquet"
    emit_results_parquet(OUT_EXAMPLE1, INP_EXAMPLE1, str(pq_path))

    df = pq.read_table(str(pq_path)).to_pandas()

    # Node rows: link & subcatchment metrics must be NaN.
    node_rows = df[df["role"] == "node"]
    if len(node_rows) > 0:
        row = node_rows.iloc[0]
        assert all(str(row[c]) == "nan" for c in ("flow_rate", "flow_velocity"))
        assert all(str(row[c]) == "nan" for c in ("rainfall", "runoff"))

    # Link rows: node & subcatchment metrics must be NaN.
    link_rows = df[df["role"] == "link"]
    if len(link_rows) > 0:
        row = link_rows.iloc[0]
        assert all(str(row[c]) == "nan" for c in ("depth", "head", "volume"))
        assert all(str(row[c]) == "nan" for c in ("rainfall", "runoff"))

    # Subcatchment rows: node & link metrics must be NaN.
    sub_rows = df[df["role"] == "subcatchment"]
    if len(sub_rows) > 0:
        row = sub_rows.iloc[0]
        assert all(str(row[c]) == "nan" for c in ("depth", "head", "volume"))
        assert all(str(row[c]) == "nan" for c in ("flow_rate", "flow_velocity"))


@pytest.mark.skipif(not OUT_EXAMPLE1.exists(), reason="example1.out not found")
def test_emit_results_parquet_compression(tmp_path):
    """Writer settings must match file-ingestion-engine (zstd, row groups)."""
    import pyarrow.parquet as pq

    pq_path = tmp_path / "results.parquet"
    emit_results_parquet(OUT_EXAMPLE1, INP_EXAMPLE1, str(pq_path))

    md = pq.read_metadata(str(pq_path))
    rg = md.row_group(0)
    for i in range(rg.num_columns):
        assert rg.column(i).compression == "ZSTD"


# ---------------------------------------------------------------------------
# emit_geojson_layers
# ---------------------------------------------------------------------------

def test_emit_geojson_layers_shape(example1_inp):
    """Each layer spec has the documented shape and nonzero feature counts."""
    layers = emit_geojson_layers(example1_inp, crs="EPSG:4326")
    assert len(layers) > 0

    for spec in layers:
        # Required keys
        assert set(spec.keys()) == {
            "name", "role", "geometry_type", "crs", "feature_collection",
        }
        # Roles always come from the canonical map.
        assert spec["role"] == LAYER_ROLE_MAP[spec["name"]]
        assert spec["crs"] == "EPSG:4326"
        # GeoJSON type and at least one feature.
        fc = spec["feature_collection"]
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) > 0
        f0 = fc["features"][0]
        assert f0["type"] == "Feature"
        assert "id" in f0 and "properties" in f0 and "geometry" in f0
        # Geometry type matches the declared layer geometry.
        assert f0["geometry"]["type"] == spec["geometry_type"]


def test_emit_geojson_layers_node_link_subcatchment_balance(example1_inp):
    """Example1 has all three role classes — confirm at least one of each."""
    layers = emit_geojson_layers(example1_inp)
    by_role = {s["role"]: s for s in layers}
    # Junctions and conduits exist in any non-trivial SWMM model.
    assert "junction" in by_role
    assert "conduit" in by_role
    # Subcatchments are surfaced even when [POLYGONS] is empty (synth
    # square at outlet); example1 has subcatchments.
    if "subcatchment" in by_role:
        sub = by_role["subcatchment"]["feature_collection"]["features"]
        assert all(f["geometry"]["type"] == "Polygon" for f in sub)


# ---------------------------------------------------------------------------
# New section handlers + cross-references
# ---------------------------------------------------------------------------

SYNTHETIC_INP_WITH_NEW_SECTIONS = """[TITLE]
test
[OPTIONS]
INFILTRATION HORTON
[JUNCTIONS]
J1 100 10 0 0 0
J2 95 8 0 0 0
[OUTFALLS]
O1 90 FREE
[CONDUITS]
C1 J1 J2 100 0.013 0 0 0
C2 J2 O1 50 0.013 0 0 0
[XSECTIONS]
C1 CIRCULAR 1 0 0 0
C2 CIRCULAR 1 0 0 0
[SUBCATCHMENTS]
S1 RG1 J1 5 50 100 1 0
[SUBAREAS]
S1 0.01 0.1 0.05 0.05 25 OUTLET
[INFILTRATION]
S1 3 0.5 4 7 0
[TREATMENT]
J2 TSS R = 0.5*R_TSS
J2 BOD R = 0.7*R_BOD
[GROUNDWATER]
S1 AQ1 J1 100 0.001 1.5 0.0 0.0 0.0 0 * 90 0.5 0.3
[STREETS]
ST1 0.05 0.5 0.02 0.016 2.0 1.0 2
[INLETS]
INLET1 GRATE 2.0 0.5 P_30
[INLET_USAGE]
C1 INLET1 J2 1 5 0 0 0 ON_GRADE
[CONTROLS]
RULE R1
IF NODE J1 DEPTH > 5
THEN LINK C1 STATUS = CLOSED
[RAINGAGES]
RG1 INTENSITY 0:05 1.0 TIMESERIES TS1
[COORDINATES]
J1 0 0
J2 100 0
O1 150 0
[POLYGONS]
S1 -10 -10
S1 10 -10
S1 10 10
S1 -10 10
"""


@pytest.fixture
def synth_inp_path(tmp_path) -> Path:
    p = tmp_path / "synth.inp"
    p.write_text(SYNTHETIC_INP_WITH_NEW_SECTIONS)
    return p


def test_new_section_decoders(synth_inp_path):
    """Newly-added sections decode into structured shapes."""
    from swmm_utils.inp_decoder import SwmmInputDecoder

    m = SwmmInputDecoder().decode_file(str(synth_inp_path))

    # [TREATMENT] — list of {node, pollutant, function}
    assert m["treatment"] == [
        {"node": "J2", "pollutant": "TSS", "function": "R = 0.5*R_TSS"},
        {"node": "J2", "pollutant": "BOD", "function": "R = 0.7*R_BOD"},
    ]
    # [GROUNDWATER] — list of {subcatchment, aquifer, node, surface_elev, a1..umc}
    assert len(m["groundwater"]) == 1
    gw = m["groundwater"][0]
    assert gw["subcatchment"] == "S1"
    assert gw["aquifer"] == "AQ1"
    assert gw["a1"] == "0.001"
    assert gw["umc"] == "0.3"
    # [STREETS] — dict[name -> params]
    assert "ST1" in m["streets"]
    assert m["streets"]["ST1"]["sx"] == "0.02"
    # [INLETS] — dict[name -> list[{type, params}]]
    assert "INLET1" in m["inlets"]
    assert m["inlets"]["INLET1"][0]["type"] == "GRATE"
    # [INLET_USAGE] — list of {conduit, inlet, node, ...}
    assert m["inlet_usage"][0]["conduit"] == "C1"
    assert m["inlet_usage"][0]["pct_clogged"] == "5"


def test_new_section_round_trip(synth_inp_path):
    """decode → encode → decode preserves all new sections cleanly."""
    from swmm_utils.inp_decoder import SwmmInputDecoder
    from swmm_utils.inp_encoder import SwmmInputEncoder
    import io

    d = SwmmInputDecoder()
    e = SwmmInputEncoder()
    m1 = d.decode_file(str(synth_inp_path))
    buf = io.StringIO()
    e.encode_to_inp(m1, buf)
    m2 = d.decode(io.StringIO(buf.getvalue()))

    for key in ("treatment", "groundwater", "streets", "inlets", "inlet_usage"):
        assert m1.get(key) == m2.get(key), \
            f"{key} did not round-trip cleanly"


def test_emit_geojson_layers_authoring_field_coverage(synth_inp_path):
    """Layer enrichments cover the high-value authoring fields:
    rim_elev, slope, in_ctrl, treatment_*, gw_*, inlet_*, infil_model,
    rdii_* (when present), lid_names (when present)."""
    layers = emit_geojson_layers(synth_inp_path, crs="EPSG:4326")
    by_role = {s["role"]: s for s in layers}

    # Junction J2 — has [TREATMENT] rows, in [CONTROLS] but not directly
    # by name (only J1 is referenced), invert + max_depth set so rim_elev.
    j_feats = by_role["junction"]["feature_collection"]["features"]
    j2 = next(f for f in j_feats if f["id"] == "J2")
    j2p = j2["properties"]
    assert j2p["rim_elev"] == 103.0
    assert j2p["treatment_count"] == 2
    assert j2p["treatment_pollutant"] == "TSS"
    # J1 is in_ctrl=True; J2 is not.
    j1 = next(f for f in j_feats if f["id"] == "J1")
    assert j1["properties"]["in_ctrl"] is True
    assert j2p["in_ctrl"] is False

    # Conduit C1 — slope computed, in_ctrl=True (referenced by RULE R1),
    # inlet_usage row binds inlet_name + inlet_pct_clogged.
    c_feats = by_role["conduit"]["feature_collection"]["features"]
    c1 = next(f for f in c_feats if f["id"] == "C1")
    c1p = c1["properties"]
    assert c1p["slope"] == pytest.approx(0.05)
    assert c1p["in_ctrl"] is True
    assert c1p["inlet_name"] == "INLET1"
    assert c1p["inlet_pct_clogged"] == 5.0

    # Subcatchment S1 — gw_* keys present, infil_model from OPTIONS.
    s_feats = by_role["subcatchment"]["feature_collection"]["features"]
    s1p = s_feats[0]["properties"]
    assert s1p["infil_model"] == "HORTON"
    assert s1p["gw_aquifer"] == "AQ1"
    assert s1p["gw_node"] == "J1"
    assert s1p["gw_surface_elev"] == "100"
    assert s1p["gw_a1"] == "0.001"
