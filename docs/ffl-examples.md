# FFL Examples — `conflict`

Every numbered scenario is a **complete, compilable FFL file**. Copy one into
`my.ffl` and run it:

```bash
fw ffl run --primary my.ffl \
  --library ~/fw_handlers/fwh_conflict/src/conflict/ffl/conflict.ffl \
  --workflow my.conflict.<WorkflowName>
```

A runner serving the `conflict` namespace must be up
(`fw runner start --domain conflict`). Every block below is compile-checked
against `src/conflict/ffl/conflict.ffl`.

New to the language? Start with the
[FFL grammar](https://github.com/rlemke/facetwork/blob/main/docs/reference/language/grammar.md)
and the [canonical examples](https://github.com/rlemke/facetwork/tree/main/examples/canonical).

---

## The facets at a glance

| Declaration | Signature | Does |
|---|---|---|
| `conflict.sources.DownloadUCDP` | `(year: Int = 0, force: Boolean = false) => (year: Int, country_count: Int)` | UCDP GED bulk CSV → cached per-country aggregate for a year (`0` = latest) |
| `conflict.maps.BuildConflictMap` | `(year: Int = 0) => (html_path, geojson_path, year, country_count)` | Join onto Natural Earth geometry, normalise by population, render the choropleth |
| `conflict.workflows.BuildConflictWorldMap` | `(year: Int = 0) => (status, html_path, year, country_count)` | The shipped entry point: download → build |

---

## 1. Run what ships — no FFL to write

```bash
fw ffl seed --include conflict

fw ffl run --primary ~/fw_handlers/fwh_conflict/src/conflict/ffl/conflict.ffl \
  --workflow conflict.workflows.BuildConflictWorldMap \
  --inputs '{"year": 0}'          # 0 = latest year in the dataset
```

Write FFL when you want to change the *shape* of the run — a different sequence,
your own error handling, a sweep over years, or composition with another domain.

## 2. The smallest workflow you can write

Every FFL workflow needs a `namespace`, a `use` per namespace it calls into, and a
`yield` back to itself.

```ffl
namespace my.conflict {

    use conflict.sources
    use conflict.maps

    /** Download the UCDP aggregate, then render the world map. */
    workflow MyConflictMap() => (html_path: String, countries: Int) andThen {

        ucdp = conflict.sources.DownloadUCDP(year = 0)

        map = conflict.maps.BuildConflictMap(year = 0) after ucdp

        yield MyConflictMap(html_path = map.html_path, countries = map.country_count)
    }
}
```

Three rules visible above: `=>` sits on the **same line** as the closing `)` of the
parameter list; references are always `step.field` (never a bare step name); `$.x`
reads the container's attributes.

## 3. Parameters and `$`

`$` always means "my immediate container" — inside a workflow body that's the
workflow, so `$.year` is its parameter. `$$` walks one level out.

```ffl
namespace my.conflict {

    use conflict.sources
    use conflict.maps

    /** Map one specific year, optionally bypassing the cache. */
    workflow ConflictYear(year: Int = 2023, force: Boolean = false) => (status: String, html_path: String) andThen {

        ucdp = conflict.sources.DownloadUCDP(year = $.year, force = $.force)

        map = conflict.maps.BuildConflictMap(year = $.year) after ucdp

        yield ConflictYear(status = "completed", html_path = map.html_path)
    }
}
```

Run with `--inputs '{"year": 2014, "force": true}'`.

## 4. Sweep several years in parallel — `foreach`

`andThen foreach v in <list>` turns one step into N runtime steps the fleet claims
in parallel. Drive the list from a `Json` parameter and the sweep is a CLI argument:

```ffl
namespace my.conflict {

    use conflict.sources
    use conflict.maps

    /** One download+render per year, fanned out across the fleet. */
    workflow ConflictYears(years: Json) => (built: [Int]) andThen foreach y in $.years {

        ucdp = conflict.sources.DownloadUCDP(year = $.y)

        map = conflict.maps.BuildConflictMap(year = $.y) after ucdp

        yield ConflictYears(built = [map.year])
    }
}
```

```bash
fw ffl run --primary my.ffl --library …/conflict.ffl \
  --workflow my.conflict.ConflictYears \
  --inputs '{"years": [2020, 2021, 2022, 2023]}'
```

Wall clock is the slowest year, not the sum. Watch the fan-out on the dashboard's
execution graph.

## 5. Sequencing steps that share no data

`BuildConflictMap` reads the *cache* the download wrote — it needs no value from
it. Steps that exchange no value are unordered, so state the dependency explicitly
with `after`:

```ffl
namespace my.conflict {

    use conflict.sources
    use conflict.maps

    /** Ordering comes from the reference, not from line order. */
    workflow OrderedConflictBuild() => (html_path: String) andThen {

        ucdp = conflict.sources.DownloadUCDP()

        // referencing ucdp.country_count is what makes this run second
        map = conflict.maps.BuildConflictMap() after ucdp

        yield OrderedConflictBuild(html_path = map.html_path)
    }
}
```

## 6. Call-time mixins — timeouts and retries

A facet declares its defaults (`DownloadUCDP` ships `with Timeout(minutes = 15)`);
the **call site** can add or override mixins for one particular use.

```ffl
namespace my.conflict {

    use conflict.sources
    use conflict.maps

    /** The UCDP bulk zip is large — be patient, and retry transient failures. */
    workflow ResilientConflictMap() => (html_path: String) andThen {

        ucdp = conflict.sources.DownloadUCDP(force = true) with Timeout(minutes = 45) with Retry(maxAttempts = 3, backoffSeconds = 60)

        map = conflict.maps.BuildConflictMap() with Timeout(minutes = 20) after ucdp

        yield ResilientConflictMap(html_path = map.html_path)
    }
}
```

## 7. Survive a failed download — `catch`

`catch` runs when its step errors after retries are exhausted. Yielding from the
catch block ends the run with a partial result instead of a hard failure.

```ffl
namespace my.conflict {

    use conflict.sources
    use conflict.maps

    /** Report a partial result rather than failing. */
    workflow BestEffortConflictMap() => (status: String, html_path: String) andThen {

        ucdp = conflict.sources.DownloadUCDP(force = true) catch {
            yield BestEffortConflictMap(status = "download_failed", html_path = "")
        }

        map = conflict.maps.BuildConflictMap() after ucdp

        yield BestEffortConflictMap(status = "completed", html_path = map.html_path)
    }
}
```

## 8. Branch on a result — `when`

A `when` block hangs off the step it inspects: inside a case `$` is that step,
`$$` reaches the workflow's parameters. Every `when` needs a default case, last.

```ffl
namespace my.conflict {

    use conflict.sources
    use conflict.maps

    /** Only render when the year actually has country coverage. */
    workflow GuardedConflictMap(min_countries: Int = 20) => (status: String, html_path: String) andThen {

        ucdp = conflict.sources.DownloadUCDP() andThen when {
            case $.country_count >= $$.min_countries => {
                map = conflict.maps.BuildConflictMap()
                yield GuardedConflictMap(status = "completed", html_path = map.html_path)
            }
            case _ => {
                yield GuardedConflictMap(status = "sparse_year", html_path = "")
            }
        }
    }
}
```

## 9. Reuse the shipped workflow

Workflows compose like facets — wrap `BuildConflictWorldMap` instead of forking it.

```ffl
namespace my.conflict {

    use conflict.workflows

    /** Wrap the shipped workflow and reshape its result. */
    workflow ConflictWithHeadline(year: Int = 0) => (headline: String) andThen {

        built = conflict.workflows.BuildConflictWorldMap(year = $.year)

        yield ConflictWithHeadline(
            headline = "conflict map built: " ++ built.status)
    }
}
```

## 10. Compose across domains — publish the map

Facets from different domains compose in one workflow as long as some runner
serves each namespace. `census.Publish` is the generic publisher the map domains
share.

```ffl
namespace my.conflict {

    use conflict.maps
    use census.Publish

    /** Render, then push to the public maps site. */
    workflow ConflictPublish(repo: String = "rlemke/facetwork-maps") => (pages_url: String) andThen {

        map = conflict.maps.BuildConflictMap()

        published = census.Publish.PublishWebBundle(
            repo = $.repo,
            prefixes = ["conflict/output"],
            dests = ["world/conflict"],
            labels = ["Armed conflict (UCDP)"],
            landing_title = "Facetwork maps")

        yield ConflictPublish(pages_url = published.pages_url)
    }
}
```

Compile that one with `--library ~/fw_handlers/fwh_census_us/src/census_us/ffl/census.ffl`
as well.

---

## Cheat sheet

| You want to… | Write |
|---|---|
| Read a workflow/step parameter | `$.name` (`$$.name` one level out) |
| Read a previous step's result | `stepname.field` |
| Order two independent steps | reference a field of the first from the second |
| Fan out over a list | `workflow W(items: Json) … andThen foreach i in $.items { … }` |
| More time / retries for one call | `… with Timeout(minutes = 45) with Retry(maxAttempts = 3, backoffSeconds = 60)` |
| Handle a step failure | `step = Facet(…) catch { yield … }` |
| Branch | `step = Facet(…) andThen when { case <bool> => { … } case _ => { … } }` |
| Concatenate strings | `a ++ b` |

**Validate before you run:** `afl my.ffl --check` or MCP `fw_validate`. Every error
carries a `rule_id` — fetch `fw://docs/rules/{rule_id}` for a wrong/right pair.

## See also

- [`docs/README.md`](README.md) — per-feature specs for this domain
- [FFL grammar](https://github.com/rlemke/facetwork/blob/main/docs/reference/language/grammar.md) ·
  [canonical examples](https://github.com/rlemke/facetwork/tree/main/examples/canonical) ·
  [relative `$`-scoping](https://github.com/rlemke/facetwork/blob/main/docs/architecture/ffl-relative-scoping.md)
- `src/conflict/ffl/conflict.ffl` — the source of truth for every signature above
