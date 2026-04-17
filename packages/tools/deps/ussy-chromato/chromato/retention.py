"""Retention time calculator — computes how long a dependency is 'retained' in the column."""

from __future__ import annotations

from chromato.models import (
    Dependency,
    DependencyGraph,
    LICENSE_RESTRICTIVENESS,
    Solvent,
)


def compute_retention_time(
    dep: Dependency,
    graph: DependencyGraph,
    solvent: Solvent = Solvent.COUPLING,
) -> float:
    """Compute how long a dependency is 'retained' in the column.

    Higher retention time = higher risk/worse health.

    Args:
        dep: The dependency to analyze.
        graph: The full dependency graph.
        solvent: The analysis mode (coupling, risk, freshness, license).

    Returns:
        Retention time as a float (0.0 = best, higher = worse).
    """
    if solvent == Solvent.COUPLING:
        # Deep coupling = long retention
        depth = graph.coupling_depth(dep)
        breadth = graph.dependent_count(dep)
        return 0.3 * depth + 0.7 * breadth
    elif solvent == Solvent.RISK:
        # High risk = long retention
        vulns = dep.advisory_count
        age = dep.days_since_update()
        return 0.5 * vulns + 0.005 * age
    elif solvent == Solvent.FRESHNESS:
        # Stale = long retention (elutes last = worst)
        return dep.days_since_update()
    elif solvent == Solvent.LICENSE:
        # Restrictive = long retention
        return LICENSE_RESTRICTIVENESS.get(dep.license, 0.6)
    return 0.0


def compute_all_retention_times(
    graph: DependencyGraph,
    solvent: Solvent = Solvent.COUPLING,
) -> dict[str, float]:
    """Compute retention times for all dependencies in the graph.

    Returns:
        Dictionary mapping dependency name to retention time.
    """
    results: dict[str, float] = {}
    for dep in graph.dependencies:
        results[dep.name] = compute_retention_time(dep, graph, solvent)
    return results
