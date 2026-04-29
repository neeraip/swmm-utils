"""
Producer-side helpers used by NEER Console / WRM API to derive consumer-shaped
artifacts from SWMM .inp / .rpt / .out files.

Mirrors `epanet_utils.exports`. SWMM-specific differences:
- Subcatchments are a third role alongside nodes and links.
- Pollutants are dynamic — one metric per pollutant defined in the model.
- The SWMM 1D vs 2D distinction is an authoring convention captured in
  the [TAGS] section by some external GUIs; the engine treats both
  identically. We don't branch on it here.

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


# ---------------------------------------------------------------------------
# .inp → per-role GeoJSON layers
# ---------------------------------------------------------------------------
#
# This is the canonical SWMM .inp → spatial-layer parser. It used to live in
# NEER's lambda-importer (`app/inp_parser.py`), with a lower-fidelity copy in
# the console seed script — drift between the two was the motivation for
# lifting it here. Both the lambda and the seed should call into this helper
# instead of reimplementing per-element cross-references.
#
# Output is GeoJSON FeatureCollection dicts (no shapely / geopandas dep).
# Callers who want a GeoDataFrame can do:
#     gpd.GeoDataFrame.from_features(fc["features"], crs=spec["crs"])

# Per-engine layer-name → HydraulicModelRole. Layer names are intentionally
# capitalized to match the human-readable convention used in the import
# pipeline; the role enum is the lowercase token persisted in the gis DB.
LAYER_ROLE_MAP: Dict[str, str] = {
    "Rain Gages":    "raingage",
    "Subcatchments": "subcatchment",
    "Junctions":     "junction",
    "Outfalls":      "outfall",
    "Storage":       "storage",
    "Dividers":      "divider",
    "Conduits":      "conduit",
    "Pumps":         "pump",
    "Orifices":      "orifice",
    "Weirs":         "weir",
    "Outlets":       "outlet",
}


def _sf(val: Any) -> Optional[float]:
    """Safe float conversion. Returns None if the value can't be coerced."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _link_coords(
    n1: str,
    n2: str,
    link_id: str,
    coord_map: Dict[str, tuple],
    vertex_map: Dict[str, List[tuple]],
) -> Optional[List[List[float]]]:
    """LineString coordinates: start node → vertices in order → end node.

    Returns None if either endpoint isn't in the coord map (a real model
    error — engine would refuse to simulate). Vertices for a link with no
    [VERTICES] rows yields a straight 2-point line.
    """
    start = coord_map.get(n1)
    end = coord_map.get(n2)
    if not start or not end:
        return None
    coords: List[List[float]] = [[start[0], start[1]]]
    for vx, vy in vertex_map.get(link_id, []):
        coords.append([vx, vy])
    coords.append([end[0], end[1]])
    return coords


