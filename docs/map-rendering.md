# Choropleth Join & Map Rendering

**Namespace:** `conflict.maps` ·
**FFL:** `src/conflict/ffl/conflict.ffl` (`BuildConflictMap`) ·
**Handlers:** `src/conflict/handlers/conflict_handlers.py` (`handle_build_conflict_map`) ·
**Library:** `src/conflict/_lib.py`
(`build_conflict_map`, `_world_geojson`, `_render_html`, and the `_search_*` /
`_modal_*` / `_attribution` helpers) ·
**Tests:** `tests/test_conflict.py` (`test_render_html_from_synthetic_aggregate`)

## Overview

This is the **flagship** feature — the deliverable is the interactive world map. It
takes the cached UCDP aggregate ([ucdp-ingest](ucdp-ingest.md)) plus the three
overlay datasets ([displacement-overlays](displacement-overlays.md)), joins them
onto **Natural Earth** country polygons, derives population-normalised intensity,
and renders a **self-contained MapLibre GL choropleth** with a metric dropdown,
country search, an "About this data" modal, a live legend, and a provenance footer.
Output is a single `index.html` (plus the joined `conflict.geojson`) written to the
conflict output root.

## How it works

`build_conflict_map(year=None, force=False)` (`_lib.py`):

1. **Gather inputs** — `download_ucdp_aggregate` (5 core metrics),
   `download_unhcr_displacement`, `download_idmc_new_displacements`,
   `download_ipc_food_insecurity` (3 overlays), and `_world_geojson()` (Natural
   Earth `ne_110m_admin_0_countries`, itself cached as `world-countries.geojson`).
2. **Join, per NE feature:**
   - **UCDP by name** — `countries.get(props["NAME"])`, falling back to a scan of
     `COUNTRY_ALIASES` (UCDP historical name → NE `NAME`).
   - **Overlays by ISO3** — `ISO_A3`, or `ADM0_A3` when `ISO_A3` is `-99`.
   - Sets `m_events`, `m_deaths`, `m_civilian`, `m_actors` from the UCDP record;
     computes `m_intensity = round(deaths / POP_EST * 100000, 2)` when `POP_EST > 0`;
     sets `m_displaced` / `m_new_displaced` / `m_food_insecure` from the overlay
     dicts. Every feature's props are rewritten to `{NAME, POP_EST, m_*}` (raw NE
     props are dropped to keep the embedded GeoJSON small).
   - `matched` counts features that hit a UCDP record — returned as
     `country_count`.
3. **Render** — `_render_html(fc, year)` produces the HTML; both the GeoJSON and the
   HTML are written via `cstore.open_write`.

Data shape: `aggregate JSON + overlay JSON + NE GeoJSON → joined FeatureCollection →
MapLibre HTML`.

The `BuildConflictMap` event facet (`handle_build_conflict_map`) returns
`{html_path, geojson_path, year, country_count}`.

## Fan-out

**Single-task — no fan-out.** One world FeatureCollection is joined and rendered in
a single pass; there is no `foreach`. The map is atomic — a partial world map is not
useful — so the render is deliberately one step.

## Data & fields

- **Geometry:** Natural Earth 110m admin-0 countries (`WORLD_GEOJSON_URL`), props
  `NAME`, `POP_EST`, `ISO_A3`, `ADM0_A3`.
- **Output feature props:** `NAME`, `POP_EST`, and the eight metric keys `m_events`,
  `m_deaths`, `m_civilian`, `m_intensity`, `m_actors`, `m_displaced`,
  `m_new_displaced`, `m_food_insecure` (each an int, or `None` for no-data).
- **Color scale:** `RAMP` — a five-stop **YlOrRd** ramp (`#ffffb2` → `#bd0026`),
  "light → dark = worse"; `NODATA = #e0e0e0`. Colours are computed **client-side** by
  a MapLibre `interpolate` expression linearly stretched between the min and max of
  the currently selected metric's positive values (`colorExpr`); values `< 1` or
  `null` render as `NODATA`.

