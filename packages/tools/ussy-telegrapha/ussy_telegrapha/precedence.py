"""Message Precedence — Priority Queue Optimization.

Applies Signal Corps FLASH/IMMEDIATE/PRIORITY/ROUTINE system with
M/G/1 preemptive priority queue formulas.
"""

from __future__ import annotations

import math
from typing import Any

from .models import PrecedenceClass, PrecedenceResult

# Signal Corps precedence labels
PRECEDENCE_LABELS = ["FLASH", "IMMEDIATE", "PRIORITY", "ROUTINE"]


def compute_mg1_avg_wait(
    arrival_rate: float,
    service_time: float,
    higher_class_load: float,
    residual_service: float,
) -> float:
    """Compute average waiting time for a class in M/G/1 priority queue.

    Uses the M/G/1 conservation law and priority queue formulas:
    W_k = (R / (1 - sigma_{i<k} rho_i)) + sum of higher class contributions

    Simplified for preemptive priority:
    W_k ≈ residual_service / (1 - sum(rho_i for i < k))
         + higher_class_preemption_overhead

    Args:
        arrival_rate: Arrival rate (lambda) for this class.
        service_time: Mean service time (1/mu) for this class.
        higher_class_load: Sum of utilization for higher-priority classes.
        residual_service: Mean residual service time (R = lambda * E[S^2] / 2).
    """
    rho_k = arrival_rate * service_time
    denominator = 1.0 - higher_class_load

    if denominator <= 0:
        return float("inf")  # System unstable

    # Average wait = residual / (1 - sigma_{i<k} rho_i)
    wait = residual_service / denominator
    return wait


def compute_system_stability(classes: list[PrecedenceClass]) -> float:
    """Compute total system utilization (rho = sum of lambda_i * service_time_i).

    System is stable if rho < 1.0.
    """
    return sum(c.arrival_rate * c.service_time for c in classes)


def compute_residual_service_time(classes: list[PrecedenceClass]) -> float:
    """Compute mean residual service time for M/G/1.

    R = sum(lambda_i * E[S_i^2]) / 2

    Assuming service time variance is service_time^2 (exponential):
    E[S^2] = 2 * (service_time)^2 for exponential distribution
    R = sum(lambda_i * 2 * service_time_i^2) / 2 = sum(lambda_i * service_time_i^2)
    """
    return sum(c.arrival_rate * c.service_time ** 2 for c in classes)


def find_optimal_class_count(
    base_classes: list[PrecedenceClass],
    max_classes: int = 8,
    marginal_threshold: float = 0.02,
) -> int:
    """Find optimal number of priority classes.

    The marginal gain of adding another class diminishes.
    Optimal count is where adding one more class gives < marginal_threshold improvement.
    """
    current_count = len(base_classes)
    if current_count <= 1:
        return max(1, current_count)

    # Compute the marginal improvement of each additional class
    # We approximate: more classes = better tail latency separation
    # but with diminishing returns
    best_count = current_count

    for n in range(current_count, max_classes + 1):
        # Marginal gain of nth class: approximately 1/n^2 (diminishing returns)
        if n > 1:
            marginal_gain = 1.0 / (n ** 2)
            if marginal_gain < marginal_threshold:
                best_count = n - 1
                break
    else:
        best_count = max_classes

    return max(1, best_count)