def emit_geojson_layers(
    inp_path: PathLike,
    crs: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build one GeoJSON FeatureCollection per HydraulicModelRole.

    Cross-references the per-element sibling sections that don't get
    standalone editors in the console (xsections, losses, subareas,
    infiltration, coverages, lid_usage, inflows, dwf, tags) onto each
    feature's properties so the attribute table reflects the full
    authored .inp.

    Subcatchments without a [POLYGONS] boundary fall back to a small
    synthesized square at their outlet (sized as 0.05% of the model's
    coordinate extent) so they still render. Subcatchments without a
    resolvable outlet are silently dropped — there's nowhere to put
    them spatially.

    Args:
        inp_path: Path to a source .inp file.
        crs: Optional CRS string (e.g. ``"EPSG:2236"``, ``"ESRI:102726"``)
             stored in each layer spec for downstream reprojection. The
             coordinate values themselves are never transformed here.

    Returns:
        List of layer specs:
            [
              {
                "name": "Junctions",
                "role": "junction",
                "geometry_type": "Point",
                "crs": crs,
                "feature_collection": {
                  "type": "FeatureCollection",
                  "features": [...],
                },
              },
              ...
            ]

        Empty roles are omitted. ``Subcatchments`` is emitted (possibly
        with empty features list) whenever the model declared any
        subcatchments at all, so the layer schema stays consistent
        across imports.
    """
    with SwmmInput(Path(inp_path)) as inp:
        full = inp.to_dict()

    # --- Geometry lookups ---
    coord_map: Dict[str, tuple] = {}
    for c in full.get("coordinates", []) or []:
        nid = str(c.get("name", c.get("node", "")))
        if nid:
            try:
                coord_map[nid] = (float(c["x"]), float(c["y"]))
            except (KeyError, TypeError, ValueError):
                continue

    vertex_map: Dict[str, List[tuple]] = {}
    for v in full.get("vertices", []) or []:
        lid = str(v.get("link", v.get("name", "")))
        if not lid:
            continue
        try:
            vertex_map.setdefault(lid, []).append((float(v["x"]), float(v["y"])))
        except (KeyError, TypeError, ValueError):
            continue

    polygon_map: Dict[str, List[tuple]] = {}
    for p in full.get("polygons", []) or []:
        sid = str(p.get("subcatchment", p.get("name", "")))
        if not sid:
            continue
        try:
            polygon_map.setdefault(sid, []).append((float(p["x"]), float(p["y"])))
        except (KeyError, TypeError, ValueError):
            continue

    # --- Cross-reference lookups (sibling sections) ---
    tag_by_id: Dict[str, str] = {}
    for t in full.get("tags", []) or []:
        nid = (
            t.get("name") or t.get("id") or t.get("element_name") or t.get("subject")
        )
        tag = t.get("tag") or t.get("value") or t.get("category")
        if nid is not None and tag is not None:
            tag_by_id[str(nid)] = str(tag)

    xsection_by_link = {
        str(x.get("link", x.get("name", ""))): {
            f"xsection_{k}": v for k, v in x.items() if k not in ("link", "name")
        }
        for x in (full.get("xsections", []) or [])
        if x.get("link") or x.get("name")
    }
    losses_by_link = {
        str(l.get("link", l.get("name", ""))): {
            f"loss_{k}": v for k, v in l.items() if k not in ("link", "name")
        }
        for l in (full.get("losses", []) or [])
        if l.get("link") or l.get("name")
    }
    subareas_by_id = {
        str(s.get("subcatchment", s.get("name", ""))): {
            k: v for k, v in s.items() if k not in ("subcatchment", "name")
        }
        for s in (full.get("subareas", []) or [])
        if s.get("subcatchment") or s.get("name")
    }
    # The decoder emits this section under "infiltrations" (plural) — the
    # historical singular alias is also accepted defensively in case an
    # older blob round-trips through this code path.
    infiltration_section = (
        full.get("infiltrations") or full.get("infiltration") or []
    )
    infiltration_by_id = {
        str(i.get("subcatchment", i.get("name", ""))): {
            f"infil_{k}": v for k, v in i.items() if k not in ("subcatchment", "name")
        }
        for i in infiltration_section
        if i.get("subcatchment") or i.get("name")
    }

    # Per-node external inflows. Multi-row sections (one per pollutant) are
    # collapsed to the FLOW row plus a count of additional rows so the
    # attribute table stays one row per element.
    inflow_by_id: Dict[str, Dict[str, Any]] = {}
    for inf in full.get("inflows", []) or []:
        nid = str(inf.get("node", inf.get("id", "")))
        if not nid:
            continue
        constituent = str(inf.get("constituent", inf.get("type", ""))).upper()
        if constituent == "FLOW" or nid not in inflow_by_id:
            inflow_by_id[nid] = {
                "inflow_constituent": constituent or None,
                "inflow_timeseries": inf.get("timeseries"),
                "inflow_type": inf.get("type"),
                "inflow_mfactor": _sf(inf.get("mfactor")),
                "inflow_sfactor": _sf(inf.get("sfactor")),
                "inflow_baseline": _sf(inf.get("baseline")),
                "inflow_baseline_pattern": inf.get("baseline_pattern"),
            }

    # Per-node dry-weather flow. The decoder writes:
    #   {node, constituent, baseline, patterns: ["WEEKDAY", "WEEKEND", "", ""]}
    # We expose the engine's authoring shape on the feature with a
    # ``dwf_baseline`` value (the .inp column is literally named
    # "Baseline") and the four pattern slots split out so the panel
    # can render them as individual reference chips.
    def _strip_quotes(s: Any) -> Optional[str]:
        if s is None:
            return None
        out = str(s)
        if len(out) >= 2 and out[0] == '"' and out[-1] == '"':
            out = out[1:-1]
        return out or None

    dwf_by_id: Dict[str, Dict[str, Any]] = {}
    for d in full.get("dwf", []) or []:
        nid = str(d.get("node", d.get("id", "")))
        if not nid:
            continue
        constituent = str(d.get("constituent", "")).upper()
        if constituent == "FLOW" or nid not in dwf_by_id:
            patterns = d.get("patterns") or []
            if not isinstance(patterns, list):
                patterns = [patterns]
            entry: Dict[str, Any] = {
                "dwf_constituent": d.get("constituent"),
                "dwf_baseline": _sf(
                    d.get("baseline", d.get("value", d.get("average")))
                ),
            }
            for i in range(4):
                entry[f"dwf_pattern{i + 1}"] = _strip_quotes(
                    patterns[i] if i < len(patterns) else None
                )
            dwf_by_id[nid] = entry

    # [COVERAGES]: one row per (subcatchment, landuse). Summarize as the
    # dominant landuse + a count so the row stays single-valued.
    coverages_by_id: Dict[str, Dict[str, Any]] = {}
    for cv in full.get("coverages", []) or []:
        sid = str(cv.get("subcatchment", cv.get("name", "")))
        if not sid:
            continue
        landuse = cv.get("landuse")
        pct = _sf(cv.get("percent")) or 0.0
        bucket = coverages_by_id.setdefault(
            sid,
            {
                "coverage_dominant_landuse": None,
                "coverage_dominant_pct": 0.0,
                "coverage_count": 0,
            },
        )
        bucket["coverage_count"] += 1
        if pct > bucket["coverage_dominant_pct"]:
            bucket["coverage_dominant_landuse"] = landuse
            bucket["coverage_dominant_pct"] = pct

    # [LID_USAGE]: many rows per subcatchment. Roll up into count + first
    # control name + total area + comma-joined names so consumers can
    # render the full set without re-aggregating.
    lid_usage_by_id: Dict[str, Dict[str, Any]] = {}
    for lu in full.get("lid_usage", []) or []:
        sid = str(lu.get("subcatchment", lu.get("name", "")))
        if not sid:
            continue
        bucket = lid_usage_by_id.setdefault(
            sid,
            {
                "lid_count": 0,
                "lid_first_control": None,
                "lid_names": [],
                "lid_total_area": 0.0,
            },
        )
        bucket["lid_count"] += 1
        ctrl = lu.get("lid_control") or lu.get("control")
        if bucket["lid_first_control"] is None:
            bucket["lid_first_control"] = ctrl
        if ctrl and ctrl not in bucket["lid_names"]:
            bucket["lid_names"].append(ctrl)
        a = _sf(lu.get("area"))
        if a is not None:
            bucket["lid_total_area"] += a
    # Finalize lid_names as a stable comma-joined string.
    for bucket in lid_usage_by_id.values():
        bucket["lid_names"] = ",".join(bucket["lid_names"]) or None

    # [RDII]: per-node unit hydrograph assignment. The decoder emits a
    # list of {node, unithydrograph, sewer_area, factor}; bind by node.
    rdii_by_id: Dict[str, Dict[str, Any]] = {}
    for r in full.get("rdii", []) or []:
        nid = str(r.get("node", r.get("id", "")))
        if not nid:
            continue
        rdii_by_id[nid] = {
            "rdii_unithydrograph": r.get("unithydrograph"),
            "rdii_sewer_area": _sf(r.get("sewer_area")),
            "rdii_factor": _sf(r.get("factor")),
        }

    # [TREATMENT]: many rows per node (one per pollutant). Collapse to
    # the FIRST pollutant's function string + a count so the row stays
    # single-valued. Consumers can look up the full set via the node id
    # if they need it.
    treatment_by_id: Dict[str, Dict[str, Any]] = {}
    for t in full.get("treatment", []) or []:
        nid = str(t.get("node", ""))
        if not nid:
            continue
        bucket = treatment_by_id.setdefault(
            nid,
            {
                "treatment_count": 0,
                "treatment_pollutant": None,
                "treatment_function": None,
            },
        )
        bucket["treatment_count"] += 1
        if bucket["treatment_pollutant"] is None:
            bucket["treatment_pollutant"] = t.get("pollutant")
            bucket["treatment_function"] = t.get("function")

    # [GROUNDWATER]: one row per subcatchment. Surface every parameter
    # under a stable ``gw_`` prefix so the attribute table can group.
    groundwater_by_id: Dict[str, Dict[str, Any]] = {}
    for gw in full.get("groundwater", []) or []:
        sid = str(gw.get("subcatchment", gw.get("name", "")))
        if not sid:
            continue
        groundwater_by_id[sid] = {
            f"gw_{k}": v
            for k, v in gw.items()
            if k not in ("subcatchment", "name")
        }

    # [INLET_USAGE]: one row per conduit assignment. Bind onto the
    # conduit feature with stable ``inlet_*`` prefixes; record the
    # street name from the conduit's [CONDUITS] row when present so
    # styling can branch on street-flow links.
    inlet_usage_by_link: Dict[str, Dict[str, Any]] = {}
    for u in full.get("inlet_usage", []) or []:
        lid = str(u.get("conduit", ""))
        if not lid:
            continue
        inlet_usage_by_link[lid] = {
            "inlet_name": u.get("inlet"),
            "inlet_node": u.get("node"),
            "inlet_count": _sf(u.get("number")) or 1,
            "inlet_pct_clogged": _sf(u.get("pct_clogged")),
            "inlet_max_flow": _sf(u.get("max_flow")),
            "inlet_h_dstore": _sf(u.get("h_dstore")),
            "inlet_w_dstore": _sf(u.get("w_dstore")),
            "inlet_placement": u.get("placement"),
        }

    # [CONTROLS] presence flag. The decoder stores controls as a single
    # string blob; we scan it for each link/node id and set ``in_ctrl``
    # / ``in_ctrl_node`` to True when the id appears as a whole token.
    # Cheaper than parsing the rule-language properly and good enough
    # for "show me elements involved in control rules" symbology.
    controls_text = ""
    if isinstance(full.get("controls"), str):
        controls_text = full["controls"]

    def _in_controls(eid: str) -> bool:
        if not eid or not controls_text:
            return False
        # Word-boundary match so "P1" doesn't match "P10".
        token = eid
        idx = 0
        while True:
            idx = controls_text.find(token, idx)
            if idx < 0:
                return False
            before = controls_text[idx - 1] if idx > 0 else " "
            after_pos = idx + len(token)
            after = controls_text[after_pos] if after_pos < len(controls_text) else " "
            if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
                return True
            idx = after_pos

    # OPTIONS.INFILTRATION choice — when present, surface on each
    # subcatchment as ``infil_model`` so the UI can label the generic
    # param1..5 columns (e.g. HORTON's max-rate / min-rate / decay vs
    # CURVE_NUMBER's curve number / conductivity / dry time).
    options_dict = full.get("options", {}) or {}
    infiltration_model = None
    if isinstance(options_dict, dict):
        for k, v in options_dict.items():
            if k.lower() == "infiltration":
                infiltration_model = str(v).upper() if v else None
                break

    def _enrich_node(row: Dict[str, Any], nid: str) -> Dict[str, Any]:
        if nid in tag_by_id:
            row["tag"] = tag_by_id[nid]
        if nid in inflow_by_id:
            row.update(inflow_by_id[nid])
        if nid in dwf_by_id:
            row.update(dwf_by_id[nid])
        if nid in rdii_by_id:
            row.update(rdii_by_id[nid])
        if nid in treatment_by_id:
            row.update(treatment_by_id[nid])
        # Computed: rim_elev = invert + max_depth. Junctions / storage /
        # dividers have invert under "elevation" and max-depth under
        # "max_depth". Outfalls have only an invert (no rim) so this is
        # a no-op for them.
        elev = _sf(row.get("elevation"))
        depth = _sf(row.get("max_depth"))
        if elev is not None and depth is not None:
            row["rim_elev"] = elev + depth
        # Boolean: any [CONTROLS] rule references this node.
        row["in_ctrl"] = _in_controls(nid)
        return row

    def _enrich_link(row: Dict[str, Any], lid: str) -> Dict[str, Any]:
        if lid in tag_by_id:
            row["tag"] = tag_by_id[lid]
        if lid in xsection_by_link:
            row.update(xsection_by_link[lid])
        if lid in losses_by_link:
            row.update(losses_by_link[lid])
        if lid in inlet_usage_by_link:
            row.update(inlet_usage_by_link[lid])
        # Computed: slope = (from_invert - to_invert) / length where
        # invert = node.elevation + offset. Falls through silently if
        # any input is unresolvable so we don't manufacture a 0 slope.
        if all(k in row for k in ("from_node", "to_node", "length")):
            length = _sf(row.get("length"))
            if length and length > 0:
                from_inv = _sf(node_invert_by_id.get(row["from_node"]))
                to_inv = _sf(node_invert_by_id.get(row["to_node"]))
                in_off = _sf(row.get("in_offset")) or 0.0
                out_off = _sf(row.get("out_offset")) or 0.0
                if from_inv is not None and to_inv is not None:
                    row["slope"] = ((from_inv + in_off) - (to_inv + out_off)) / length
        # Boolean: any [CONTROLS] rule references this link.
        row["in_ctrl"] = _in_controls(lid)
        return row

    def _enrich_subcatchment(row: Dict[str, Any], sid: str) -> Dict[str, Any]:
        if sid in tag_by_id:
            row["tag"] = tag_by_id[sid]
        if sid in subareas_by_id:
            row.update(subareas_by_id[sid])
        if sid in infiltration_by_id:
            row.update(infiltration_by_id[sid])
        if sid in coverages_by_id:
            row.update(coverages_by_id[sid])
        if sid in lid_usage_by_id:
            row.update(lid_usage_by_id[sid])
        if sid in groundwater_by_id:
            row.update(groundwater_by_id[sid])
        if infiltration_model:
            row["infil_model"] = infiltration_model
        return row

    # Node-invert lookup for conduit slope computation. Built once
    # (post-coord_map) so all link enrichments reuse it. Includes every
    # node type — junctions, outfalls, storage, dividers — using the
    # `elevation` column on each section row.
    node_invert_by_id: Dict[str, Any] = {}
    for section_key in ("junctions", "outfalls", "storage", "dividers"):
        for r in full.get(section_key, []) or []:
            nid = r.get("name")
            if nid:
                node_invert_by_id[str(nid)] = r.get("elevation")

    layers: List[Dict[str, Any]] = []

    def _layer_spec(
        name: str, geometry_type: str, features: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return {
            "name": name,
            "role": LAYER_ROLE_MAP[name],
            "geometry_type": geometry_type,
            "crs": crs,
            "feature_collection": {
                "type": "FeatureCollection",
                "features": features,
            },
        }

    def _node_features(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for r in rows:
            nid = str(r.get("name", ""))
            xy = coord_map.get(nid)
            if not xy:
                continue
            row = _enrich_node({**r, "name": nid}, nid)
            out.append(
                {
                    "type": "Feature",
                    "id": nid,
                    "properties": row,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [xy[0], xy[1]],
                    },
                }
            )
        return out

    def _link_features(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for r in rows:
            lid = str(r.get("name", ""))
            n1 = str(r.get("from_node", ""))
            n2 = str(r.get("to_node", ""))
            coords = _link_coords(n1, n2, lid, coord_map, vertex_map)
            if not coords or len(coords) < 2:
                continue
            row = _enrich_link(
                {**r, "name": lid, "from_node": n1, "to_node": n2}, lid
            )
            out.append(
                {
                    "type": "Feature",
                    "id": lid,
                    "properties": row,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords,
                    },
                }
            )
        return out

    # Layer emit order matches console's SWMM_CANONICAL_LAYERS so the
    # from-scratch and import flows surface the same layer sequence:
    #   Rain Gages → Subcatchments → Junctions → Outfalls → Storage →
    #   Dividers → Conduits → Pumps → Orifices → Weirs → Outlets.

    # --- Rain Gages (point) ---
    raingages_section = full.get("raingages", []) or []
    if raingages_section:
        # Geometry comes from [SYMBOLS] (gage name → x,y). The decoder
        # writes that as ``symbols: list[{gage, x, y}]``.
        gage_xy: Dict[str, tuple] = {}
        for sym in full.get("symbols", []) or []:
            gid = str(sym.get("gage", sym.get("name", "")))
            if not gid:
                continue
            try:
                gage_xy[gid] = (float(sym["x"]), float(sym["y"]))
            except (KeyError, TypeError, ValueError):
                continue
        rain_feats: List[Dict[str, Any]] = []
        for r in raingages_section:
            rid = str(r.get("name", ""))
            xy = gage_xy.get(rid)
            if not xy:
                # Raingages with no [SYMBOLS] entry have no spatial
                # reference — skip rather than guess. The canonical
                # Rain Gages layer can still exist (empty) for users
                # to add gage symbols later.
                continue
            row = _enrich_node({**r, "name": rid}, rid)
            rain_feats.append({
                "type": "Feature",
                "id": rid,
                "properties": row,
                "geometry": {"type": "Point", "coordinates": [xy[0], xy[1]]},
            })
        if rain_feats:
            layers.append(_layer_spec("Rain Gages", "Point", rain_feats))

    # --- Subcatchments (polygon) ---
    subcatchments_section = full.get("subcatchments", []) or []
    if subcatchments_section:
        # Synth-square sizing: 0.05% of the model's coordinate extent so it
        # works in any CRS (state plane feet, UTM meters, lat/lon degrees).
        if coord_map:
            xs = [xy[0] for xy in coord_map.values()]
            ys = [xy[1] for xy in coord_map.values()]
            extent = max(max(xs) - min(xs), max(ys) - min(ys))
            synth_half = max(extent * 0.0005, 1e-6)
        else:
            synth_half = 1.0

        sub_feats: List[Dict[str, Any]] = []
        for sc in subcatchments_section:
            sid = str(sc.get("name", ""))
            if not sid:
                continue

            ring = polygon_map.get(sid)
            geometry: Optional[Dict[str, Any]] = None
            if ring and len(ring) >= 3:
                ring_coords = [[x, y] for x, y in ring]
                if ring_coords[0] != ring_coords[-1]:
                    ring_coords.append(ring_coords[0])
                geometry = {"type": "Polygon", "coordinates": [ring_coords]}
            else:
                outlet = str(sc.get("outlet", ""))
                xy = coord_map.get(outlet) if outlet else None
                if xy:
                    x, y = xy
                    geometry = {
                        "type": "Polygon",
                        "coordinates": [[
                            [x - synth_half, y - synth_half],
                            [x + synth_half, y - synth_half],
                            [x + synth_half, y + synth_half],
                            [x - synth_half, y + synth_half],
                            [x - synth_half, y - synth_half],
                        ]],
                    }

            if geometry is None:
                continue

            row = _enrich_subcatchment({**sc, "name": sid}, sid)
            sub_feats.append(
                {
                    "type": "Feature",
                    "id": sid,
                    "properties": row,
                    "geometry": geometry,
                }
            )

        layers.append(_layer_spec("Subcatchments", "Polygon", sub_feats))

    # --- Nodes (point) ---
    junctions = _node_features(full.get("junctions", []) or [])
    if junctions:
        layers.append(_layer_spec("Junctions", "Point", junctions))

    outfalls = _node_features(full.get("outfalls", []) or [])
    if outfalls:
        layers.append(_layer_spec("Outfalls", "Point", outfalls))

    storage = _node_features(full.get("storage", []) or [])
    if storage:
        layers.append(_layer_spec("Storage", "Point", storage))

    dividers = _node_features(full.get("dividers", []) or [])
    if dividers:
        layers.append(_layer_spec("Dividers", "Point", dividers))

    # --- Links (line) ---
    conduits = _link_features(full.get("conduits", []) or [])
    if conduits:
        layers.append(_layer_spec("Conduits", "LineString", conduits))

    for section_key, name in (
        ("pumps", "Pumps"),
        ("orifices", "Orifices"),
        ("weirs", "Weirs"),
        ("outlets", "Outlets"),
    ):
        feats = _link_features(full.get(section_key, []) or [])
        if feats:
            layers.append(_layer_spec(name, "LineString", feats))

    return layers


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

def _swmm_flatten_continuity(continuity: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Flatten SWMM's nested continuity dict to a one-level
    ``label -> display string`` map.

    SWMM's .rpt continuity sections (flow_routing, runoff,
    groundwater, quality_routing) emit each leaf as a 2-element list
    ``[volume_in_units, percent_of_inflow]``. The Console Results
    panel renders ``balances`` via simple key/value rows that skip
    nested objects, so we serialize each pair as ``"<vol> (<pct>%)"``
    string here.
    """
    out: Dict[str, str] = {}
    for section, sub in (continuity or {}).items():
        if not isinstance(sub, dict):
            continue
        for key, value in sub.items():
            label = f"{section}.{key}"
            if isinstance(value, (list, tuple)):
                if len(value) >= 2:
                    out[label] = f"{value[0]:g} ({value[1]:g}%)"
                elif len(value) == 1:
                    out[label] = f"{value[0]:g}"
                else:
                    out[label] = ""
            elif value is None:
                continue
            else:
                out[label] = str(value)
    return out


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
            # Top-level normalized fields the Console Results panel
            # consumes directly. Engine-shape sections above stay as
            # the source of truth; these are display-ready summaries.
            "warnings": list(report.warnings),
            "errors": list(report.errors),
            "timestamps": {
                "start_date": report.analysis_options.get("starting_date"),
                "end_date": report.analysis_options.get("ending_date"),
                "flow_units": report.analysis_options.get("flow_units"),
                "flow_routing_method": report.analysis_options.get(
                    "flow_routing_method"
                ),
            },
            "balances": _swmm_flatten_continuity(report.continuity),
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
        summary["nodes"] = _summarize_per_feature(nodes_df, _NODE_METRICS)
    if links_df is not None:
        summary["links"] = _summarize_per_feature(links_df, _LINK_METRICS)
    if sub_df is not None:
        summary["subcatchments"] = _summarize_per_feature(sub_df, _SUB_METRICS)

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


def _summarize_per_feature(df, metrics: Iterable[str]) -> Dict[str, Any]:
    """
    Min/max/mean per metric per feature for a SwmmOutput dataframe.

    SWMM's `to_dataframe(element_type=...)` returns a MultiIndex DataFrame
    keyed on (timestamp, element_name). Columns are the positional
    ``value_0`` … ``value_<M-1>`` (raw SWMM output indices); we map them
    to the canonical metric names so the summary is self-describing.

    Vectorized via ``groupby.agg`` so 100k+ rows reduce in a single
    pass instead of a Python-level inner loop.
    """
    import numpy as np

    out: Dict[str, Any] = {}
    if df is None or getattr(df, "empty", True):
        return out

    metrics = list(metrics)

    try:
        idx_names = df.index.names
        element_level = idx_names.index("element_name") if "element_name" in idx_names else 1
        grouped = df.groupby(level=element_level, sort=False)
        # Vectorized aggregation: one pass over the data, returns a
        # DataFrame keyed by element_name with multi-level columns
        # (metric_col, stat).
        agg = grouped.agg(["min", "max", "mean"])
    except Exception:
        return out

    raw_cols = list(df.columns)

    # Iterate over the small element axis (hundreds typically) and pull
    # the precomputed stats out of `agg`.
    for fid in agg.index:
        per_metric: Dict[str, Any] = {}
        for j, raw_col in enumerate(raw_cols):
            metric_name = metrics[j] if j < len(metrics) else raw_col
            try:
                vmin = float(agg.loc[fid, (raw_col, "min")])
                vmax = float(agg.loc[fid, (raw_col, "max")])
                vmean = float(agg.loc[fid, (raw_col, "mean")])
            except (TypeError, ValueError, KeyError):
                continue
            if any(np.isnan([vmin, vmax, vmean])):
                continue
            per_metric[metric_name] = {"min": vmin, "max": vmax, "mean": vmean}
        out[str(fid)] = per_metric
    return out


# ---------------------------------------------------------------------------
# .out → results.parquet   (sidecar for file-ingestion-engine query service)
# ---------------------------------------------------------------------------

# Compression/writer settings mirrored from
# `neeraip/file-ingestion-engine/ingest/csv_ingest.py`.
_PARQUET_WRITER_KWARGS: Dict[str, Any] = {
    "compression": "zstd",
    "compression_level": 3,
    "use_dictionary": True,
    "write_statistics": True,
    "data_page_size": 1 << 20,     # 1 MB
    "row_group_size": 1_000_000,
    "flavor": "spark",
}

# Synthetic timestamp base so the query service's datetime parsing works
# without configuration. SWMM .out timestamps CAN be real wall-clock if the
# model's START_DATE is set, but we use a synthetic anchor for consistency
# with the EPANET emitter. Add period_seconds to this to derive period_ts.
_PERIOD_TS_BASE = "2000-01-01"


def emit_results_parquet(
    out_path: PathLike,
    inp_path: PathLike,
    parquet_path: PathLike,
) -> Dict[str, Any]:
    """
    Write simulation time-series to a single Parquet file as a sidecar for
    the file-ingestion-engine query service. Long-by-period wide-by-metric
    format: one row per (feature, period). Per-role metric columns are
    nulled across the other role(s).

    Schema:
        fid             string (dict)   — SWMM element id ("J-101","C-12")
        role            string (dict)   — "node" | "link" | "subcatchment"
        element_type    string (dict)   — junction|outfall|storage|divider|
                                          conduit|pump|orifice|weir|outlet|
                                          subcatchment
        period_idx      int32
        period_ts       timestamp[us]   — synthetic, base 2000-01-01
        period_seconds  int32
        depth / head / volume / lateral_inflow / total_inflow / flooding   (nodes)
        flow_rate / flow_depth / flow_velocity / flow_volume / capacity   (links)
        rainfall / snow_depth / evaporation / infiltration / runoff       (subcatchments)

    All metric columns are float32. Rows from other roles have NULL in the
    metric columns not applicable to that role.

    Writer settings match file-ingestion-engine/ingest/csv_ingest.py so the
    query service reads it indistinguishably from CSV-origin Parquet.

    Args:
        out_path:     Path to SWMM binary .out.
        inp_path:     Path to source .inp (for element_type classification).
        parquet_path: Destination path for the `.parquet` file.

    Returns:
        Small descriptor dict: row count, column list, n_periods.
    """
    try:
        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as e:
        raise ImportError(
            "emit_results_parquet requires `pandas` and `pyarrow` (already "
            "in install_requires — reinstall the package)."
        ) from e

    element_type_by_id = _classify_element_types(inp_path)

    with SwmmOutput(Path(out_path), load_time_series=True) as ep:
        n_periods = ep.n_periods
        step_seconds = int(ep.report_interval.total_seconds()) if ep.report_interval else 1
        node_df = _safe_to_dataframe(ep, "nodes")
        link_df = _safe_to_dataframe(ep, "links")
        sub_df = _safe_to_dataframe(ep, "subcatchments")

    frames = []
    if node_df is not None:
        frames.append(_prepare_role_frame(
            node_df, role="node", metrics=_NODE_METRICS,
            element_type_by_id=element_type_by_id,
            step_seconds=step_seconds,
        ))
    if link_df is not None:
        frames.append(_prepare_role_frame(
            link_df, role="link", metrics=_LINK_METRICS,
            element_type_by_id=element_type_by_id,
            step_seconds=step_seconds,
        ))
    if sub_df is not None:
        frames.append(_prepare_role_frame(
            sub_df, role="subcatchment", metrics=_SUB_METRICS,
            element_type_by_id=element_type_by_id,
            step_seconds=step_seconds,
        ))

    if not frames:
        df = pd.DataFrame(columns=_parquet_schema_columns())
    else:
        df = pd.concat(frames, ignore_index=True, sort=False)

    # Materialize timestamps from period_seconds.
    base = pd.Timestamp(_PERIOD_TS_BASE)
    df["period_ts"] = base + pd.to_timedelta(df["period_seconds"].astype("int64"), unit="s")

    df = _coerce_parquet_types(df)
    table = pa.Table.from_pandas(df, preserve_index=False)

    out_path_local = Path(parquet_path)
    out_path_local.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(out_path_local), **_PARQUET_WRITER_KWARGS)

    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "n_periods": int(n_periods),
        "report_time_step_seconds": step_seconds,
        "node_metrics": list(_NODE_METRICS),
        "link_metrics": list(_LINK_METRICS),
        "sub_metrics": list(_SUB_METRICS),
    }


