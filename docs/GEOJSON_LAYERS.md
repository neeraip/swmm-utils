# SWMM GeoJSON layer schema

`swmm_utils.exports.emit_geojson_layers(inp_path, crs)` is the canonical
SWMM `.inp` → spatial-layer parser. It returns one layer spec per
HydraulicModel role; each spec wraps a GeoJSON `FeatureCollection`
whose feature properties follow the schema below.

This document is the contract the producer (this lib) and the consumers
(NEER's lambda-importer, Console attribute table, results-coloring
pipeline) agree on. Adding a property is non-breaking; renaming or
removing one is.

## Layer specs returned

```python
[
  {
    "name": str,             # capitalized layer name ("Junctions")
    "role": str,             # HydraulicModelRole token ("junction")
    "geometry_type": str,    # "Point" | "LineString" | "Polygon"
    "crs": str | None,       # caller-supplied (e.g. "EPSG:2882")
    "feature_collection": {
      "type": "FeatureCollection",
      "features": [...],
    },
  },
  ...
]
```

`role` ↔ `name` mapping (`LAYER_ROLE_MAP`):

| name | role | geometry |
|---|---|---|
| Junctions | junction | Point |
| Outfalls | outfall | Point |
| Storage | storage | Point |
| Dividers | divider | Point |
| Conduits | conduit | LineString |
| Pumps | pump | LineString |
| Orifices | orifice | LineString |
| Weirs | weir | LineString |
| Outlets | outlet | LineString |
| Subcatchments | subcatchment | Polygon |

Empty roles are omitted from the returned list. `Subcatchments` is
emitted whenever the model declared any subcatchments, even if every
one was dropped — keeps the layer schema consistent across imports.

## Feature `id`

Each feature's top-level `id` is the SWMM element name (the `name`
column of the source section). MapLibre `promoteId="name"` lets
feature-state attached by element name flow through PMTiles.

## Properties — by role

Every feature's `properties` dict is the source-section row plus any
applicable cross-references. Source-section column names match the
SWMM 5.2 `.inp` spec exactly (lowercase). Cross-reference keys carry a
prefix (`xsection_`, `loss_`, `dwf_`, `inflow_`, `infil_`, `coverage_`,
`lid_`) so consumers can group/filter without ambiguity.

### junction

```jsonc
{
  "name": "J1",
  "elevation":     "100",   // [JUNCTIONS] columns
  "max_depth":     "10",
  "init_depth":    "0",
  "surcharge_depth": "0",
  "ponded_area":   "0",

  "tag":           "...",   // [TAGS] (when present)

  // [INFLOWS] FLOW row (multi-row sections collapsed)
  "inflow_constituent":      "FLOW",
  "inflow_timeseries":       "...",
  "inflow_type":             "FLOW",
  "inflow_mfactor":          0,
  "inflow_sfactor":          0,
  "inflow_baseline":         0,
  "inflow_baseline_pattern": "...",

  // [DWF] FLOW row
  "dwf_constituent": "FLOW",
  "dwf_value":       0,
  "dwf_pattern1":    "...",
  "dwf_pattern2":    "...",
  "dwf_pattern3":    "...",
  "dwf_pattern4":    "...",
}
```

### outfall / storage / divider

`[OUTFALLS]` / `[STORAGE]` / `[DIVIDERS]` columns + the same
`tag` / `inflow_*` / `dwf_*` cross-refs as junction.

### conduit

```jsonc
{
  "name":      "C1",
  "from_node": "J1",
  "to_node":   "J2",
  "length":    "100",     // [CONDUITS]
  "roughness": "0.013",
  "in_offset": "0",
  "out_offset": "0",
  "init_flow": "0",
  "max_flow":  "0",

  "tag": "...",

  // [XSECTIONS] — every column except `link`/`name`, prefixed.
  "xsection_shape":   "CIRCULAR",
  "xsection_geom1":   "1",
  "xsection_geom2":   "0",
  "xsection_geom3":   "0",
  "xsection_geom4":   "0",
  "xsection_barrels": "1",

  // [LOSSES]
  "loss_inlet":     "0",
  "loss_outlet":    "0",
  "loss_average":   "0",
  "loss_flap_gate": "NO",
  "loss_seepage":   "0",
}
```

### pump / orifice / weir / outlet

Same shape as conduit (link geometry, `from_node`/`to_node`,
`tag`/`xsection_*`/`loss_*` cross-refs). Each section's columns are
preserved verbatim plus the cross-refs.

### subcatchment

```jsonc
{
  "name":         "S1",
  "raingage":     "RG1",   // [SUBCATCHMENTS]
  "outlet":       "J1",
  "area":         "10",
  "imperv":       "50",
  "width":        "100",
  "slope":        "1",
  "curb_length":  "0",
  "snowpack":     "...",   // optional column

  "tag": "...",

  // [SUBAREAS] — every column except `subcatchment`/`name`.
  "n_imperv": "0.01",
  "n_perv":   "0.1",
  "s_imperv": "0.05",
  "s_perv":   "0.05",
  "pct_zero": "25",
  "route_to": "OUTLET",
  "pct_routed": "100",

  // [INFILTRATION] (decoder writes the section as `infiltrations`).
  "infil_param1": "...",
  "infil_param2": "...",
  // ...

  // [COVERAGES] — collapsed to the dominant landuse plus a count.
  "coverage_dominant_landuse": "RES",
  "coverage_dominant_pct":     0.6,
  "coverage_count":            3,

  // [LID_USAGE] — collapsed.
  "lid_count":         2,
  "lid_first_control": "BIO_RETENTION",
  "lid_total_area":    50.0,
}
```

## Polygon fallback

Subcatchments without a `[POLYGONS]` boundary fall back to a small
synthesized square centered on their outlet, sized as 0.05% of the
model's coordinate extent. They appear in the layer with full
attributes but the geometry is an approximation — UI / styling should
not infer area or shape from it.

Subcatchments with no resolvable outlet are silently dropped (no
spatial reference to anchor on).

## Stability guarantees

- Property names are stable. Adding a new property is non-breaking;
  renaming or removing one is breaking.
- Cross-reference prefixes (`xsection_`, `loss_`, `dwf_`, etc.) are
  stable.
- Column values are emitted as **strings** (matching the source `.inp`
  text). Cross-reference numeric summaries (e.g. `coverage_dominant_pct`,
  `lid_total_area`, `dwf_value`) are emitted as numbers via `_sf()` —
  `null` if the source value can't coerce.
- Geometry coordinate values are passed through verbatim from the
  source `.inp`'s coordinate sections — no reprojection happens here.
  The caller is responsible for honoring `crs`.
