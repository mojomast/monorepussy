"""Uncertainty Budget — GUM Combined Standard Uncertainty.

Implements the Law of Propagation of Uncertainty from the Guide to the
Expression of Uncertainty in Measurement (GUM).

u_c²(y) = Σᵢ (cᵢ · u(xᵢ))² + 2·ΣᵢΣⱼ cᵢ·cⱼ·u(xᵢ)·u(xⱼ)·r(xᵢ,xⱼ)

Where:
  cᵢ = ∂f/∂xᵢ = sensitivity coefficient
  u(xᵢ) = standard uncertainty of source i
  r(xᵢ,xⱼ) = correlation coefficient
  U = k · u_c(y) where k=2 for ~95% confidence
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ussy_calibre.models import TestRun, UncertaintyBudget, UncertaintySource


def compute_sensitivity_coefficients(
    sources: List[UncertaintySource],
) -> List[float]:
    """Return sensitivity coefficients (already stored in each source)."""
    return [s.sensitivity_coefficient for s in sources]


def compute_combined_uncertainty(sources: List[UncertaintySource]) -> float:
    """Compute combined standard uncertainty u_c(y) using GUM LPU.

    Includes correlation terms for linked sources.
    """
    if not sources:
        return 0.0

    # First term: sum of (c_i * u(x_i))^2
    variance_sum = sum(s.contribution for s in sources)

    # Correlation term: 2 * sum over correlated pairs
    correlation_term = 0.0
    source_map: Dict[str, UncertaintySource] = {s.name: s for s in sources}

    for s in sources:
        if s.correlation_with and s.correlation_with in source_map:
            other = source_map[s.correlation_with]
            # Only count each pair once
            if s.name < other.name:
                correlation_term += (
                    2.0
                    * s.sensitivity_coefficient
                    * other.sensitivity_coefficient
                    * s.uncertainty_value
                    * other.uncertainty_value
                    * s.correlation_coefficient
                )

    combined_variance = variance_sum + correlation_term
    return combined_variance ** 0.5


def compute_expanded_uncertainty(
    combined_uncertainty: float, coverage_factor: float = 2.0
) -> float:
    """Compute expanded uncertainty U = k * u_c(y)."""
    return coverage_factor * combined_uncertainty


def find_dominant_source(sources: List[UncertaintySource]) -> str:
    """Find the uncertainty source with the largest contribution."""
    if not sources:
        return ""
    return max(sources, key=lambda s: s.contribution).name


def build_budget(
    measurand: str,
    sources: List[UncertaintySource],
    coverage_factor: float = 2.0,
) -> UncertaintyBudget:
    """Build a complete uncertainty budget from sources."""
    combined = compute_combined_uncertainty(sources)
    expanded = compute_expanded_uncertainty(combined, coverage_factor)
    dominant = find_dominant_source(sources)

    return UncertaintyBudget(
        measurand=measurand,
        sources=sources,
        combined_uncertainty=combined,
        expanded_uncertainty=expanded,
        coverage_factor=coverage_factor,
        dominant_source=dominant,
    )


def budget_from_test_runs(
    module: str, runs: List[TestRun]
) -> UncertaintyBudget:
    """Compute an uncertainty budget for a module from test run data.

    Derives uncertainty sources from observed test behavior:
    - Flakiness rate uncertainty
    - Environment variance uncertainty
    - Duration variance (proxy for timing sensitivity)
    """
    if not runs:
        return build_budget(module, [])

    # Group runs by test_name
    by_test: Dict[str, List[TestRun]] = {}
    for r in runs:
        by_test.setdefault(r.test_name, []).append(r)

    # Group by environment
    by_env: Dict[str, List[TestRun]] = {}
    for r in runs:
        by_env.setdefault(r.environment, []).append(r)

    # Compute flakiness uncertainty
    pass_rates: List[float] = []
    for test_runs in by_test.values():
        if test_runs:
            rate = sum(1 for r in test_runs if r.passed) / len(test_runs)
            pass_rates.append(rate)

    if pass_rates:
        mean_rate = sum(pass_rates) / len(pass_rates)
        variance = sum((r - mean_rate) ** 2 for r in pass_rates) / len(pass_rates)
        flakiness_uncertainty = variance ** 0.5
    else:
        flakiness_uncertainty = 0.0

    # Compute environment variance
    env_rates: Dict[str, float] = {}
    for env, env_runs in by_env.items():
        if env_runs:
            env_rates[env] = sum(1 for r in env_runs if r.passed) / len(env_runs)

    if len(env_rates) >= 2:
        env_values = list(env_rates.values())
        env_mean = sum(env_values) / len(env_values)
        env_var = sum((v - env_mean) ** 2 for v in env_values) / len(env_values)
        env_uncertainty = env_var ** 0.5
    else:
        env_uncertainty = 0.0

    # Duration variance as proxy for timing sensitivity
    durations = [r.duration for r in runs if r.duration > 0]
    if len(durations) >= 2:
        dur_mean = sum(durations) / len(durations)
        dur_var = sum((d - dur_mean) ** 2 for d in durations) / len(durations)
        duration_uncertainty = (dur_var ** 0.5) / dur_mean if dur_mean > 0 else 0.0
    else:
        duration_uncertainty = 0.0

    # Data staleness uncertainty (assume small default)
    staleness_uncertainty = 0.01

    # Mock fidelity uncertainty (assume small default)
    mock_fidelity_uncertainty = 0.02

    sources = [
        UncertaintySource(
            name="flakiness",
            uncertainty_value=flakiness_uncertainty,
            sensitivity_coefficient=1.0,
            uncertainty_type=None,
        ),
        UncertaintySource(
            name="environment_variance",
            uncertainty_value=env_uncertainty,
            sensitivity_coefficient=0.8,
            correlation_with="flakiness",
            correlation_coefficient=0.3,
        ),
        UncertaintySource(
            name="timing_sensitivity",
            uncertainty_value=duration_uncertainty,
            sensitivity_coefficient=0.5,
        ),
        UncertaintySource(
            name="data_staleness",
            uncertainty_value=staleness_uncertainty,
            sensitivity_coefficient=0.3,
        ),
        UncertaintySource(
            name="mock_fidelity",
            uncertainty_value=mock_fidelity_uncertainty,
            sensitivity_coefficient=0.4,
        ),
    ]

    return build_budget(module, sources)


def format_budget(budget: UncertaintyBudget) -> str:
    """Format an uncertainty budget as a readable table."""
    lines: List[str] = []
    lines.append(f"{'='*60}")
    lines.append(f"Uncertainty Budget: {budget.measurand}")
    lines.append(f"{'='*60}")
    lines.append("")
    lines.append(f"{'Source':<25} {'u(x)':>8} {'c_i':>6} {'Contribution':>14}")
    lines.append(f"{'-'*25} {'-'*8} {'-'*6} {'-'*14}")

    for s in budget.sources:
        lines.append(
            f"{s.name:<25} {s.uncertainty_value:>8.4f} {s.sensitivity_coefficient:>6.2f} "
            f"{s.contribution:>14.6f}"
        )

    lines.append("")
    lines.append(f"Combined uncertainty u_c(y) = {budget.combined_uncertainty:.6f}")
    lines.append(
        f"Expanded uncertainty U(k={budget.coverage_factor:.0f}) = "
        f"{budget.expanded_uncertainty:.6f}"
    )
    lines.append(f"Dominant source: {budget.dominant_source}")
    lines.append("")

    return "\n".join(lines)