def _classify_element_types(inp_path: PathLike) -> Dict[str, str]:
    """Map every node/link/subcatchment id → canonical element_type."""
    with SwmmInput(Path(inp_path)) as inp:
        full = inp.to_dict()

    out: Dict[str, str] = {}
    mapping = (
        ("junctions", "junction"),
        ("outfalls", "outfall"),
        ("storage", "storage"),
        ("dividers", "divider"),
        ("conduits", "conduit"),
        ("pumps", "pump"),
        ("orifices", "orifice"),
        ("weirs", "weir"),
        ("outlets", "outlet"),
        ("subcatchments", "subcatchment"),
    )
    for section, element_type in mapping:
        for row in full.get(section, []) or []:
            fid = row.get("id") or row.get("name") or row.get("node")
            if fid:
                out[fid] = element_type
    return out


def _parquet_schema_columns() -> list:
    return [
        "fid", "role", "element_type",
        "period_idx", "period_ts", "period_seconds",
        *_NODE_METRICS,
        *_LINK_METRICS,
        *_SUB_METRICS,
    ]


def _prepare_role_frame(
    df,
    *,
    role: str,
    metrics: Iterable[str],
    element_type_by_id: Dict[str, str],
    step_seconds: int,
):
    """
    Reshape a SwmmOutput MultiIndex DataFrame to the common Parquet schema.

    SwmmOutput.to_dataframe(element_type=<role>) returns a MultiIndex
    DataFrame where the index levels are (timestamp, element_name) and the
    columns are the metric names. We flatten into long rows with added
    fid / role / element_type / period_idx / period_seconds columns.
    """
    import pandas as pd

    metrics = tuple(metrics)
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame(columns=_parquet_schema_columns())

    # Flatten index into columns.
    flat = df.reset_index()

    idx_names = list(df.index.names)
    # Normalize the two level names to canonical "timestamp" + "fid".
    if "element_name" in idx_names:
        flat = flat.rename(columns={"element_name": "fid"})
    elif "name" in idx_names:
        flat = flat.rename(columns={"name": "fid"})
    else:
        # Fall back to positional — assume level 1 is the element name.
        non_time = [c for c in idx_names if c != "timestamp"]
        if non_time:
            flat = flat.rename(columns={non_time[0]: "fid"})

    if "timestamp" in flat.columns:
        ts_col = "timestamp"
    else:
        # Some SwmmOutput versions may name the time level differently.
        time_candidates = [c for c in idx_names if c not in ("element_name", "name", "fid")]
        ts_col = time_candidates[0] if time_candidates else None

    # period_idx: 0-based sequential per distinct timestamp, in order.
    if ts_col is not None:
        # Unique timestamps in first-appearance order.
        unique_ts = pd.Series(flat[ts_col].unique()).reset_index(drop=True)
        ts_to_idx = {t: i for i, t in enumerate(unique_ts)}
        flat["period_idx"] = flat[ts_col].map(ts_to_idx).astype("int32")
    else:
        flat["period_idx"] = 0

    flat["role"] = role
    flat["element_type"] = flat["fid"].map(element_type_by_id).fillna(role)
    flat["period_seconds"] = (flat["period_idx"].astype("int64") * int(step_seconds)).astype("int32")

    # Ensure every expected metric column exists across all roles.
    for m in (*_NODE_METRICS, *_LINK_METRICS, *_SUB_METRICS):
        if m not in flat.columns:
            flat[m] = pd.NA

    return flat