def analyze_precedence(
    classes: list[PrecedenceClass],
    marginal_threshold: float = 0.02,
) -> PrecedenceResult:
    """Perform full precedence analysis with M/G/1 priority queue model.

    Args:
        classes: List of priority classes sorted by precedence (highest first).
        marginal_threshold: Threshold for marginal gain of additional classes.

    Returns:
        PrecedenceResult with wait times, stability analysis, and recommendations.
    """
    # Compute wait times for each class
    residual = compute_residual_service_time(classes)
    higher_load = 0.0

    for cls in classes:
        cls.avg_wait = compute_mg1_avg_wait(
            cls.arrival_rate,
            cls.service_time,
            higher_load,
            residual,
        )
        higher_load += cls.arrival_rate * cls.service_time

    # System stability
    stability = compute_system_stability(classes)

    # Optimal class count
    optimal_count = find_optimal_class_count(classes, marginal_threshold=marginal_threshold)

    # Recommendations
    recommendations: list[str] = []

    if stability >= 1.0:
        recommendations.append(
            f"System UNSTABLE: σ={stability:.2f} ≥ 1.0 — "
            f"reduce arrival rates or increase service capacity"
        )
    elif stability > 0.8:
        recommendations.append(
            f"System approaching instability: σ={stability:.2f} — "
            f"consider adding capacity or reducing load"
        )

    # Preemption analysis for FLASH class
    flash_classes = [c for c in classes if c.label == "FLASH"]
    for fc in flash_classes:
        if fc.preemption_overhead > 0:
            # Preemption is worth it if it saves more tail latency than it costs
            routine_waits = [
                c.avg_wait for c in classes if c.label in ("ROUTINE", "PRIORITY")
            ]
            max_routine_wait = max(routine_waits) if routine_waits else 0
            if fc.preemption_overhead < max_routine_wait * 0.1:
                recommendations.append(
                    f"Preemption IS worth it for {fc.name}: "
                    f"{fc.preemption_overhead * 1000:.0f}ms overhead saves "
                    f"significant tail latency"
                )
            else:
                recommendations.append(
                    f"Preemption overhead for {fc.name} may not be justified: "
                    f"{fc.preemption_overhead * 1000:.0f}ms overhead"
                )

    if optimal_count < len(classes):
        recommendations.append(
            f"Optimal class count: {optimal_count} "
            f"(marginal gain of {len(classes)}th class < {marginal_threshold:.0%})"
        )

    return PrecedenceResult(
        classes=classes,
        optimal_class_count=optimal_count,
        system_stability=stability,
        is_stable=stability < 1.0,
        recommendations=recommendations,
    )


def format_precedence_report(result: PrecedenceResult) -> str:
    """Format precedence result as a human-readable report."""
    lines: list[str] = []

    lines.append("Precedence Analysis (M/G/1 Priority Queue):")
    lines.append("")

    for i, cls in enumerate(result.classes, 1):
        lines.append(f"  Class {i} ({cls.label}): {cls.name}")
        lines.append(
            f"    Arrival rate: {cls.arrival_rate:.1f}/min, "
            f"Service time: {cls.service_time * 1000:.0f}ms"
        )
        if cls.avg_wait == float("inf"):
            lines.append("    Avg wait: ∞ (system unstable)")
        else:
            lines.append(f"    Avg wait: {cls.avg_wait * 1000:.0f}ms")
        if cls.preemption_overhead > 0:
            lines.append(f"    Preemption overhead: {cls.preemption_overhead * 1000:.0f}ms")

    lines.append("")
    lines.append(
        f"  Optimal class count: {result.optimal_class_count}"
    )
    lines.append(
        f"  System stability: σ = {result.system_stability:.2f} "
        f"({'healthy' if result.is_stable else 'UNSTABLE'}, < 1.0)"
    )

    for r in result.recommendations:
        lines.append(f"  → {r}")

    return "\n".join(lines)


def precedence_to_dict(result: PrecedenceResult) -> dict[str, Any]:
    """Convert precedence result to a JSON-serializable dictionary."""
    return {
        "optimal_class_count": result.optimal_class_count,
        "system_stability": round(result.system_stability, 4),
        "is_stable": result.is_stable,
        "recommendations": result.recommendations,
        "classes": [
            {
                "name": c.name,
                "label": c.label,
                "arrival_rate": c.arrival_rate,
                "service_time": c.service_time,
                "avg_wait": round(c.avg_wait, 6) if c.avg_wait != float("inf") else "inf",
                "preemption_overhead": c.preemption_overhead,
            }
            for c in result.classes
        ],
    }
