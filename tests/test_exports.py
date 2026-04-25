"""
Tests for the producer-side helpers in swmm_utils.exports.

Mirrors the EPANET equivalent. Pure-.inp tests run unconditionally;
.rpt and .out tests skip when fixtures aren't present (consistent with
the existing test_out / test_rpt modules in this repo).
"""

from pathlib import Path

import pytest

from swmm_utils.exports import (
    NON_SPATIAL_SECTIONS,
    SPATIAL_SECTIONS,
    decode_to_data_json,
    emit_report_json,
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
