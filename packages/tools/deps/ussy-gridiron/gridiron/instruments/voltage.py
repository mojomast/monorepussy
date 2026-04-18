"""Instrument 5: Voltage Analyst — Capability Margin and Collapse Proximity.

Reactive power: Q ≈ |V|²/X
Voltage collapse when dQ/dV → ∞ (nose point of QV curve).
Modal analysis: J_QV·ΔV = ΔQ; eigenvalues λᵢ → 0 signals instability.

Mapping:
  P → primary functionality
  Q → capability support (types, docs, tests, backward compat)
  |V| → package "health voltage"
  X → semantic distance (API drift)
  Q = V²/X → capability = (compatibility²)/(API drift)
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from gridiron.graph import DependencyGraph
from gridiron.models import PackageInfo, VoltageReport, VoltageResult


class VoltageAnalyst:
    """Capability margin and collapse proximity analysis."""

    # Per-unit voltage thresholds
    VOLTAGE_SAG_THRESHOLD = 0.95  # below this = sagging
    VOLTAGE_CRITICAL_THRESHOLD = 0.90  # below this = critical

    def __init__(self, graph: DependencyGraph) -> None:
        self.graph = graph

    def analyze(self) -> VoltageReport:
        """Run voltage / QV analysis on all packages."""
        results: List[VoltageResult] = []
        names = sorted(self.graph.packages.keys())
        n = len(names)

        for pkg_name in names:
            result = self._analyze_package(pkg_name)
            results.append(result)

        # Modal analysis: build simplified J_QV and find eigenvalues
        eigenvalues = self._modal_analysis(results)

        # Identify weakest packages (lowest CPI)
        sorted_by_cpi = sorted(results, key=lambda r: r.collapse_proximity_index)
        weakest = [r.package for r in sorted_by_cpi[:5]]

        # Reactive compensation recommendations
        recommendations = self._generate_recommendations(results)

        return VoltageReport(
            package_results=results,
            weakest_packages=weakest,
            modal_eigenvalues=eigenvalues,
            reactive_compensation_recommendations=recommendations,
        )

    def _analyze_package(self, package: str) -> VoltageResult:
        """Analyze voltage/capability for a single package."""
        pkg = self.graph.packages.get(package, PackageInfo(name=package))

        # Health voltage: composite of maintainer activity, response, releases
        # Normalized to per-unit (0 to 1.1)
        v_health = self._compute_health_voltage(pkg)

        # Semantic reactance: API churn rate
        # Higher churn → higher X → lower Q → closer to collapse
        x_semantic = self._compute_semantic_reactance(pkg)

        # Reactive capability: Q = V² / X
        if x_semantic > 0:
            q_reactive = (v_health ** 2) / x_semantic
        else:
            q_reactive = float("inf")

        # Maximum Q (ideal case with zero churn and perfect health)
        q_max = (1.1 ** 2) / max(x_semantic, 0.01)

        # Q margin: surplus before collapse
        q_margin = q_reactive - 0.5 * q_max  # collapse at ~50% of max

        # Collapse Proximity Index: CPI = Q_margin / Q_max
        if q_max > 0:
            cpi = q_margin / q_max
        else:
            cpi = 1.0

        is_sagging = v_health < self.VOLTAGE_SAG_THRESHOLD

        # Participation factor: how much this package contributes to system instability
        # Higher = more destabilizing
        participation = max(0, 1.0 - cpi) * pkg.risk_weight

        return VoltageResult(
            package=package,
            health_voltage=v_health,
            reactive_capability=q_reactive,
            semantic_reactance=x_semantic,
            q_margin=q_margin,
            q_max=q_max,
            collapse_proximity_index=cpi,
            is_sagging=is_sagging,
            participation_factor=participation,
        )

    def _compute_health_voltage(self, pkg: PackageInfo) -> float:
        """Compute per-unit health voltage from package metadata.

        Components:
        - Maintainer count: more maintainers → higher V
        - Release frequency: more regular → higher V
        - Issue response time: faster → higher V
        - Has types/docs/tests: yes → higher V
        """
        # Maintainer score (0-0.2)
        maint_score = min(pkg.maintainers / 5.0, 1.0) * 0.2

        # Release frequency score (0-0.2): regular releases = healthy
        if pkg.release_frequency_days > 0:
            freq_score = min(30.0 / pkg.release_frequency_days, 1.0) * 0.2
        else:
            freq_score = 0.2

        # Issue response score (0-0.2)
        if pkg.issue_response_days > 0:
            resp_score = min(7.0 / pkg.issue_response_days, 1.0) * 0.2
        else:
            resp_score = 0.2

        # Quality score (0-0.4): types + docs + tests
        quality = sum([
            0.13 if pkg.has_types else 0,
            0.13 if pkg.has_docs else 0,
            0.14 if pkg.has_tests else 0,
        ])

        # Semver compliance bonus (0-0.1)
        semver_bonus = pkg.semver_compliance * 0.1

        v = 0.3 + maint_score + freq_score + resp_score + quality + semver_bonus
        return min(v, 1.1)  # cap at 1.1 per-unit

    def _compute_semantic_reactance(self, pkg: PackageInfo) -> float:
        """Compute semantic reactance (API drift).

        Higher reactance → more drift → closer to collapse.
        Based on: API surface size, side effects, type pollution.
        """
        # Base reactance from API surface
        base = 0.5 + pkg.api_surface_size * 0.05

        # Side effects increase reactance
        side_effect_contrib = pkg.side_effect_ratio * 2.0

        # Type pollution increases reactance
        pollution_contrib = pkg.type_pollution * 3.0

        return base + side_effect_contrib + pollution_contrib

    def _modal_analysis(self, results: List[VoltageResult]) -> List[float]:
        """Simplified modal analysis.

        Compute eigenvalues of the participation factor "matrix."
        In full implementation, this would be J_QV eigenvalue analysis.
        Here we approximate: each package contributes an eigenvalue
        proportional to its stability.
        """
        eigenvalues = []
        for result in results:
            # Eigenvalue: high participation → small eigenvalue → instability
            if result.participation_factor > 0:
                eigenvalue = 1.0 / result.participation_factor
            else:
                eigenvalue = 100.0  # very stable
            eigenvalues.append(round(eigenvalue, 4))
        return eigenvalues

    def _generate_recommendations(self, results: List[VoltageResult]) -> List[str]:
        """Generate reactive compensation recommendations."""
        recs: List[str] = []

        for result in results:
            pkg = self.graph.packages.get(result.package, PackageInfo(name=result.package))

            if result.collapse_proximity_index < 0.1:
                recs.append(
                    f"CRITICAL: {result.package} near collapse "
                    f"(CPI={result.collapse_proximity_index:.3f}). "
                    f"Immediate action required: add type definitions, improve docs."
                )
            elif result.collapse_proximity_index < 0.3:
                recs.append(
                    f"WARNING: {result.package} sagging "
                    f"(V={result.health_voltage:.3f} pu, CPI={result.collapse_proximity_index:.3f}). "
                    f"Add type stubs and documentation."
                )
            elif result.is_sagging:
                recs.append(
                    f"Monitor: {result.package} voltage sag "
                    f"(V={result.health_voltage:.3f} pu < {self.VOLTAGE_SAG_THRESHOLD})."
                )

        return recs
