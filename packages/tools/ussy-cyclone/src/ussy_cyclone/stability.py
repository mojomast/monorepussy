"""Stability analysis — Richardson number and baroclinic instability.

Baroclinic instability occurs when there are large throughput differences
between adjacent pipeline stages. The Richardson number quantifies this:

    Ri = (load_stability)² / (throughput_gradient)²

When Ri < 0.25 (critical Richardson number), the pipeline is baroclinically
unstable — large throughput differences will cause cascading failures.

Pipeline mapping:
- load_stability: stability of queue depth (variance in load)
- throughput_gradient: difference in throughput between adjacent stages
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from ussy_cyclone.models import PipelineStage, PipelineTopology, StabilityReading


CRITICAL_RICHARDSON = 0.25


def compute_richardson_number(
    stage_a: PipelineStage,
    stage_b: PipelineStage,
) -> StabilityReading:
    """Compute the Richardson number at the boundary between two stages.

    Ri = (load_stability)² / (throughput_gradient)²

    Where:
    - load_stability = average load variance across both stages
    - throughput_gradient = difference in total throughput

    Ri < 0.25 → baroclinic instability
    """
    # Load stability: based on queue depth / consumer ratio
    load_a = stage_a.load_variance
    load_b = stage_b.load_variance
    load_stability = (load_a + load_b) / 2.0

    # Throughput gradient: difference in throughput
    throughput_a = stage_a.total_throughput
    throughput_b = stage_b.total_throughput
    throughput_gradient = abs(throughput_a - throughput_b)

    # Richardson number
    if throughput_gradient > 0:
        ri = (load_stability ** 2) / (throughput_gradient ** 2)
    else:
        # No gradient → infinitely stable (or undefined, treat as stable)
        ri = float("inf")

    boundary = f"{stage_a.name} → {stage_b.name}"

    return StabilityReading(
        boundary=boundary,
        richardson_number=ri,
        throughput_gradient=throughput_gradient,
        load_stability=load_stability,
    )


def compute_all_stability(
    topology: PipelineTopology,
) -> List[StabilityReading]:
    """Compute Richardson number at every stage boundary.

    Returns stability readings for all adjacent stage pairs.
    """
    readings: List[StabilityReading] = []
    seen_boundaries: set = set()

    for src, dst in topology.edges:
        if src in topology.stages and dst in topology.stages:
            boundary_key = (src, dst)
            if boundary_key not in seen_boundaries:
                seen_boundaries.add(boundary_key)
                reading = compute_richardson_number(
                    topology.stages[src], topology.stages[dst]
                )
                readings.append(reading)

    return readings


def find_unstable_boundaries(
    topology: PipelineTopology,
    critical: float = CRITICAL_RICHARDSON,
) -> List[StabilityReading]:
    """Find all stage boundaries with Ri below the critical threshold.

    These are the locations where baroclinic instability could trigger
    cyclonic activity.
    """
    all_readings = compute_all_stability(topology)
    return [r for r in all_readings if r.richardson_number < critical]


def compute_wind_shear(
    stage_a: PipelineStage,
    stage_b: PipelineStage,
) -> float:
    """Compute wind shear between two adjacent stages.

    Wind shear = velocity difference between adjacent stages.
    High shear → potential for instability.
    """
    du = stage_a.forward_rate - stage_b.forward_rate
    dv = stage_a.reprocessing_rate - stage_b.reprocessing_rate
    return (du ** 2 + dv ** 2) ** 0.5


def format_stability(
    readings: List[StabilityReading],
    critical_only: bool = False,
) -> str:
    """Format stability analysis as a human-readable string."""
    lines: List[str] = []

    lines.append("🔬 Stability Analysis — Richardson Number")
    lines.append("=" * 55)

    if critical_only:
        lines.append("  Showing only unstable boundaries (Ri < 0.25)")
        display = [r for r in readings if r.is_unstable]
    else:
        display = readings

    if not display:
        lines.append("")
        if critical_only:
            lines.append("  No unstable boundaries detected. Pipeline is stable.")
        else:
            lines.append("  No stage boundaries found to analyze.")
        return "\n".join(lines)

    lines.append("")
    lines.append(f"  {'Boundary':<30} {'Ri':>8} {'Shear':>10} {'Status':<15}")
    lines.append("  " + "-" * 63)

    for r in display:
        status = "⚠ UNSTABLE" if r.is_unstable else "Stable"
        lines.append(
            f"  {r.boundary:<30} {r.richardson_number:>8.3f} "
            f"{r.throughput_gradient:>10.1f} {status:<15}"
        )

    lines.append("")
    lines.append("=" * 55)
    return "\n".join(lines)
