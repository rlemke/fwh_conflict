# fwh_conflict — Facetwork conflict-maps domain

UCDP armed-conflict world maps. Aggregates the Uppsala Conflict Data Program's
Georeferenced Event Dataset (GED) by country and renders a MapLibre world
choropleth with a metric dropdown:

- Conflict events (events/year)
- Conflict deaths (fatalities/year)
- Civilian targeting (one-sided violence events)
- Conflict intensity (deaths per 100,000 population)
- Armed actor count (distinct armed groups)

Plus three humanitarian overlays joined by ISO3: displaced population (UNHCR), new
conflict displacements (IDMC), and food insecurity (IPC Phase 3+).

## FFL at a glance

The domain is driven from [FFL](https://github.com/rlemke/facetwork/blob/main/docs/reference/language/grammar.md),
Facetwork's workflow language. A step is `name = Facet(args)`, and later steps
reference earlier ones as `step.field`:

```ffl
namespace my.conflict {

    use conflict.sources
    use conflict.maps

    /** Download the UCDP aggregate for a year, then render the world map. */
    workflow ConflictYear(year: Int = 2023) => (status: String, html_path: String) andThen {

        ucdp = conflict.sources.DownloadUCDP(year = $.year)

        map = conflict.maps.BuildConflictMap(year = $.year) after ucdp

        yield ConflictYear(status = "completed", html_path = map.html_path)
    }
}
```

```bash
fw ffl run --primary my.ffl --library src/conflict/ffl/conflict.ffl \
  --workflow my.conflict.ConflictYear --inputs '{"year": 2023}'
```

📖 **[docs/ffl-examples.md](docs/ffl-examples.md)** — the full example gallery:
sweeping several years in parallel with `foreach`, call-time mixins
(timeout/retry), `catch`, `when` branching, wrapping the shipped workflow, and
cross-domain composition (publishing). Every snippet there is compile-checked.

## Feature specifications

Per-feature docs live in [`docs/`](docs/README.md) (one spec per feature, common
shape). Start with the flagship [map-rendering](docs/map-rendering.md).

| Spec | What it covers |
|------|----------------|
| [ucdp-ingest](docs/ucdp-ingest.md) | UCDP GED download + per-country aggregation; the 5 core metrics; `DownloadUCDP`, caching, country aliases. |
| [displacement-overlays](docs/displacement-overlays.md) | UNHCR / IDMC / IPC overlay metrics, fetched in the map step and joined by ISO3. |
| [map-rendering](docs/map-rendering.md) | **Flagship.** `BuildConflictMap`: join onto Natural Earth geometry, intensity normalisation, the MapLibre choropleth. |
| [workflow-and-handlers](docs/workflow-and-handlers.md) | The `BuildConflictWorldMap` workflow, two-facet dispatch/registration, `DomainPackage` discovery. |
| [storage-and-cache](docs/storage-and-cache.md) | Backend-aware `storage.py`: local vs MinIO/S3 roots, cache/output layout, override env vars. |

Full index + section shape: [`docs/README.md`](docs/README.md).

Run: `fw ffl run --primary src/conflict/ffl/conflict.ffl --workflow conflict.workflows.BuildConflictWorldMap --task-list conflict`
