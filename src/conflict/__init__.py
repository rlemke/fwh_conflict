"""Conflict domain — Facetwork workflows + handlers for UCDP armed-conflict maps.

Builds a world country choropleth (with a metric dropdown) from the Uppsala
Conflict Data Program's Georeferenced Event Dataset (GED). Discovered by the
Facetwork runner via the ``facetwork.domains`` entry point in pyproject.toml::

    [project.entry-points."facetwork.domains"]
    conflict = "conflict:domain"
"""

from __future__ import annotations

from pathlib import Path

from facetwork.domains import DomainPackage

from .handlers import register_all_registry_handlers

domain = DomainPackage(
    name="conflict",
    ffl_dir=Path(__file__).parent / "ffl",
    register_handlers=register_all_registry_handlers,
)
