"""Damping coefficient computation.

Computes the damping ratio ζ for each pipeline stage to classify its
oscillation behavior and recommend adjustments for critical damping (ζ ≈ 1.0).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ussy_cavity.topology import PipelineTopology


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class DampingClass(Enum):
    """Classification of damping behavior."""

    UNDAMPED = "UNDAMPED"  # ζ ≈ 0 — pure deadlock
    UNDERDAMPED = "UNDERDAMPED"  # ζ < 1 — oscillating backpressure
    CRITICALLY_DAMPED = "CRITICALLY_DAMPED"  # ζ ≈ 1 — optimal
    OVERDAMPED = "OVERDAMPED"  # ζ > 1 — slow response


@dataclass
class DampingResult:
    """Damping analysis result for a single stage."""

    stage_name: str
    zeta: float  # Damping ratio
    damping_class: DampingClass
    backoff_rate: float  # c
    contention_strength: float  # k
    work_inertia: float  # m
    recommendation: str = ""

    def summary(self) -> str:
        return (
            f"Stage '{self.stage_name}': ζ={self.zeta:.4f} "
            f"({self.damping_class.value}), "
            f"c={self.backoff_rate:.4f}, k={self.contention_strength:.4f}, "
            f"m={self.work_inertia:.4f}"
        )


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------


def compute_damping_ratio(
    backoff_rate: float,
    contention_strength: float,
    work_inertia: float,
) -> float:
    """Compute damping ratio ζ = c / (2√(k·m)).

    Parameters
    ----------
    backoff_rate : float
        c — timeout + retry delay per cycle (seconds/cycle).
    contention_strength : float
        k — inverse of lock granularity (1/lock_count or similar).
    work_inertia : float
        m — average work item size × processing time.

    Returns
    -------
    float
        Damping ratio ζ.
    """
    product = contention_strength * work_inertia
    if product < 1e-15:
        return 0.0
    return backoff_rate / (2.0 * (product ** 0.5))


def classify_damping_class(zeta: float) -> DampingClass:
    """Classify a damping ratio into a damping class."""
    if zeta < 0.05:
        return DampingClass.UNDAMPED
    if zeta < 0.95:
        return DampingClass.UNDERDAMPED
    if zeta <= 1.05:
        return DampingClass.CRITICALLY_DAMPED
    return DampingClass.OVERDAMPED


def recommend_adjustment(zeta: float, target: float = 1.0) -> str:
    """Generate a recommendation for adjusting damping toward the target.

    Parameters
    ----------
    zeta : float
        Current damping ratio.
    target : float
        Target damping ratio (default 1.0 = critical damping).

    Returns
    -------
    str
        Human-readable recommendation.
    """
    if abs(zeta - target) < 0.1:
        return "Damping is near optimal — no adjustment needed."

    if zeta < 0.5:
        return (
            f"ζ={zeta:.2f} is too low. Increase backoff rate "
            f"(add time.sleep / exponential jitter) to improve damping. "
            f"Target: ζ≈{target:.1f}"
        )

    if zeta < target - 0.1:
        return (
            f"ζ={zeta:.2f} is slightly below target. "
            f"Consider modest backoff increase. Target: ζ≈{target:.1f}"
        )

    if zeta > 2.0:
        return (
            f"ζ={zeta:.2f} is too high. Decrease backoff rate "
            f"(reduce timeout, remove unnecessary delays) to improve throughput. "
            f"Target: ζ≈{target:.1f}"
        )

    if zeta > target + 0.1:
        return (
            f"ζ={zeta:.2f} is slightly above target. "
            f"Consider modest backoff decrease. Target: ζ≈{target:.1f}"
        )

    return "Damping is near target — no adjustment needed."


def analyze_stage_damping(
    topology: PipelineTopology,
    target_zeta: float = 1.0,
) -> list[DampingResult]:
    """Analyze damping for all stages in a topology.

    Derives c, k, m from topology properties:
    - c (backoff_rate) = estimated from rate and buffer (retry delay ~ buffer/rate)
    - k (contention_strength) = 1 / num_locks_held (or 1.0 if no locks)
    - m (work_inertia) = (1/rate) × buffer  (processing time × item count)

    Parameters
    ----------
    topology : PipelineTopology
        Pipeline topology to analyze.
    target_zeta : float
        Target damping ratio for recommendations.

    Returns
    -------
    list[DampingResult]
    """
    results: list[DampingResult] = []

    for name, stage in topology.stages.items():
        # Derive backoff rate: estimated retry delay
        if stage.rate > 0:
            backoff_rate = stage.buffer / stage.rate  # seconds per cycle
        else:
            backoff_rate = 0.0

        # Contention strength: inverse of lock count
        num_locks = len(stage.locks) if stage.locks else 1
        contention_strength = 1.0 / num_locks

        # Work inertia: processing time × buffer size
        if stage.rate > 0:
            work_inertia = (1.0 / stage.rate) * stage.buffer
        else:
            work_inertia = float(stage.buffer)

        zeta = compute_damping_ratio(backoff_rate, contention_strength, work_inertia)
        dclass = classify_damping_class(zeta)
        rec = recommend_adjustment(zeta, target_zeta)

        results.append(
            DampingResult(
                stage_name=name,
                zeta=zeta,
                damping_class=dclass,
                backoff_rate=backoff_rate,
                contention_strength=contention_strength,
                work_inertia=work_inertia,
                recommendation=rec,
            )
        )

    return results


def format_damping_results(results: list[DampingResult]) -> str:
    """Format damping results for display."""
    lines: list[str] = []
    if not results:
        lines.append("No stages to analyze.")
        return "\n".join(lines)

    lines.append(f"Damping Analysis ({len(results)} stages)")
    lines.append("=" * 60)
    for result in results:
        lines.append(result.summary())
        if result.recommendation:
            lines.append(f"  → {result.recommendation}")
    return "\n".join(lines)
