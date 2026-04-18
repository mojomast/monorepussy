"""Instrument 1: Contingency Analyzer — N-1 Single-Point-of-Failure Analysis.

For each package k, remove it from the graph and verify:
  App(G\\{k}) ∈ {FUNCTIONAL, DEGRADED, FAILED}

If FAILED → k is a Single Point of Failure.
Severity(k) = Σⱼ weight(j) for all affected transitive dependents j.
"""

from __future__ import annotations

from typing import Dict, List

from gridiron.graph import DependencyGraph
from gridiron.models import (
    ContingencyResult,
    N1Report,
    PackageInfo,
    SystemState,
)


class ContingencyAnalyzer:
    """N-1 contingency analysis for dependency graphs."""

    def __init__(self, graph: DependencyGraph) -> None:
        self.graph = graph

    def analyze(self) -> N1Report:
        """Run N-1 contingency analysis on all packages in the graph.

        For each package, remove it and check if the system survives.
        """
        results: List[ContingencyResult] = []
        spof_register: List[ContingencyResult] = []
        passing = 0

        for pkg_name in sorted(self.graph.packages.keys()):
            result = self._analyze_single(pkg_name)
            results.append(result)

            if result.system_state == SystemState.FUNCTIONAL:
                passing += 1
            else:
                spof_register.append(result)

        # Sort SPOF register by blast radius (descending)
        spof_register.sort(key=lambda r: r.blast_radius, reverse=True)

        total = len(self.graph.packages)
        return N1Report(
            total_packages=total,
            passing_packages=passing,
            spof_register=spof_register,
            all_results=results,
        )

    def _analyze_single(self, package: str) -> ContingencyResult:
        """Analyze system state after removing a single package."""
        state = self.graph.assess_state_without(package)

        # Calculate blast radius
        affected = list(self.graph.transitive_dependents(package))
        blast_radius = sum(
            self.graph.packages.get(dep, PackageInfo(name=dep)).risk_weight
            for dep in affected
        )

        is_spof = state == SystemState.FAILED
        recommendation = ""
        if is_spof:
            pkg = self.graph.packages.get(package)
            backups = pkg.backup_packages if pkg else []
            if backups:
                recommendation = (
                    f"Add backup path via: {', '.join(backups)}"
                )
            else:
                recommendation = (
                    f"Identify and add alternative packages for {package}"
                )
        elif state == SystemState.DEGRADED:
            recommendation = (
                f"Consider adding backup dependencies for {package}"
            )

        return ContingencyResult(
            removed_package=package,
            system_state=state,
            affected_packages=affected,
            blast_radius=blast_radius,
            is_spof=is_spof,
            recommendation=recommendation,
        )

    def analyze_specific(self, package: str) -> ContingencyResult:
        """Analyze N-1 for a specific package."""
        return self._analyze_single(package)
