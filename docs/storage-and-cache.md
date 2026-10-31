# Backend-Aware Storage, Cache & Output Layout

**Module:** `src/conflict/storage.py` (imported as `cstore` in `_lib.py`) ·
**Backs:** every download/aggregate/render in [ucdp-ingest](ucdp-ingest.md),
[displacement-overlays](displacement-overlays.md), [map-rendering](map-rendering.md)

## Overview

A thin, **backend-aware** I/O layer so the same code path works for terminal runs
(local disk) and fleet runs (MinIO/S3). Since September 2026 the module is a shim
over the shared `facetwork.domains.storage` (`domain_storage("conflict")`), which
owns the behaviour for most `fwh_*` repos; this file keeps the import path and the
public names `_lib` uses (including the private `_data_root`). It gives `_lib` a small vocabulary —
`cache_root()`, `output_root()`, `join`, `exists`, `open_read`, `open_write`,
`localize` — so no `_lib` function ever branches on the storage backend itself. The
layout arguments pin where this domain's data already sits in the object store —
changing them orphans the cache rather than moving it.

## How it works

- **Root resolution** — `data_root()` (alias `_data_root`) returns `FW_DATA_ROOT` if set, else
  `get_output_base()`. `is_remote(path)` is simply `"://" in path`.
- **`cache_root()`** — remote: `<root>/cache/conflict/cache`; local:
  `<root>/conflict-cache`. Overridable with `FW_CONFLICT_CACHE_DIR` (the shared
  layer derives `FW_<DOMAIN>_CACHE_DIR` / `_OUTPUT_DIR` from the domain name).
- **`output_root()`** — remote: `<root>/cache/conflict/output`; local:
  `<root>/conflict-output`. Overridable with `FW_CONFLICT_OUTPUT_DIR`.
- **`exists(path)`** — delegates to `get_storage_backend(path).exists(path)`.
- **`open_read`** — `localize()`s a remote object to a local temp path first, then
  opens it normally.
- **`open_write`** (context manager) — local: `makedirs` + open in place; remote:
  write to a `tempfile`, then on close copy the bytes into the backend
  (`get_storage_backend(path).open(path, "wb")`). This is the **stage-local,
  finalize-on-close** pattern object stores require (no partial writes).

## Fan-out

Not applicable — a support module, not a facet. (One line, so the heading isn't
dropped silently.)

## Data & fields

The concrete files this layer holds, all under `cache_root()` unless noted:

| File | Written by | Contents |
|---|---|---|
| `aggregate-<year>.json` | `download_ucdp_aggregate` | `{year, countries:{name:{events,deaths,civilian,actors}}}` — keyed on the resolved year |
| `aggregate-latest.pointer.json` | `download_ucdp_aggregate` | `{year, resolved_at}` — which year was newest; expires after 7 days |
| `world-countries.geojson` | `_world_geojson` | Natural Earth 110m admin-0 countries |
| `unhcr-displacement-<year>.json` | `download_unhcr_displacement` | `{ISO3: refugees+idps}` |
| `idmc-new-displacements-<year>.json` | `download_idmc_new_displacements` | `{ISO3: new conflict displacements}` |
| `ipc-food-insecurity.json` | `download_ipc_food_insecurity` | `{ISO3: IPC Phase 3+ population}` |
| `conflict.geojson` | `build_conflict_map` | joined world FeatureCollection (**`output_root()`**) |
| `index.html` | `build_conflict_map` | the MapLibre choropleth (**`output_root()`**) |

## External libraries / binaries

- **`facetwork.domains.storage`** — `domain_storage`, `join`, `is_remote`; it in turn
  uses `facetwork.runtime.storage` (backends, `localize`, the runtime's single S3
  client) and `facetwork.config.get_output_base` (the default data root).
- No binary dependencies.

## Cache / output

This *is* the cache/output layer. On the fleet everything roots at
`s3://afl-cache/cache/conflict/` (`cache/` for inputs, `output/` for artifacts); on a
laptop it roots at `<FW_DATA_ROOT>/conflict-cache` and `<FW_DATA_ROOT>/conflict-output`.
The published map is `output/index.html` in MinIO (as the FFL header notes).

## Gotchas & notes

- **Local vs remote path shapes differ.** Remote uses a nested `cache/conflict/…`
  layout; local uses flat `conflict-cache` / `conflict-output` dirs. Don't assume one
  when debugging on the other.
- **`open_write` finalizes on close for remote paths** — if the writing block raises,
  the temp file is unlinked and nothing lands in the backend (no half-written
  object). Good for atomicity; means a crashed render leaves no partial `index.html`.
- **Overrides are per-purpose.** `FW_CONFLICT_CACHE_DIR` / `FW_CONFLICT_OUTPUT_DIR`
  fully replace the computed root (bypassing the local/remote branch), while
  `FW_DATA_ROOT` shifts both.
- **Cache keys are not namespaced by dataset version.** `aggregate-<year>.json`
  survives a UCDP version bump (and the latest pointer for up to 7 days) — pass
  `force=true` (or clear the cache) after changing `UCDP_GED_URL`.

## Related specs

- [ucdp-ingest](ucdp-ingest.md), [displacement-overlays](displacement-overlays.md),
  [map-rendering](map-rendering.md) — the producers/consumers of these files.
- [workflow-and-handlers](workflow-and-handlers.md) — the runtime that invokes them.
