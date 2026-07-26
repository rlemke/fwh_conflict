<!-- SPEC TEMPLATE — every docs/<feature>.md follows this shape so the set reads
consistently. Delete this comment in real specs. Keep sections in this order;
omit a section only if it genuinely does not apply (say so in one line rather
than dropping the heading silently). Ground every claim in the actual FFL
docstrings / handler code / _lib functions — do not invent behaviour. -->

# <Feature Name>

**Namespace(s):** `conflict.<ns>` · **FFL:** `src/conflict/ffl/conflict.ffl` ·
**Handlers:** `src/conflict/handlers/conflict_handlers.py` · **Library:** `src/conflict/_lib.py` (functions this feature uses)

## Overview
One or two paragraphs: what this feature is for, the request it answers, and where
it sits in the pipeline (download → aggregate → join → render).

## How it works
The algorithm / data flow, step by step. Name the concrete functions and the shape
of the data at each (bulk CSV → per-country aggregate JSON → joined GeoJSON → HTML
map, etc.). Note the two-step workflow split (source facet vs map facet) where it
matters.

## Fan-out
Does it fan out across the fleet? This domain builds one world map from a single
global dataset, so most features are **single-task — no fan-out**; say so and why
(world-scale single pass, atomic render). If a feature ever fans out, name the
`foreach` and the unit.

## Data & fields
What data it reads and on which fields — be specific (UCDP GED columns `country`,
`best`, `type_of_violence`, `side_a`/`side_b`, `year`; Natural Earth `NAME`,
`ISO_A3`, `ADM0_A3`, `POP_EST`; the join key — UCDP by `NAME` + `COUNTRY_ALIASES`,
overlays by `ISO3`). Name the derived metric keys (`m_events`, `m_deaths`,
`m_civilian`, `m_intensity`, `m_actors`, `m_displaced`, `m_new_displaced`,
`m_food_insecure`) where relevant. If the feature does no filtering, say so.

## External libraries / binaries
Every non-stdlib dependency this feature relies on and what for — e.g. `requests`
(HTTP download), `openpyxl` (IDMC xlsx export), `facetwork.runtime.storage`
(backend-aware I/O). Distinguish a **binary** dependency (none here) from a **pip**
one, and note anything imported lazily.

## Facets & workflows
The key event facets and workflows, with signatures and a one-line purpose taken
from the FFL docstrings. Mark event facets (need a handler) vs pure facets, and
note `Effect`/`Cost`/`Timeout` mixins where present.

## Cache / output
The cache namespace under `$FW_DATA_ROOT/cache/conflict/` (or the local
`conflict-cache` / `conflict-output` dirs) and the concrete filenames, plus the
output artifact(s) and format (aggregate JSON / joined GeoJSON / MapLibre HTML).
Note whether outputs go to local disk or MinIO/S3, and the override env vars.

## Gotchas & notes
Known pitfalls, name-alias drift, join-key mismatches, rate limits, sensitivity
caveats, or non-obvious constraints (worth capturing anything a future maintainer
would trip on).

## Related specs
Links to the specs this feature composes with or depends on.
