"""Callus formation — Adapter generation dynamics."""

from __future__ import annotations

import math

from ussy_cambium.models import CallusDynamics


def compute_callus_dynamics(
    total_mismatches: int,
    initially_resolved: int = 2,
    generation_rate: float = 0.5,
    test_pass_rate: float = 0.0,
) -> CallusDynamics:
    """Create a CallusDynamics model from adapter analysis parameters."""
    return CallusDynamics(
        k_adapter=float(total_mismatches),
        n0=float(max(initially_resolved, 1)),
        r_gen=generation_rate,
        test_pass_rate=test_pass_rate,
    )


def estimate_adapter_mismatches(
    consumer_methods: set[str],
    provider_methods: set[str],
) -> int:
    """Estimate total mismatches requiring adapters from method name differences."""
    consumer_only = consumer_methods - provider_methods
    return len(consumer_only)


def compute_adapter_quality(
    test_cases_passed: list[int],
    test_cases_total: list[int],
) -> float:
    """Compute adapter quality Q_adapter.

    Q_adapter = Σ_a (test_cases_passed(a) / test_cases_total(a)) / |adapters|

    A low Q means adapters compile but fail on edge cases — "undifferentiated callus."
    """
    if not test_cases_total:
        return 1.0  # no test data = assume perfect by default

    scores: list[float] = []
    for passed, total in zip(test_cases_passed, test_cases_total):
        if total == 0:
            scores.append(0.0)
        else:
            scores.append(passed / total)

    return sum(scores) / len(scores) if scores else 0.0


def callus_trajectory(dynamics: CallusDynamics, time_points: list[float]) -> list[dict]:
    """Generate callus growth trajectory at specified time points."""
    result: list[dict] = []
    for t in time_points:
        resolved = dynamics.callus_at(t)
        remaining = dynamics.k_adapter - resolved
        quality = dynamics.adapter_quality
        result.append({
            "time": round(t, 2),
            "adapters_resolved": round(resolved, 2),
            "adapters_remaining": round(max(remaining, 0), 2),
            "quality": round(quality, 2),
        })
    return result


def format_callus_report(dynamics: CallusDynamics) -> str:
    """Format a callus/adapter dynamics report."""
    lines: list[str] = []
    lines.append("Adapter Generation Dynamics (Callus Formation Model)")
    lines.append("─" * 50)
    lines.append(f"  Total mismatches (K):         {dynamics.k_adapter:.0f}")
    lines.append(f"  Initially resolved (N₀):      {dynamics.n0:.0f}")
    lines.append(f"  Generation rate (r):           {dynamics.r_gen:.2f}")
    lines.append(f"  Bridging time:                 {dynamics.bridging_time:.1f} months")
    lines.append(f"  Adapter quality (Q):           {dynamics.adapter_quality:.2f}", )

    if dynamics.adapter_quality < 0.5:
        lines.append("  ⚠️  Low adapter quality — undifferentiated callus!")
    elif dynamics.adapter_quality < 0.8:
        lines.append("  ⚡ Partial adapter quality — some fragile adapters")
    else:
        lines.append("  ✅ Good adapter quality — well-differentiated tissue")

    lines.append("")
    lines.append("  Trajectory:")
    for point in callus_trajectory(dynamics, [0, 1, 2, 4, 8, 12, 18, 24]):
        bar_len = int(point["adapters_resolved"] / max(dynamics.k_adapter, 1) * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        lines.append(f"    t={point['time']:5.1f}m  {bar}  {point['adapters_resolved']:.1f}/{dynamics.k_adapter:.0f}")

    return "\n".join(lines)
