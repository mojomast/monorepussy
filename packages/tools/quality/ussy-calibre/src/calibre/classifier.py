"""Uncertainty Classifier — Type A vs Type B Uncertainty.

Type A (statistical/random): u_A(x) = s(x_bar) = s(x) / sqrt(n)
  - From repeated observations
  - Random flakiness: race conditions, timing, resource contention
  - Fix with: retries, synchronization

Type B (systematic): u_B(x) = a/sqrt(3) (rectangular) or a/sqrt(6) (triangular)
  - From calibration certificates, manufacturer specs, professional judgment
  - Systematic flakiness: wrong expected values, missing mocks, stale data
  - Fix with: test logic redesign

Combined: u_c(y) = sqrt(u_A^2 + u_B^2 + 2*r_AB*u_A*u_B)

Key diagnostic:
  - Consistent failure rate across environments → Type A
  - Always fails in one environment → Type B
  - If Type A dominant → add retries
  - If Type B dominant → fix test logic
  - If mixed → address Type B first (higher impact)
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from calibre.models import (
    FlakinessClassification,
    TestResult,
    TestRun,
    UncertaintyType,
)


def compute_type_a_uncertainty(observations: List[float]) -> float:
    """Compute Type A uncertainty from repeated observations.

    u_A = s(x_bar) = s(x) / sqrt(n)
    """
    n = len(observations)
    if n < 2:
        return 0.0

    mean = sum(observations) / n
    variance = sum((x - mean) ** 2 for x in observations) / (n - 1)
    std_dev = variance ** 0.5
    return std_dev / math.sqrt(n)


def compute_type_b_uncertainty_rectangular(half_width: float) -> float:
    """Compute Type B uncertainty assuming rectangular distribution.

    u_B = a / sqrt(3)
    where a is the half-width of the distribution.
    """
    return half_width / math.sqrt(3)


def compute_type_b_uncertainty_triangular(half_width: float) -> float:
    """Compute Type B uncertainty assuming triangular distribution.

    u_B = a / sqrt(6)
    """
    return half_width / math.sqrt(6)


def compute_combined_ab_uncertainty(
    u_a: float, u_b: float, correlation: float = 0.0
) -> float:
    """Compute combined uncertainty from Type A and Type B.

    u_c = sqrt(u_A^2 + u_B^2 + 2*r_AB*u_A*u_B)
    """
    variance = u_a**2 + u_b**2 + 2 * correlation * u_a * u_b
    return math.sqrt(max(0.0, variance))


def classify_test(
    runs: List[TestRun], test_name: str
) -> FlakinessClassification:
    """Classify a test's flakiness as Type A (random) or Type B (systematic).

    Strategy:
    - Compute failure rates per environment
    - If failure rates are similar across envs → Type A (random)
    - If failure rate varies significantly by env → Type B (systematic)
    - Compute both uncertainty types and determine dominant
    """
    test_runs = [r for r in runs if r.test_name == test_name]
    if not test_runs:
        return FlakinessClassification(
            test_name=test_name,
            dominant_type=UncertaintyType.TYPE_A,
            remediation="No data available",
        )

    # Group by environment
    by_env: Dict[str, List[TestRun]] = {}
    for r in test_runs:
        by_env.setdefault(r.environment, []).append(r)

    # Compute failure rate per environment
    env_failure_rates: Dict[str, float] = {}
    for env, env_runs in by_env.items():
        failures = sum(1 for r in env_runs if not r.passed)
        env_failure_rates[env] = failures / len(env_runs)

    # Overall failure observations (0=fail, 1=pass)
    observations = [r.numeric_result for r in test_runs]

    # Type A: statistical uncertainty from repeated observations
    u_a = compute_type_a_uncertainty(observations)

    # Type B: systematic uncertainty from cross-environment variation
    # If one env always fails and others pass, that's systematic
    if len(env_failure_rates) >= 2:
        rates = list(env_failure_rates.values())
        rate_range = max(rates) - min(rates)
        # Use triangular distribution assumption for systematic component
        u_b = compute_type_b_uncertainty_triangular(rate_range / 2)
    elif len(env_failure_rates) == 1:
        # Only one environment — can't distinguish, assume Type A
        u_b = 0.0
    else:
        u_b = 0.0

    # Correlation between A and B (usually small)
    correlation_ab = 0.1

    # Combined
    u_combined = compute_combined_ab_uncertainty(u_a, u_b, correlation_ab)

    # Determine dominant type
    if u_a > u_b:
        dominant_type = UncertaintyType.TYPE_A
        remediation = "Type A (random) flakiness dominant → Add retries / add synchronization"
    elif u_b > u_a:
        dominant_type = UncertaintyType.TYPE_B
        remediation = "Type B (systematic) flakiness dominant → Fix test logic — retries won't help"
    else:
        dominant_type = UncertaintyType.TYPE_A
        remediation = "Mixed Type A/B → Address Type B first (higher impact)"

    # Cross-env vs single-env failure rates
    if env_failure_rates:
        cross_env_rate = sum(env_failure_rates.values()) / len(env_failure_rates)
        single_env_rate = max(env_failure_rates.values())
    else:
        cross_env_rate = 0.0
        single_env_rate = 0.0

    return FlakinessClassification(
        test_name=test_name,
        type_a_uncertainty=u_a,
        type_b_uncertainty=u_b,
        combined_uncertainty=u_combined,
        dominant_type=dominant_type,
        correlation_ab=correlation_ab,
        remediation=remediation,
        cross_env_failure_rate=cross_env_rate,
        single_env_failure_rate=single_env_rate,
    )


def format_classification(classification: FlakinessClassification) -> str:
    """Format a flakiness classification as a readable report."""
    lines: List[str] = []
    lines.append(f"{'='*60}")
    lines.append(f"Uncertainty Classification: {classification.test_name}")
    lines.append(f"{'='*60}")
    lines.append("")
    lines.append(f"  Type A (random):     u_A = {classification.type_a_uncertainty:.6f}")
    lines.append(f"  Type B (systematic): u_B = {classification.type_b_uncertainty:.6f}")
    lines.append(f"  Combined:            u_c = {classification.combined_uncertainty:.6f}")
    lines.append(f"  Correlation (A↔B):        {classification.correlation_ab:.2f}")
    lines.append("")
    lines.append(f"  Dominant type: {classification.dominant_type.value}")
    lines.append(f"  Cross-env failure rate: {classification.cross_env_failure_rate:.4f}")
    lines.append(f"  Single-env failure rate: {classification.single_env_failure_rate:.4f}")
    lines.append("")
    lines.append(f"  Remediation: {classification.remediation}")
    lines.append("")

    return "\n".join(lines)