def _coerce_parquet_types(df):
    """Cast columns to the types expected by the file-ingestion-engine."""
    import pandas as pd

    df["fid"] = df["fid"].astype("string")
    df["role"] = df["role"].astype("string")
    df["element_type"] = df["element_type"].astype("string")
    df["period_idx"] = df["period_idx"].astype("int32")
    df["period_seconds"] = df["period_seconds"].astype("int32")
    for col in (*_NODE_METRICS, *_LINK_METRICS, *_SUB_METRICS):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")
    cols = _parquet_schema_columns()
    return df.reindex(columns=cols)


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

    DataFrame index: (timestamp, element_name). Columns are positional
    ``value_0`` … ``value_<M-1>`` from SWMM's binary output, in the
    canonical metric order matching ``_NODE_METRICS`` / ``_LINK_METRICS``
    / ``_SUB_METRICS``. SWMM's ``to_dataframe`` emits rows grouped by
    element with timestamps incrementing within each group, so a per-
    element ``.values`` slab is already in period order — we groupby
    once and copy each slab into the destination cube.

    Missing element_names in the DataFrame stay NaN. Missing tail
    periods (e.g. early-terminated run) stay NaN. Extra metric columns
    beyond ``len(metrics)`` are ignored; missing ones stay NaN.
    """
    import numpy as np

    metrics = list(metrics)
    n = len(ordered_ids)
    m = len(metrics)
    cube = np.full((n, n_periods, m), np.nan, dtype="float64")

    if df is None or getattr(df, "empty", True):
        return cube

    id_to_idx = {fid: i for i, fid in enumerate(ordered_ids)}

    idx_names = df.index.names
    name_lvl = idx_names.index("element_name") if "element_name" in idx_names else 1
    m_in_df = df.shape[1]
    cols_to_copy = min(m_in_df, m)

    # ``sort=False`` keeps SWMM's natural emission order — each group
    # is already (period_0, period_1, …, period_{n_periods-1}) for one
    # element, so .values is shape (n_periods_present, m_in_df) ready
    # to drop into the cube at row id_to_idx[fid].
    for fid, group in df.groupby(level=name_lvl, sort=False):
        i = id_to_idx.get(fid)
        if i is None:
            continue
        vals = group.values
        rows = min(vals.shape[0], n_periods)
        cube[i, :rows, :cols_to_copy] = vals[:rows, :cols_to_copy]
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
