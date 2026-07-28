# Conflict Maps — Feature Specifications

This directory holds one **spec per feature** of the `conflict` domain (UCDP
armed-conflict world choropleth: 5 metrics + displacement overlays). Each document
follows a common shape ([`SPEC_TEMPLATE.md`](SPEC_TEMPLATE.md)) and states, for that
feature: how it works, whether it **fans out** (it doesn't — this is a single-task
world-map pipeline), what **data & fields** it reads and how it **joins** them, the
**external libraries** it relies on, its **facets & workflows**, and its
**cache/output**. Claims are grounded in the FFL `/** … */` docstrings, the handler
code (`conflict_handlers.py`), and the library (`_lib.py` / `storage.py`) — the
source of truth for each facet remains its FFL docstring; these specs are the
feature-level narrative over them.

**Start here:** [**Choropleth Join & Map Rendering**](map-rendering.md) — the
flagship feature (the interactive world map is the deliverable) and the deepest
write-up.

## Data ingest & sources

| Spec | What it covers |
|------|----------------|
| [ucdp-ingest.md](ucdp-ingest.md) | UCDP GED bulk-CSV download + per-country aggregation; the 5 core metrics (events, deaths, civilian targeting, actors, intensity); `DownloadUCDP`, caching, `COUNTRY_ALIASES`. |
| [displacement-overlays.md](displacement-overlays.md) | The 3 humanitarian overlay metrics — UNHCR (displaced), IDMC (new conflict displacements), IPC (food insecurity) — fetched inside the map step and joined by ISO3. |

## Visualization

| Spec | What it covers |
|------|----------------|
| [map-rendering.md](map-rendering.md) | **Flagship.** `BuildConflictMap`: join onto Natural Earth geometry, population-normalised intensity, and the self-contained MapLibre choropleth (metric dropdown, country search, About modal, legend, provenance footer). |

## Composition & runtime

| Spec | What it covers |
|------|----------------|
| [workflow-and-handlers.md](workflow-and-handlers.md) | The `BuildConflictWorldMap` workflow (download → build, `dependency_signal` sequencing), the two-facet dispatch/registration, and `DomainPackage` discovery. |
| [ffl-examples.md](ffl-examples.md) | **Usage patterns.** A gallery of complete, compile-checked FFL examples over these facets — minimal workflow, `foreach` year sweeps, call-time mixins, `catch`, `when`, and cross-domain composition. |
| [storage-and-cache.md](storage-and-cache.md) | Backend-aware `storage.py`: local vs MinIO/S3 roots, the cache/output filenames, stage-local finalize-on-close, and the override env vars. |

---

*See also the repo [`README.md`](../README.md) (run command + metric list) and the
package entry point `conflict:domain` (`src/conflict/__init__.py`). The
live/queryable interface is the MCP `fw_capabilities` / `fw_describe_handler` tools.*
