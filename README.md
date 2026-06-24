# fwh_conflict — Facetwork conflict-maps domain

UCDP armed-conflict world maps. Aggregates the Uppsala Conflict Data Program's
Georeferenced Event Dataset (GED) by country and renders a MapLibre world
choropleth with a metric dropdown:

- Conflict events (events/year)
- Conflict deaths (fatalities/year)
- Civilian targeting (one-sided violence events)
- Conflict intensity (deaths per 100,000 population)
- Armed actor count (distinct armed groups)

Run: `fw ffl run --primary src/conflict/ffl/conflict.ffl --workflow conflict.workflows.BuildConflictWorldMap --task-list conflict`
