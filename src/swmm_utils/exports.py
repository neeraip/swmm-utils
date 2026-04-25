"""
Producer-side helpers used by NEER Console / WRM API to derive consumer-shaped
artifacts from SWMM .inp / .rpt / .out files.

Mirrors `epanet_utils.exports`. SWMM-specific differences:
- Subcatchments are a third role alongside nodes and links.
- Pollutants are dynamic — one metric per pollutant defined in the model.
- The SWMM 1D vs 2D distinction is a PCSWMM authoring convention captured
  in the [TAGS] section; the engine treats both identically. We don't
  branch on it here.

Helpers:
- decode_to_data_json    — split an .inp into spatial vs editable non-spatial
- encode_with_overlay    — render a complete .inp from source + overlay
- emit_report_json       — parse .rpt into a structured report.json
- emit_results_zarr      — write the (feature × period × metric) cube to Zarr
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from .inp import SwmmInput
from .out import SwmmOutput
from .rpt import SwmmReport


PathLike = Union[str, Path]


# Sections describing geometry / position. These live in PMTiles + LayerFeature
# rows in Console, NOT in data.json. They are read from source.inp at encode
# time and never modified through the data.json overlay.
SPATIAL_SECTIONS: frozenset = frozenset({
    # Nodes
    "junctions",
    "outfalls",
    "storage",
    "dividers",
    # Links
    "conduits",
    "pumps",
    "orifices",
    "weirs",
    "outlets",
    # Areal
    "subcatchments",
    # Geometry helpers
    "coordinates",
    "vertices",
    "polygons",
    "symbols",
})

# Sections that describe behavior / configuration / per-element attributes
# that don't fit on the spatial feature row. These are the editable surface
# in data.json. Keys mirror SwmmInput's section property names.
NON_SPATIAL_SECTIONS: frozenset = frozenset({
    "title",
    "options",
    "report",
    "tags",
    "raingages",
    "evaporation",
    "temperature",
    "snowpacks",
    "subareas",
    "infiltration",
    "aquifers",
    "groundwater",
    "lid_controls",
    "lid_usage",
    "hydrographs",
    "rdii",
    "curves",
    "timeseries",
    "patterns",
    "controls",
    "rules",
    "pollutants",
    "landuses",
    "coverages",
    "loadings",
    "buildup",
    "washoff",
    "treatment",
    "inflows",
    "dwf",
    "files",
    "transects",
    "xsections",
    "losses",
    "map",
    "backdrop",
    "labels",
})


# ---------------------------------------------------------------------------
# .inp ↔ data.json
# ---------------------------------------------------------------------------

def decode_to_data_json(inp_path: PathLike) -> Dict[str, Any]:
    """
    Extract the non-spatial sections of a SWMM .inp file as a serializable
    dict suitable for writing as `data.json` on S3.

    Spatial sections (junctions, conduits, subcatchments, coordinates, etc.)
    are excluded — they live in the spatial pipeline (PMTiles + LayerFeature).

    Args:
        inp_path: Path to a source .inp file.

    Returns:
        A dict whose keys are a subset of NON_SPATIAL_SECTIONS. Sections that
        the source .inp does not contain are omitted (not present as None).
    """
    with SwmmInput(Path(inp_path)) as model:
        full = model.to_dict()

    data: Dict[str, Any] = {}
    for section in NON_SPATIAL_SECTIONS:
        if section in full and full[section] not in (None, "", [], {}):
            data[section] = full[section]
    return data


def encode_with_overlay(
    source_inp_path: PathLike,
    data_overlay: Dict[str, Any],
) -> str:
    """
    Render a complete .inp by overlaying the editable non-spatial sections
    (`data_overlay`) onto an immutable source `.inp`. Spatial sections from
    the source are preserved verbatim. Spatial keys in `data_overlay` are
    silently ignored.

    Returns the rendered .inp file content as a string.

    The SwmmInput high-level interface lacks an `to_inp_string` method, so
    this writes via a temp file and reads it back. It's still cheap.
    """
    import tempfile

    with SwmmInput(Path(source_inp_path)) as model:
        for section, value in data_overlay.items():
            if section not in NON_SPATIAL_SECTIONS:
                # Silently ignore — spatial edits don't go through this path.
                continue
            model[section] = value

        # SwmmInput writes via a file on disk. Use a NamedTemporaryFile
        # (with delete=False on POSIX so we can close-then-read).
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".inp", delete=False, encoding="utf-8"
        ) as tmp:
            tmp_path = Path(tmp.name)

        try:
            model.to_inp(tmp_path)
            return tmp_path.read_text(encoding="utf-8")
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# .rpt → report.json
# ---------------------------------------------------------------------------

def emit_report_json(
    rpt_path: PathLike,
    out_path: Optional[PathLike] = None,
) -> Dict[str, Any]:
    """
    Produce the consumer-shaped `report.json` from a SWMM .rpt (and
    optionally cross-referenced with the binary .out for richer summaries).

    Args:
        rpt_path: Path to the SWMM .rpt file.
        out_path: Optional path to the binary .out for per-feature summaries.

    Returns:
        Dict with: header, element_count, analysis_options, continuity,
        runoff/depth/inflow/flooding/storage/pump/lid/flow_classification
        summary tables, plus per_feature_summary if .out is provided, plus
        a metrics descriptor.
    """
    with SwmmReport(rpt_path) as report:
        out: Dict[str, Any] = {
            "header": report.header,
            "element_count": report.element_count,
            "analysis_options": report.analysis_options,
            "continuity": report.continuity,
            "subcatchment_runoff": report.subcatchment_runoff,
            "node_depth": report.node_depth,
            "node_inflow": report.node_inflow,
            "node_flooding": report.node_flooding,
            "node_surcharge": report.node_surcharge,
            "outfall_loading": report.outfall_loading,
            "link_flow": report.link_flow,
            "conduit_surcharge": report.conduit_surcharge,
            "storage_volume": report.storage_volume,
            "pumping_summary": report.pumping_summary,
            "lid_performance": report.lid_performance,
            "flow_classification": report.flow_classification,
            "groundwater_summary": report.groundwater_summary,
            "quality_routing_continuity": report.quality_routing_continuity,
            "subcatchment_washoff": report.subcatchment_washoff,
            "link_pollutant_load": report.link_pollutant_load,
        }

    if out_path is not None:
        out["per_feature_summary"] = _per_feature_summary(out_path)

    out["metrics"] = {
        "node": _NODE_METRICS,
        "link": _LINK_METRICS,
        "subcatchment": _SUB_METRICS,
    }
    return out


# Standard SWMM .out variables per role (excluding pollutants, which are
# discovered dynamically from the .out file's pollutant_labels).
_NODE_METRICS: List[str] = [
    "depth", "head", "volume", "lateral_inflow", "total_inflow", "flooding",
]
_LINK_METRICS: List[str] = [
    "flow_rate", "flow_depth", "flow_velocity", "flow_volume", "capacity",
]
_SUB_METRICS: List[str] = [
    "rainfall", "snow_depth", "evaporation", "infiltration", "runoff",
]


def _per_feature_summary(out_path: PathLike) -> Dict[str, Any]:
    """Per-feature min/max/mean across periods, all roles."""
    summary: Dict[str, Any] = {"nodes": {}, "links": {}, "subcatchments": {}}

    with SwmmOutput(Path(out_path), load_time_series=True) as ep:
        nodes_df = _safe_to_dataframe(ep, "nodes")
        links_df = _safe_to_dataframe(ep, "links")
        sub_df = _safe_to_dataframe(ep, "subcatchments")

    if nodes_df is not None:
        summary["nodes"] = _summarize_per_feature(nodes_df)
    if links_df is not None:
        summary["links"] = _summarize_per_feature(links_df)
    if sub_df is not None:
        summary["subcatchments"] = _summarize_per_feature(sub_df)

    return summary


def _safe_to_dataframe(ep: SwmmOutput, role: str):
    """Best-effort dataframe export; returns None on absence / failure."""
    try:
        df = ep.to_dataframe(element_type=role)
    except Exception:
        return None
    if df is None or getattr(df, "empty", True):
        return None
    return df


def _summarize_per_feature(df) -> Dict[str, Any]:
    """
    Min/max/mean per metric per feature for a SwmmOutput dataframe.

    SWMM's `to_dataframe(element_type=...)` returns a MultiIndex DataFrame
    keyed on (timestamp, element_name). We group by element_name (the second
    level) and reduce across the time axis.
    """
    out: Dict[str, Any] = {}

    # MultiIndex DataFrame: index level 1 is element_name.
    try:
        idx_names = df.index.names
        element_level = idx_names.index("element_name") if "element_name" in idx_names else 1
        grouped = df.groupby(level=element_level)
    except Exception:
        return out

    for fid, sub in grouped:
        per_metric: Dict[str, Any] = {}
        for col in sub.columns:
            series = sub[col]
            try:
                per_metric[col] = {
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "mean": float(series.mean()),
                }
            except (TypeError, ValueError):
                continue
        out[str(fid)] = per_metric
    return out


# ---------------------------------------------------------------------------
# .out → results.zarr
# ---------------------------------------------------------------------------

def emit_results_zarr(
    out_path: PathLike,
    inp_path: PathLike,
    zarr_store: Any,
    *,
    chunk_features: int = 10_000,
    sort_spatial: bool = True,
) -> Dict[str, Any]:
    """
    Write SWMM simulation time-series to a Zarr store.

    Layout (one xarray Dataset; per-role arrays):
        nodes          shape (N, P, M_node)
        links          shape (L, P, M_link)
        subcatchments  shape (S, P, M_sub)
    Plus dynamic per-pollutant arrays (suffix _quality_<pollutant>) when
    the model defines pollutants.

    Coordinates: <role>_feature_id, period_seconds, <role>_metric.

    Features pre-sorted by Z-order Morton curve on coordinates when
    `sort_spatial=True` so feature-axis chunks are spatially coherent.

    Args:
        out_path:        Path to SWMM binary .out.
        inp_path:        Path to source .inp (for spatial sort coordinates).
        zarr_store:      A zarr-store-compatible target.
        chunk_features:  Feature-axis chunk size. Default 10_000.
        sort_spatial:    If True, sort features by Z-order on coordinates.

    Returns:
        Descriptor dict with shapes, metric lists, period count.
    """
    try:
        import numpy as np
        import xarray as xr
    except ImportError as e:
        raise ImportError(
            "emit_results_zarr requires `xarray` and `zarr`. "
            "Install with: pip install 'swmm-utils[console]'"
        ) from e

    with SwmmInput(Path(inp_path)) as inp_model:
        coords_data = inp_model.to_dict().get("coordinates", []) or []
    coords_by_id = _build_coords_lookup(coords_data)

    with SwmmOutput(Path(out_path), load_time_series=True) as ep:
        node_ids = list(ep.node_labels)
        link_ids = list(ep.link_labels)
        sub_ids = list(ep.subcatchment_labels)
        n_periods = ep.n_periods
        report_interval = ep.report_interval
        step_seconds = int(report_interval.total_seconds()) if report_interval else 1

        node_df = _safe_to_dataframe(ep, "nodes")
        link_df = _safe_to_dataframe(ep, "links")
        sub_df = _safe_to_dataframe(ep, "subcatchments")

    node_metrics = list(_NODE_METRICS)
    link_metrics = list(_LINK_METRICS)
    sub_metrics = list(_SUB_METRICS)

    node_arr = _df_to_cube(node_df, node_ids, n_periods, node_metrics)
    link_arr = _df_to_cube(link_df, link_ids, n_periods, link_metrics)
    sub_arr = _df_to_cube(sub_df, sub_ids, n_periods, sub_metrics)

    if sort_spatial:
        node_order = _zorder(node_ids, coords_by_id)
        link_order = _zorder(link_ids, coords_by_id)
        sub_order = _zorder(sub_ids, coords_by_id)
        node_ids = [node_ids[i] for i in node_order]
        node_arr = node_arr[node_order]
        link_ids = [link_ids[i] for i in link_order]
        link_arr = link_arr[link_order]
        sub_ids = [sub_ids[i] for i in sub_order]
        sub_arr = sub_arr[sub_order]

    period_seconds = (np.arange(n_periods, dtype="int32") * step_seconds).astype("int32")

    data_vars: Dict[str, Any] = {}
    coords: Dict[str, Any] = {
        "period_seconds": ("period_idx", period_seconds),
    }
    encoding: Dict[str, Dict[str, Any]] = {}

    if len(node_ids) > 0:
        data_vars["nodes"] = (("node_idx", "period_idx", "node_metric"), node_arr.astype("float32"))
        coords["node_feature_id"] = ("node_idx", np.array(node_ids, dtype=object))
        coords["node_metric"] = node_metrics
        encoding["nodes"] = {"chunks": (
            min(chunk_features, max(1, len(node_ids))), n_periods, len(node_metrics),
        )}
    if len(link_ids) > 0:
        data_vars["links"] = (("link_idx", "period_idx", "link_metric"), link_arr.astype("float32"))
        coords["link_feature_id"] = ("link_idx", np.array(link_ids, dtype=object))
        coords["link_metric"] = link_metrics
        encoding["links"] = {"chunks": (
            min(chunk_features, max(1, len(link_ids))), n_periods, len(link_metrics),
        )}
    if len(sub_ids) > 0:
        data_vars["subcatchments"] = (
            ("sub_idx", "period_idx", "sub_metric"), sub_arr.astype("float32"),
        )
        coords["sub_feature_id"] = ("sub_idx", np.array(sub_ids, dtype=object))
        coords["sub_metric"] = sub_metrics
        encoding["subcatchments"] = {"chunks": (
            min(chunk_features, max(1, len(sub_ids))), n_periods, len(sub_metrics),
        )}

    ds = xr.Dataset(
        data_vars=data_vars,
        coords=coords,
        attrs={
            "producer": "swmm-utils",
            "sim_engine": "swmm",
            "report_time_step_seconds": step_seconds,
        },
    )

    ds.to_zarr(zarr_store, mode="w", consolidated=True, encoding=encoding)

    return {
        "nodes_shape": [len(node_ids), n_periods, len(node_metrics)],
        "links_shape": [len(link_ids), n_periods, len(link_metrics)],
        "subcatchments_shape": [len(sub_ids), n_periods, len(sub_metrics)],
        "node_metrics": node_metrics,
        "link_metrics": link_metrics,
        "sub_metrics": sub_metrics,
        "n_periods": n_periods,
        "report_time_step_seconds": step_seconds,
        "chunk_features": chunk_features,
    }


def _build_coords_lookup(coords_data: List[Dict[str, Any]]) -> Dict[str, tuple]:
    """
    Build {feature_id: (x, y)} from a SWMM coordinates section.
    SwmmInput's keys vary (id/node/x/y/x_coord/y_coord depending on parser
    version), so probe several.
    """
    out: Dict[str, tuple] = {}
    for c in coords_data:
        fid = c.get("id") or c.get("node") or c.get("name")
        if fid is None:
            continue
        x = c.get("x_coord", c.get("x"))
        y = c.get("y_coord", c.get("y"))
        if x is None or y is None:
            continue
        out[fid] = (x, y)
    return out


def _df_to_cube(df, ordered_ids: list, n_periods: int, metrics: Iterable[str]):
    """
    Reshape SWMM's MultiIndex DataFrame to (n_features, n_periods, n_metrics).
    DataFrame index: (timestamp, element_name). Columns are metric names.
    Missing metrics fill with NaN; missing periods or features stay NaN.
    """
    import numpy as np

    metrics = list(metrics)
    n = len(ordered_ids)
    m = len(metrics)
    cube = np.full((n, n_periods, m), np.nan, dtype="float64")

    if df is None or getattr(df, "empty", True):
        return cube

    id_to_idx = {fid: i for i, fid in enumerate(ordered_ids)}
    metric_to_idx = {name: j for j, name in enumerate(metrics)}

    # Identify which level holds element_name and which holds time.
    idx_names = df.index.names
    name_lvl = idx_names.index("element_name") if "element_name" in idx_names else 1
    time_lvl = 1 - name_lvl

    # Flatten to row-iteration; vectorized on small data is overkill.
    for (k0, k1), row in df.iterrows():
        fid = k1 if name_lvl == 1 else k0
        ts = k0 if name_lvl == 1 else k1
        i = id_to_idx.get(fid)
        if i is None:
            continue
        # Map timestamp → period index. We rely on the timestamps being in
        # order — SWMM .out always emits them sequentially.
        # The time level is a DatetimeIndex; positions are 0..n_periods-1.
        # Use level position to derive period:
        try:
            p = int(df.index.get_level_values(time_lvl).get_loc(ts))
        except (KeyError, TypeError):
            continue
        if isinstance(p, slice) or not isinstance(p, int):
            # Multiple matches — pick the first.
            try:
                p = int(getattr(p, "start", 0))
            except Exception:
                continue
        if p < 0 or p >= n_periods:
            continue
        for col, val in row.items():
            j = metric_to_idx.get(col)
            if j is None:
                continue
            try:
                cube[i, p, j] = float(val)
            except (TypeError, ValueError):
                continue
    return cube


def _zorder(ids: list, coords_by_id: Dict[str, tuple]) -> list:
    """
    Return indices that sort `ids` by Z-order (Morton) curve on (x, y).
    Features without coordinates fall to the tail in original order.
    """
    import numpy as np

    n = len(ids)
    if n == 0:
        return []

    xs = np.full(n, np.nan)
    ys = np.full(n, np.nan)
    has_coord = np.zeros(n, dtype=bool)
    for i, fid in enumerate(ids):
        c = coords_by_id.get(fid)
        if c is None:
            continue
        x, y = c
        if x is None or y is None:
            continue
        try:
            xs[i] = float(x)
            ys[i] = float(y)
            has_coord[i] = True
        except (TypeError, ValueError):
            continue

    if not has_coord.any():
        return list(range(n))

    x_valid = xs[has_coord]
    y_valid = ys[has_coord]
    x_lo, x_hi = float(x_valid.min()), float(x_valid.max())
    y_lo, y_hi = float(y_valid.min()), float(y_valid.max())
    x_range = max(x_hi - x_lo, 1e-12)
    y_range = max(y_hi - y_lo, 1e-12)

    qx = np.zeros(n, dtype=np.uint64)
    qy = np.zeros(n, dtype=np.uint64)
    qx[has_coord] = np.clip(((xs[has_coord] - x_lo) / x_range * 0xFFFF), 0, 0xFFFF).astype(np.uint64)
    qy[has_coord] = np.clip(((ys[has_coord] - y_lo) / y_range * 0xFFFF), 0, 0xFFFF).astype(np.uint64)

    keys = _morton(qx) | (_morton(qy) << 1)
    order = np.lexsort((keys, ~has_coord))
    return order.tolist()


def _morton(v):
    v = v & 0xFFFF
    v = (v | (v << 8)) & 0x00FF00FF
    v = (v | (v << 4)) & 0x0F0F0F0F
    v = (v | (v << 2)) & 0x33333333
    v = (v | (v << 1)) & 0x55555555
    return v
