# Workflow, Facet Surface & Handler Wiring

**Namespace:** `conflict.workflows` (+ `conflict.sources`, `conflict.maps`) ·
**FFL:** `src/conflict/ffl/conflict.ffl` ·
**Handlers:** `src/conflict/handlers/{__init__,conflict_handlers}.py` ·
**Package:** `src/conflict/__init__.py` (the `DomainPackage`) ·
**Tests:** `tests/test_conflict.py` (`test_dispatch_keys`, `test_register_handlers`)

## Overview

This spec covers the **composition and runtime plumbing** that ties the two data
features together: the single `BuildConflictWorldMap` workflow, the facet surface it
uses, how handlers are dispatched/registered, and how the package is discovered by a
Facetwork runner. It is the "how does this actually run on the fleet" spec.

## How it works

**The workflow** (`conflict.workflows.BuildConflictWorldMap`) is a two-step
`andThen`:

```
ucdp = DownloadUCDP(year = $.year)
map  = BuildConflictMap(year = $.year)
yield BuildConflictWorldMap(status = "completed", html_path = map.html_path,
                            year = map.year, country_count = map.country_count)
```

`DownloadUCDP` caches the aggregate; `BuildConflictMap` joins + renders. No value
flows between them — the map reads the cache the download wrote — so the compiler
cannot see the dependency and the workflow states it with `after ucdp`, which is
exactly what the `after` clause is for. The workflow yields
`status/html_path/year/country_count`.

**Dispatch** (`conflict_handlers.py`): a flat `_DISPATCH` dict maps the two fully
qualified facet names to their functions:

- `conflict.sources.DownloadUCDP` → `handle_download_ucdp`
- `conflict.maps.BuildConflictMap` → `handle_build_conflict_map`

`handle(payload)` looks up `payload["_facet_name"]` and raises
`ValueError("Unknown facet: …")` on a miss. Both handlers pull the optional
`_step_log` callback from params and emit a `success`/`error` line, re-raising on
failure (no silent empty-default returns).

**Registration** has two entry points, both driven by `_DISPATCH`:

- `register_handlers(runner)` — RegistryRunner path; registers each facet with
  `module_uri=file://…conflict_handlers.py`, `entrypoint="handle"`.
- `register_poller(poller)` — AgentPoller path; `poller.register(facet, fn)`.

`handlers/__init__.py` re-exports these as `register_all_registry_handlers` /
`register_all_handlers`.

**Package discovery** (`conflict/__init__.py`): a module-level
`domain = DomainPackage(name="conflict", ffl_dir=…/ffl,
register_handlers=register_all_registry_handlers)`, exposed via the
`pyproject.toml` entry point `[project.entry-points."facetwork.domains"] conflict =
"conflict:domain"`. A runner started with `--domain conflict` finds this, loads the
FFL from `ffl_dir`, and registers the two handlers.

## Fan-out

**Single-task workflow — no fan-out.** Two sequential steps, one execution; there is
no `foreach` anywhere in the FFL.

## Data & fields

The workflow surface: input `year: Int = 0` (0 → latest); output
`(status: String, html_path: String, year: Int, country_count: Int)`. The two facet
signatures are detailed in [ucdp-ingest](ucdp-ingest.md) and
[map-rendering](map-rendering.md). No filtering happens at this layer — it is pure
composition.

## External libraries / binaries

- **`facetwork.domains.DomainPackage`** — the discovery/registration contract.
- No other dependencies at this layer; the handlers delegate all real work to
  `_lib` (see the data-feature specs).

## Facets & workflows

| Facet / Workflow | Kind | Effect / Cost / Timeout | Purpose |
|---|---|---|---|
| `conflict.workflows.BuildConflictWorldMap` | **workflow** | — | Entry point; download → build, yields status + `html_path`. |
| `conflict.sources.DownloadUCDP` | event | `external` / `moderate` / 15 min | Cache the UCDP per-country aggregate. |
| `conflict.maps.BuildConflictMap` | event | `io` / `cheap` / 10 min | Join + render the choropleth. |

Both event facets need a handler; the workflow is orchestration only. All three are
declared in the single `conflict.ffl`; the `workflows` namespace `use`s both
`conflict.sources` and `conflict.maps`.

## Cache / output

None at this layer — the workflow returns the `html_path` produced by
[map-rendering](map-rendering.md). Run it with:

```
fw ffl run --primary src/conflict/ffl/conflict.ffl \
  --workflow conflict.workflows.BuildConflictWorldMap --task-list conflict
```

(`--task-list conflict` matches the `conflict` top-level namespace, the intrinsic
routing key.)

## Gotchas & notes

- **The ordering is invisible to the compiler, so it must be written down.** The map
  and the download exchange no value; they communicate only through the cache. `after
  ucdp` states that edge directly. Drop it and the map step can race ahead of the
  download. (This replaces the old `dependency_signal` idiom, which faked a data edge
  by passing a number nothing read; `after` says the same thing without the lie.)
- **Handlers register exactly two facets.** `test_dispatch_keys` /
  `test_register_handlers` pin this — a runner advertising `conflict.*` claims only
  these two (plus the `fw:execute` / `fw:resume` protocol tasks).
- **Handlers are thin.** All behaviour lives in `_lib`; the handler layer only
  coerces `year`, logs, and re-raises. Fixes to metric/render logic go in `_lib`,
  not here.
- **The repo ships a `conflict` shell dispatcher** at the repo root (the generic
  `fwh_*` domain CLI front door), but this package has **no `tools/` directory**, so
  it exposes no terminal tools — only the FFL workflow above.

## Related specs

- [ucdp-ingest](ucdp-ingest.md) — the `DownloadUCDP` handler's real work.
- [map-rendering](map-rendering.md) — the `BuildConflictMap` handler's real work.
- [storage-and-cache](storage-and-cache.md) — the backend the handlers read/write
  through.
