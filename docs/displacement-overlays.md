# Displacement & Food-Insecurity Overlays

**Namespace:** `conflict.maps` (fetched inside `BuildConflictMap`) ·
**FFL:** `src/conflict/ffl/conflict.ffl` (`BuildConflictMap`) ·
**Library:** `src/conflict/_lib.py`
(`download_unhcr_displacement`, `download_idmc_new_displacements`,
`download_ipc_food_insecurity`) ·
**Tests:** `tests/test_conflict.py` (`test_render_html_from_synthetic_aggregate`)

## Overview

Beyond the five UCDP conflict metrics, the map carries **three humanitarian overlay
metrics** joined from independent open datasets, so a viewer can flip from "where is
the fighting" to "where are the people it displaced" on the same choropleth:

- **`displaced`** — forced-displacement burden (refugees fled + IDPs remaining) from **UNHCR**.
- **`new_displaced`** — new conflict displacements this year from **IDMC** (GIDD).
- **`food_insecure`** — population in **IPC** Phase 3+ (crisis or worse), a current snapshot.

These are declared as the last three entries of `METRICS` in `_lib.py` and appear as
extra options in the map's metric dropdown, but they originate outside UCDP and join
by **ISO3**, not by country name.

## How it works

All three are downloaded **inside `build_conflict_map`** (not by the `DownloadUCDP`
source facet), each cached independently:

1. **UNHCR** — `download_unhcr_displacement(year)` pages the UNHCR population
   endpoint (`UNHCR_URL`, `coo_all=true`, `limit=1000`), following `maxPages`, and
   sums `refugees + idps` per **country of origin** `coo_iso`. Result:
   `{ISO3: int}`.
2. **IDMC** — `download_idmc_new_displacements(year)` GETs the GIDD bulk **xlsx**
   export (`IDMC_EXPORT_URL`, public `client_id=IDMCWSHSOLO009`) for
   `start_year=end_year=year`, opens it with `openpyxl` (imported **lazily**), and
   reads the `Conflict Internal Displacements` column keyed by the `ISO3` column.
   Result: `{ISO3: int}`.
3. **IPC** — `download_ipc_food_insecurity()` GETs the open HDX CSV (`IPC_CSV_URL`),
   keeping rows where `Phase == "3+"` and `Validity period == "current"`, mapping
   `Country` (an ISO3) → `Number`. **Not year-specific** — a current snapshot.
   Result: `{ISO3: int}`.

At join time each Natural Earth feature's ISO3 (`ISO_A3`, falling back to
`ADM0_A3` when `ISO_A3` is `-99`, e.g. France/Norway) indexes the three dicts to set
`m_displaced` / `m_new_displaced` / `m_food_insecure`. A country with no entry gets
`None` (rendered as no-data grey).

## Fan-out

**Single-task — no fan-out.** Each overlay is one (possibly paginated) HTTP fetch
folded into the single `BuildConflictMap` step.

## Data & fields

| Metric key | Source | Join key | Field logic |
|---|---|---|---|
| `m_displaced` | UNHCR population API | `coo_iso` → NE ISO3 | `Σ (refugees + idps)` per country of origin |
| `m_new_displaced` | IDMC GIDD xlsx export | `ISO3` column → NE ISO3 | `Σ "Conflict Internal Displacements"` for the year |
| `m_food_insecure` | IPC global HDX CSV | `Country` (ISO3) → NE ISO3 | `Number` where `Phase == "3+"` and current |

All three join by **ISO3**, in contrast to the UCDP metrics which join by country
**name** (+ `COUNTRY_ALIASES`). The renderer resolves ISO3 once per feature and
reuses it for all three overlays.

## External libraries / binaries

- **`requests`** (pip) — all three downloads.
- **`openpyxl`** (pip, declared in `pyproject.toml` `dependencies`) — parsing the
  IDMC `.xlsx` export; **imported lazily** inside `download_idmc_new_displacements`
  so the rest of the pipeline doesn't pay for it.
- **stdlib** `csv` / `io` / `json` for UNHCR + IPC.
- No binary dependencies.

## Facets & workflows

These overlays have **no dedicated facet** — they are pure library functions called
from within `handle_build_conflict_map` → `build_conflict_map`. The only facet
involved is `conflict.maps.BuildConflictMap` (see
[map-rendering](map-rendering.md)); there is no separate "download overlays" event
facet, so a fresh map run fetches (or cache-hits) all three every time.

## Cache / output

Each overlay caches a small JSON under `cache_root()`:

- `unhcr-displacement-<year>.json`
- `idmc-new-displacements-<year>.json`
- `ipc-food-insecurity.json` (no year — current snapshot)

`force=true` on `build_conflict_map` re-fetches all three. Values land in the output
`conflict.geojson` / `index.html` as `m_*` properties (see
[map-rendering](map-rendering.md)).

## Gotchas & notes

- **Fetched by the map step, not the source step.** `DownloadUCDP` only handles
  UCDP; the overlays ride inside `BuildConflictMap`. A run that reuses a cached UCDP
  aggregate still hits UNHCR/IDMC/IPC unless *their* caches exist too.
- **Public-but-unversioned endpoints.** The IDMC `client_id` is IDMC's own public
  client used in their HDX records; the IPC HDX resource URL is pinned. If either
  endpoint moves, that overlay silently returns `{}` only if the request *succeeds*
  with no matching rows — a network error raises and fails the step instead.
- **IPC is not year-aligned** with the others. It is the latest "current" analysis,
  so `food_insecure` may reflect a different period than the map's `year`. This is
  documented in the map's "About this data" text.
- **ISO3 join misses** for a handful of NE features (`-99` ISO_A3) are handled by
  the `ADM0_A3` fallback; anything still unmatched is left `None`.
- **`coo_all=true` counts country-of-origin**, i.e. displacement *from* a country,
  not asylum *into* it — deliberately, so the overlay lines up with where conflict
  occurs.

## Related specs

- [map-rendering](map-rendering.md) — performs the ISO3 join and renders these three
  as extra dropdown metrics.
- [ucdp-ingest](ucdp-ingest.md) — the five core (name-joined) metrics these overlay.
- [storage-and-cache](storage-and-cache.md) — the per-overlay cache files.
