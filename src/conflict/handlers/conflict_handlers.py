"""Event facet handlers for the conflict domain — thin layers over ``_lib``."""

from __future__ import annotations

import os
from typing import Any

from .._lib import build_conflict_map, download_ucdp_aggregate

SRC = "conflict.sources"
MAPS = "conflict.maps"


def _yr(params: dict) -> int | None:
    y = params.get("year")
    try:
        return int(y) if y else None  # 0 / "" / None → latest
    except (TypeError, ValueError):
        return None


def handle_download_ucdp(params: dict[str, Any]) -> dict[str, Any]:
    """Download the UCDP GED bulk CSV + cache the per-country aggregate."""
    step_log = params.get("_step_log")
    try:
        year, countries = download_ucdp_aggregate(year=_yr(params), force=bool(params.get("force")))
        if step_log:
            step_log(f"DownloadUCDP: year {year}, {len(countries)} countries", level="success")
        return {"year": year, "country_count": len(countries)}
    except Exception as exc:
        if step_log:
            step_log(f"DownloadUCDP: {exc}", level="error")
        raise


def handle_build_conflict_map(params: dict[str, Any]) -> dict[str, Any]:
    """Join the UCDP aggregate onto world geometry + render the choropleth."""
    step_log = params.get("_step_log")
    try:
        res = build_conflict_map(year=_yr(params))
        if step_log:
            step_log(
                f"BuildConflictMap: year {res.year}, {res.country_count} countries "
                f"-> {res.html_path}",
                level="success",
            )
        return {
            "html_path": res.html_path,
            "geojson_path": res.output_path,
            "year": res.year,
            "country_count": res.country_count,
        }
    except Exception as exc:
        if step_log:
            step_log(f"BuildConflictMap: {exc}", level="error")
        raise


_DISPATCH: dict[str, Any] = {
    f"{SRC}.DownloadUCDP": handle_download_ucdp,
    f"{MAPS}.BuildConflictMap": handle_build_conflict_map,
}


def handle(payload: dict) -> dict:
    facet = payload["_facet_name"]
    handler = _DISPATCH.get(facet)
    if handler is None:
        raise ValueError(f"Unknown facet: {facet}")
    return handler(payload)


def register_handlers(runner) -> None:
    for facet_name in _DISPATCH:
        runner.register_handler(
            facet_name=facet_name,
            module_uri=f"file://{os.path.abspath(__file__)}",
            entrypoint="handle",
        )


def register_poller(poller) -> None:
    for facet_name, handler in _DISPATCH.items():
        poller.register(facet_name, handler)
