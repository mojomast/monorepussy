"""Hoard analysis — dependency cluster identification.

Uses connected-components approach for community detection
(no networkx dependency required). Identifies dependency clusters,
shared maintainers, and contamination risks in lockfiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ussy_mint.models import Hoard, get_grade_category
from ussy_mint.lockfile import LockedPackage, build_dependency_graph


def find_connected_components(graph: dict[str, list[str]]) -> list[set[str]]:
    """Find connected components in a dependency graph using BFS.

    Simple community detection — each connected component is a cluster
    of packages that are transitively connected through dependencies.

    Args:
        graph: Dict mapping package name to list of dependency names

    Returns:
        List of sets, each set containing package names in one component
    """
    visited: set[str] = set()
    components: list[set[str]] = []

    for node in graph:
        if node in visited:
            continue

        # BFS from this node
        component: set[str] = set()
        queue = [node]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            # Add neighbors (both directions)
            for neighbor in graph.get(current, []):
                if neighbor not in visited:
                    queue.append(neighbor)
            # Also add reverse edges
            for other_node, deps in graph.items():
                if current in deps and other_node not in visited:
                    queue.append(other_node)

        if component:
            components.append(component)

    return components


def identify_cluster_name(
    packages: set[str],
    known_clusters: dict[str, list[str]] | None = None,
) -> str:
    """Identify a name for a dependency cluster.

    Uses heuristic matching against known ecosystem patterns.

    Args:
        packages: Set of package names in the cluster
        known_clusters: Optional mapping of cluster names to characteristic packages

    Returns:
        A human-readable cluster name
    """
    if known_clusters:
        for cluster_name, characteristic_pkgs in known_clusters.items():
            overlap = len(packages & set(characteristic_pkgs))
            if overlap >= 2:
                return cluster_name

    # Heuristic: try to derive a name from the packages
    pkg_list = sorted(packages)
    if not pkg_list:
        return "Empty Cluster"

    # Check for common prefixes/scopes
    scopes: dict[str, int] = {}
    for pkg in pkg_list:
        if pkg.startswith("@"):
            scope = pkg.split("/")[0]
            scopes[scope] = scopes.get(scope, 0) + 1

    if scopes:
        dominant_scope = max(scopes, key=scopes.get)
        return f"{dominant_scope} Ecosystem"

    # Use the most-connected package as the cluster name
    return f"{pkg_list[0]} Cluster"


def compute_contamination_risk(
    maintainer_overlap: float,
    min_grade: int,
    provenance_gaps: int,
    total_packages: int,
) -> float:
    """Compute contamination risk for a dependency cluster.

    risk = maintainer_overlap * 0.4 + grade_vulnerability * 0.3 + provenance_gap_ratio * 0.3

    Args:
        maintainer_overlap: Fraction of packages sharing maintainers (0.0-1.0)
        min_grade: Lowest Sheldon grade in the cluster
        provenance_gaps: Number of packages with provenance gaps
        total_packages: Total number of packages in the cluster

    Returns:
        Contamination risk score (0.0-1.0)
    """
    grade_vulnerability = max(0.0, 1.0 - min_grade / 70.0)
    provenance_gap_ratio = provenance_gaps / max(1, total_packages)

    risk = (
        maintainer_overlap * 0.4
        + grade_vulnerability * 0.3
        + provenance_gap_ratio * 0.3
    )
    return max(0.0, min(1.0, risk))


def analyze_hoard(
    packages: list[LockedPackage],
    package_grades: dict[str, int] | None = None,
    maintainers_per_pkg: dict[str, list[str]] | None = None,
    provenance_levels: dict[str, int] | None = None,
) -> list[Hoard]:
    """Perform full hoard analysis on a lockfile's packages.

    Identifies dependency clusters using connected-components,
    then computes cluster-level metrics including contamination risk.

    Args:
        packages: List of LockedPackage objects from the lockfile
        package_grades: Optional mapping of package name to Sheldon grade
        maintainers_per_pkg: Optional mapping of package name to maintainer list
        provenance_levels: Optional mapping of package name to provenance level (0-3)

    Returns:
        List of Hoard objects, one per identified cluster
    """
    if package_grades is None:
        package_grades = {}
    if maintainers_per_pkg is None:
        maintainers_per_pkg = {}
    if provenance_levels is None:
        provenance_levels = {}

    # Build dependency graph and find clusters
    graph = build_dependency_graph(packages)
    components = find_connected_components(graph)

    # Sort by size descending
    components.sort(key=len, reverse=True)

    hoards: list[Hoard] = []

    for component in components:
        pkg_list = sorted(component)
        cluster_name = identify_cluster_name(component)

        # Compute average fineness
        fineness_values = []
        for pkg_name in pkg_list:
            pkg = next((p for p in packages if p.name == pkg_name), None)
            if pkg:
                fineness_values.append(1.0)  # Default if no fineness data

        avg_fineness = sum(fineness_values) / max(1, len(fineness_values))

        # Compute max debasement (worst grade loss)
        grades = [package_grades.get(p, 35) for p in pkg_list]
        min_grade = min(grades) if grades else 35

        # Compute maintainer overlap
        cluster_maintainers: dict[str, list[str]] = {}
        for pkg_name in pkg_list:
            if pkg_name in maintainers_per_pkg:
                cluster_maintainers[pkg_name] = maintainers_per_pkg[pkg_name]

        maintainer_overlap = _compute_cluster_maintainer_overlap(cluster_maintainers)

        # Find common maintainers across the cluster
        common_maints = _find_common_maintainers(cluster_maintainers)

        # Count provenance gaps
        pg_count = sum(
            1 for p in pkg_list
            if provenance_levels.get(p, 0) < 2
        )

        # Compute contamination risk
        contamination_risk = compute_contamination_risk(
            maintainer_overlap, min_grade, pg_count, len(pkg_list)
        )

        hoards.append(Hoard(
            name=cluster_name,
            packages=pkg_list,
            co_occurrence=1.0,  # Full co-occurrence since they're in the same lockfile
            common_maintainers=common_maints,
            total_fineness=round(avg_fineness, 3),
            max_debasement=round(max(0, 70 - min_grade), 1),
            contamination_risk=round(contamination_risk, 3),
        ))

    return hoards


def _compute_cluster_maintainer_overlap(maintainers_per_pkg: dict[str, list[str]]) -> float:
    """Compute maintainer overlap within a cluster."""
    packages = list(maintainers_per_pkg.keys())
    if len(packages) < 2:
        return 0.0

    overlapping_pairs = 0
    total_pairs = 0

    for i in range(len(packages)):
        for j in range(i + 1, len(packages)):
            total_pairs += 1
            set_a = set(maintainers_per_pkg[packages[i]])
            set_b = set(maintainers_per_pkg[packages[j]])
            if set_a & set_b:
                overlapping_pairs += 1

    if total_pairs == 0:
        return 0.0
    return overlapping_pairs / total_pairs


def _find_common_maintainers(maintainers_per_pkg: dict[str, list[str]]) -> list[str]:
    """Find maintainers who appear in multiple packages in the cluster."""
    if not maintainers_per_pkg:
        return []

    maintainer_counts: dict[str, int] = {}
    for maintainers in maintainers_per_pkg.values():
        for m in set(maintainers):  # Dedupe per package
            maintainer_counts[m] = maintainer_counts.get(m, 0) + 1

    # Return maintainers who appear in more than one package
    return sorted(m for m, count in maintainer_counts.items() if count > 1)


def format_hoard_report(hoards: list[Hoard], total_packages: int) -> str:
    """Format hoard analysis results as a human-readable report.

    Args:
        hoards: List of Hoard objects
        total_packages: Total number of packages in the lockfile

    Returns:
        Formatted report string
    """
    lines = [f"Hoard Analysis: {total_packages} packages across {len(hoards)} cluster(s)"]

    for hoard in hoards:
        # Risk indicator
        if hoard.contamination_risk >= 0.7:
            indicator = "🔴"
        elif hoard.contamination_risk >= 0.4:
            indicator = "🟡"
        else:
            indicator = "🟢"

        maint_overlap = f"{hoard.common_maintainers}" if hoard.common_maintainers else "none"
        lines.append(
            f'  {indicator} Cluster "{hoard.name}" '
            f"({len(hoard.packages)} pkgs, "
            f"contamination: {hoard.contamination_risk:.2f}, "
            f"common maintainers: {maint_overlap})"
        )

        # Flag low-grade packages
        low_grade = [p for p in hoard.packages if hoard.max_debasement > 50]
        if low_grade:
            lines.append(f'    ⚠️ {len(low_grade)} package(s) with grade < G-4 (contamination risk)')

    return "\n".join(lines)