## External libraries / binaries

- **`requests`** (pip) — Natural Earth geometry + the overlay fetches (delegated).
- **`facetwork.runtime.storage`** via `conflict.storage` — writing `conflict.geojson`
  and `index.html` to local disk or MinIO/S3.
- **stdlib** `json` / `html.escape` / `datetime` — serialisation, HTML escaping,
  timestamp in the footer.
- **Client-side (CDN, referenced by the HTML, not a Python dep):**
  `maplibre-gl@4.7.1` (JS + CSS from unpkg) and CARTO Voyager raster basemap tiles.
- No binary dependencies.

## Facets & workflows

| Facet | Kind | Effect / Cost / Timeout | Signature → returns |
|---|---|---|---|
| `conflict.maps.BuildConflictMap` | **event** | `io` / `cheap` / 10 min | `(year: Int = 0, dependency_signal: Int = 0) => (html_path: String, geojson_path: String, year: Int, country_count: Int)` |

FFL docstring: *"Join the cached UCDP aggregate onto Natural Earth country geometry,
normalise intensity by population, and render the world choropleth.
`dependency_signal` sequences this strictly after the download."* The
`dependency_signal` param carries no data — the workflow passes `ucdp.country_count`
into it purely to force ordering (see [workflow-and-handlers](workflow-and-handlers.md)).

## Cache / output

- **Cache (read):** `world-countries.geojson` under `cache_root()` (the NE geometry,
  fetched once then reused).
- **Output (write):** to `output_root()` — on the fleet
  `s3://afl-cache/cache/conflict/output/`, locally `<FW_DATA_ROOT>/conflict-output/`:
  - `conflict.geojson` — the joined world FeatureCollection (compact separators).
  - `index.html` — the standalone MapLibre map (all data inlined as a JS `DATA`
    literal; no server needed).

## Gotchas & notes

- **Two different `country_count`s.** `DownloadUCDP` returns the number of UCDP
  countries in the aggregate; `BuildConflictMap` returns `matched` — NE features that
  found a UCDP record. They will not be equal (UCDP names that never match a NE
  polygon are dropped; that is exactly what `COUNTRY_ALIASES` narrows).
- **Name join is brittle by design.** UCDP joins by country *name*; the 10-entry
  `COUNTRY_ALIASES` covers the historical/spelling mismatches (`Côte d'Ivoire`,
  `Dem. Rep. Congo`, `S. Sudan`, …). A UCDP name outside that map with a different NE
  spelling silently won't shade — extend `COUNTRY_ALIASES` when adding coverage.
- **Intensity needs a positive `POP_EST`.** NE puts `POP_EST` on features; where it
  is missing or `≤ 0`, `m_intensity` is `None` (rendered grey), not `0`.
- **Raw NE properties are discarded** in the output GeoJSON — only `NAME`, `POP_EST`
  and the `m_*` keys survive, so any downstream consumer of `conflict.geojson`
  should not expect ISO codes or other NE attributes.
- **Self-contained but CDN-dependent at view time.** The HTML inlines all data but
  loads MapLibre + basemap tiles from unpkg/CARTO; it needs network to render in a
  browser (offline it shows a blank map).
- **The `_search_*` / `_modal_*` helpers return plain strings** interpolated into the
  `_render_html` f-string; their `{...}` are literal JS/CSS braces, not f-string
  fields — do not "fix" them into doubled braces.

## Related specs

- [ucdp-ingest](ucdp-ingest.md) — supplies the aggregate and the five core metrics.
- [displacement-overlays](displacement-overlays.md) — supplies the three ISO3-joined
  overlay metrics.
- [storage-and-cache](storage-and-cache.md) — where `conflict.geojson` / `index.html`
  are written.
- [workflow-and-handlers](workflow-and-handlers.md) — how this facet is sequenced
  after `DownloadUCDP`.
