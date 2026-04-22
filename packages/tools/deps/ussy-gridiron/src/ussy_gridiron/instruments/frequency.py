"""Instrument 2: Frequency Monitor — Three-Tier Version Shock Response.

Maps version shocks to power system frequency disturbances:
  Primary (droop): ΔPᵢ = -(1/Rᵢ)·Δf
  Combined: Δf/f₀ = -ΔP_L / (D + Σᵢ(1/Rᵢ))
  Secondary (AGC): ACE = ΔP_tie + B·Δf
  Tertiary: architectural redesign

Dependency frequency equation:
  Δv/v₀ = -ΔS / (F + Σᵢ(1/Rvᵢ))
where Rvᵢ = version rigidity of package i.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from ussy_gridiron.graph import DependencyGraph
from ussy_gridiron.models import (
    FrequencyReport,
    FrequencyResult,
    PackageInfo,
    VersionShock,
)


class FrequencyMonitor:
    """Three-tier version shock response analysis."""

    # Ecosystem friction (lockfiles, caches)
    DEFAULT_FRICTION = 2.0

    def __init__(self, graph: DependencyGraph) -> None:
        self.graph = graph

    def analyze_shock(self, shock: VersionShock) -> FrequencyResult:
        """Analyze the system's response to a version shock event."""
        # Calculate total inverse rigidity (droop response)
        droop_response: Dict[str, float] = {}
        total_inverse_rigidity = 0.0

        for pkg_name, pkg in self.graph.packages.items():
            if pkg.version_rigidity > 0:
                inv_r = 1.0 / pkg.version_rigidity
            else:
                inv_r = 10.0  # very flexible
            droop_response[pkg_name] = inv_r
            total_inverse_rigidity += inv_r

        # Frequency deviation: Δv/v₀ = -ΔS / (F + Σ(1/Rvᵢ))
        friction = self.DEFAULT_FRICTION
        delta_s = shock.severity  # version shock magnitude
        denominator = friction + total_inverse_rigidity

        if denominator > 0:
            frequency_deviation = -delta_s / denominator
        else:
            frequency_deviation = -1.0

        # Absolute deviation
        abs_deviation = abs(frequency_deviation)

        # Primary recovery: packages with high 1/Rv absorb the shock
        # Primary recovers proportionally to how flexible packages are
        pkg_droop = droop_response.get(shock.package, 0.0)
        primary_fraction = min(pkg_droop / max(denominator, 0.001), 0.8) if shock.is_breaking else 0.9

        # Secondary recovery: coordinated lockfile updates
        secondary_fraction = min(0.95 - primary_fraction, 0.15)

        # Tertiary needed if combined primary + secondary < 95%
        total_recovery = primary_fraction + secondary_fraction
        tertiary_needed = total_recovery < 0.95

        # AGC equivalency: time to 95% re-resolution (hours)
        # Approximate: depends on how many rigid transmitters there are
        rigid_transmitters = [
            name for name, pkg in self.graph.packages.items()
            if pkg.version_rigidity >= 0.8
        ]

        # More rigid packages → slower re-resolution
        agc_time = len(rigid_transmitters) * 0.5 + abs_deviation * 10.0
        if tertiary_needed:
            agc_time += 24.0  # at least 24 hours for manual intervention

        return FrequencyResult(
            shock=shock,
            frequency_deviation=abs_deviation,
            droop_response=droop_response,
            primary_recovery=primary_fraction,
            secondary_recovery=secondary_fraction,
            tertiary_needed=tertiary_needed,
            agc_equivalency_time=agc_time,
            rigid_transmitters=rigid_transmitters,
        )

    def analyze(self, shocks: Optional[List[VersionShock]] = None) -> FrequencyReport:
        """Run frequency analysis for all or specified shock events."""
        if shocks is None:
            # Generate synthetic shocks for each direct dependency
            shocks = []
            for pkg_name, pkg in self.graph.packages.items():
                if pkg.is_direct:
                    shocks.append(VersionShock(
                        package=pkg_name,
                        old_version=pkg.version,
                        new_version=_bump_major(pkg.version),
                        severity=0.5,
                        is_breaking=True,
                    ))

        results: List[FrequencyResult] = []
        for shock in shocks:
            result = self.analyze_shock(shock)
            results.append(result)

        # Compute aggregate metrics
        avg_deviation = (
            sum(r.frequency_deviation for r in results) / len(results)
            if results else 0.0
        )
        worst_deviation = max(
            (r.frequency_deviation for r in results), default=0.0
        )

        # Build droop compliance map
        droop_map: Dict[str, float] = {}
        if results:
            for pkg_name, inv_r in results[0].droop_response.items():
                droop_map[pkg_name] = inv_r

        return FrequencyReport(
            results=results,
            average_deviation=avg_deviation,
            worst_deviation=worst_deviation,
            droop_compliance_map=droop_map,
        )


def _bump_major(version: str) -> str:
    """Bump the major version of a semver string."""
    parts = version.split(".")
    major = int(parts[0]) if parts else 0
    return f"{major + 1}.0.0"
