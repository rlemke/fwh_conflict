# UCDP GED Ingest & Core Metrics

**Namespace:** `conflict.sources` ·
**FFL:** `src/conflict/ffl/conflict.ffl` (`DownloadUCDP`) ·
**Handlers:** `src/conflict/handlers/conflict_handlers.py` (`handle_download_ucdp`) ·
**Library:** `src/conflict/_lib.py` (`download_ucdp_aggregate`) ·
**Tests:** `tests/test_conflict.py` (`test_metric_registry`, `test_aliases_are_strings`)

## Overview

This is the **data heart** of the domain: it downloads the Uppsala Conflict Data
Program **Georeferenced Event Dataset (GED)** as a bulk CSV, filters to one year,
and aggregates every conflict event into a compact **per-country** record with the
five UCDP-derivable metrics. Everything downstream (the join and the choropleth in
[map-rendering](map-rendering.md)) reads the small aggregate JSON this feature
caches, not the ~250 MB raw CSV.

It answers "how much armed-conflict activity did each country see in year *N*?"
where activity is measured five ways: events, deaths, civilian targeting, actor
count, and population-normalised intensity.

## How it works

`download_ucdp_aggregate(year=None, force=False)` (`_lib.py`):

1. **Cache check.** Looks for `aggregate-<year|latest>.json` under the conflict
   cache root; if present and `force` is false, loads and returns
   `(blob["year"], blob["countries"])` — re-runs skip the whole download+parse.
2. **Download.** `requests.get(UCDP_GED_URL, timeout=300)` where `UCDP_GED_URL =
   https://ucdp.uu.se/downloads/ged/ged251-csv.zip`. The zip is opened in memory
   (`io.BytesIO`) and the first `*.csv` member is read via `csv.DictReader`
   (`csv.field_size_limit` is raised to 20 MB for the wide rows).
3. **Year selection.** Rows are first tallied by `int(row["year"])`; the target is
   the requested `year`, or `max(years)` — the **latest year present** — when
   `year` is `None`/`0`.
4. **Aggregate.** For every row whose `year == target`, keyed on the `country`
   column, it accumulates the five metrics (see *Data & fields*).
5. **Cache write.** Writes `{"year": target, "countries": {...}}` to
   `aggregate-<...>.json` via the backend-aware `cstore.open_write`.

Data shape: `GED zip → CSV rows → {country: {events, deaths, civilian, actors}}
JSON`. Note the aggregate stores `actors` as an **int** (the set is collapsed to
`len(...)` before serialising); `intensity` is *not* stored here — it is derived at
render time from `deaths` and Natural Earth `POP_EST` (see
[map-rendering](map-rendering.md)).

The `DownloadUCDP` event facet is a thin wrapper: `handle_download_ucdp` calls
`download_ucdp_aggregate` and returns `{"year": year, "country_count":
len(countries)}`. `_yr()` coerces the FFL `year` param so `0`/`""`/`None` all mean
"latest".

## Fan-out

**Single-task — no fan-out.** One global dataset, one aggregation pass; there is no
`foreach`. The whole GED year is parsed in a single process, then cached so the
fleet never re-parses it.

## Data & fields

Read from each GED row and reduced per `country`:

| Metric key | GED source | Rule |
|---|---|---|
| `events` | one per row | `Counter` increment per matching row |
| `deaths` | `best` | `Σ int(row["best"])` (best fatality estimate) |
| `civilian` | `type_of_violence == "3"` | count of one-sided / violence-against-civilians events |
| `actors` | `side_a`, `side_b` | size of the **union of distinct armed group names** |

`METRICS` in `_lib.py` declares the label/format for each (`events`, `deaths`,
`civilian` → `count`; `intensity` → `rate`; `actors` → `count`). The three
`displaced` / `new_displaced` / `food_insecure` entries in the same list are
**overlay** metrics from other datasets — see
[displacement-overlays](displacement-overlays.md) — not produced here.

`COUNTRY_ALIASES` (10 entries) maps UCDP's historical country names
(`"DR Congo (Zaire)"`, `"Russia (Soviet Union)"`, `"Bosnia-Herzegovina"`, …) to the
Natural Earth `NAME` used at join time. The alias map is applied by the *renderer*,
not here — the aggregate keeps UCDP's own country strings.

## External libraries / binaries

- **`requests`** (pip, hard dep) — the GED download; module-level
  `try/except ImportError` sets `requests = None`, and the function raises
  `RuntimeError("requests is required …")` if it is called without it.
- **stdlib** — `zipfile`, `io`, `csv`, `json`, `collections.Counter/defaultdict`.
- **`facetwork.runtime.storage`** via `conflict.storage` — backend-aware
  read/write/exists (see [storage-and-cache](storage-and-cache.md)).
- No binary dependencies.

## Facets & workflows

| Facet | Kind | Effect / Cost / Timeout | Signature → returns |
|---|---|---|---|
| `conflict.sources.DownloadUCDP` | **event** | `external` / `moderate` / 15 min | `(year: Int = 0, force: Boolean = false) => (year: Int, country_count: Int)` |

FFL docstring: *"Download the UCDP GED bulk CSV and cache the per-country aggregate
for a year (`year = 0` → the latest year in the dataset). The public UCDP API needs
a token; the bulk zip does not."* `country_count` here is the number of UCDP
countries in the aggregate — distinct from `BuildConflictMap`'s `country_count`,
which is the number of **matched** map features (see Gotchas in
[map-rendering](map-rendering.md)).

## Cache / output

- **Cache:** `aggregate-<year|latest>.json` under `cache_root()` — on the fleet
  `s3://afl-cache/cache/conflict/cache/`, locally `<FW_DATA_ROOT>/conflict-cache/`.
- **Output:** none directly; this facet produces only the cached aggregate. The
  rendered artifacts belong to [map-rendering](map-rendering.md).
- `force=true` bypasses the cache and re-downloads/re-parses.

## Gotchas & notes

- **The dataset version is pinned in the URL** (`ged251-csv.zip`). A new UCDP GED
  release means editing `UCDP_GED_URL`; there is no auto-discovery of the latest
  release file.
- **Bulk zip, not the API.** The public UCDP API requires a token; the bulk zip is
  open. Do not switch to the API expecting the same access.
- **`year=0` means "latest in this file"**, which is the newest year the *pinned*
  zip contains — not necessarily the current calendar year.
- **250 MB parse.** The first run reads the entire CSV into memory (`list(...)`).
  This is why the 15-minute timeout and the aggressive aggregate cache exist; keep
  `force` off for routine re-runs.
- **`best` is the "best" fatality estimate** — UCDP also ships `low`/`high`; only
  `best` is summed here.

## Related specs

- [map-rendering](map-rendering.md) — consumes this aggregate, computes
  `intensity`, joins onto geometry, and renders the choropleth.
- [displacement-overlays](displacement-overlays.md) — the three non-UCDP overlay
  metrics joined alongside these five.
- [storage-and-cache](storage-and-cache.md) — where and how the aggregate is
  cached.
- [workflow-and-handlers](workflow-and-handlers.md) — how `DownloadUCDP` is wired
  and sequenced before the map step.
