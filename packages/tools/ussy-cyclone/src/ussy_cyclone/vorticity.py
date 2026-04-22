"""Vorticity computation for pipeline stages.

Computes the 2D velocity field and derives vorticity using a hybrid approach
combining intrinsic rotation (reprocessing) with gradient-based enhancement.

Core model:
    ζ = intrinsic_rotation + gradient_enhancement

Where:
    intrinsic_rotation = reprocessing_fraction × scale_factor
    
This reflects the physical insight that reprocessing IS rotation — data
cycling back through a stage creates the same effect as cyclonic circulation.

Gradient enhancement captures developing cyclones where reprocessing is
increasing across stages (analogous to a low-pressure system building).

Also computes:
    - Absolute vorticity: η = ζ + f (Coriolis parameter)
    - Divergence: ∇·V (convergence = data accumulating)
    - Potential vorticity: PV = η / H
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ussy_cyclone.models import (
    CycloneCategory,
    PipelineStage,
    PipelineTopology,
    VorticityReading,
    classify_vorticity,
)

# Scale factor: maps reprocessing_fraction [0, 1] to vorticity range [0, 10]
# This ensures the Saffir-Simpson thresholds (0.5, 1.0, 2.0, 3.0) map to
# meaningful reprocessing fractions (5%, 10%, 20%, 30%)
INTRINSIC_SCALE = 10.0

# Scale factor for gradient enhancement
GRADIENT_SCALE = 10.0


def compute_stage_vorticity(
    stage: PipelineStage,
    upstream_stages: Optional[List[PipelineStage]] = None,
    downstream_stages: Optional[List[PipelineStage]] = None,
) -> VorticityReading:
    """Compute vorticity at a single pipeline stage.

    Uses a hybrid model:
    1. Intrinsic rotation from reprocessing fraction (primary signal)
    2. Gradient enhancement from reprocessing changes across stages
    
    In meteorology, vorticity at a point depends on the surrounding wind field.
    For pipelines, reprocessing IS the local rotation — data cycling back through
    a stage is the direct analog of cyclonic circulation.
    """
    # Primary vorticity: reprocessing creates intrinsic rotation
    zeta = stage.reprocessing_fraction * INTRINSIC_SCALE

    # Gradient enhancement: increasing reprocessing downstream suggests
    # a developing cyclone (like a low-pressure system intensifying)
    if downstream_stages:
        avg_v_downstream = sum(s.reprocessing_rate for s in downstream_stages) / len(downstream_stages)
        # If downstream has higher reprocessing, cyclone is building
        if avg_v_downstream > stage.reprocessing_rate:
            gradient_boost = (avg_v_downstream - stage.reprocessing_rate) / max(stage.total_throughput, 1.0)
            zeta += gradient_boost * GRADIENT_SCALE
    elif upstream_stages:
        # If this stage has higher reprocessing than upstream, it's the cyclone center
        avg_v_upstream = sum(s.reprocessing_rate for s in upstream_stages) / len(upstream_stages)
        if stage.reprocessing_rate > avg_v_upstream:
            gradient_boost = (stage.reprocessing_rate - avg_v_upstream) / max(stage.total_throughput, 1.0)
            zeta += gradient_boost * GRADIENT_SCALE

    # Coriolis parameter
    f = stage.coriolis_parameter

    # Absolute vorticity
    eta = zeta + f

    # Divergence: negative = convergence (data accumulating)
    # Computed as throughput change ratio between this stage and downstream
    if downstream_stages:
        avg_u_downstream = sum(s.forward_rate for s in downstream_stages) / len(downstream_stages)
        throughput_ratio = avg_u_downstream / max(stage.forward_rate, 1.0)
        divergence = (throughput_ratio - 1.0) * INTRINSIC_SCALE
    else:
        divergence = 0.0

    # Potential vorticity: PV = η / H
    H = max(stage.queue_depth, 1)
    pv = eta / H

    # Classify
    category = classify_vorticity(zeta, stage.reprocessing_fraction)

    return VorticityReading(
        stage_name=stage.name,
        zeta=zeta,
        absolute_vorticity=eta,
        divergence=divergence,
        timestamp=datetime.now(timezone.utc),
        pv=pv,
        category=category,
    )


def compute_vorticity_field(topology: PipelineTopology) -> Dict[str, VorticityReading]:
    """Compute vorticity at every stage in the pipeline topology.

    Returns a mapping from stage name to VorticityReading.
    """
    downstream_map = topology.downstream
    upstream_map = topology.upstream
    readings: Dict[str, VorticityReading] = {}

    for name, stage in topology.stages.items():
        downstream = [
            topology.stages[ds]
            for ds in downstream_map.get(name, [])
            if ds in topology.stages
        ]
        upstream = [
            topology.stages[us]
            for us in upstream_map.get(name, [])
            if us in topology.stages
        ]
        readings[name] = compute_stage_vorticity(stage, upstream, downstream)

    return readings


def compute_vorticity_change(
    current: Dict[str, VorticityReading],
    previous: Dict[str, VorticityReading],
) -> Dict[str, float]:
    """Compute the change in vorticity (dζ/dt) between two readings.

    Positive values mean vorticity is intensifying (cyclone forming).
    """
    changes: Dict[str, float] = {}
    for name in current:
        if name in previous:
            changes[name] = current[name].zeta - previous[name].zeta
    return changes


def format_vorticity(readings: Dict[str, VorticityReading], mode: str = "summary") -> str:
    """Format vorticity readings as a human-readable string.

    Args:
        readings: Mapping of stage name to VorticityReading.
        mode: 'summary' for compact, 'full' for detailed, or stage name for single stage.
    """
    lines: List[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines.append("┌" + "─" * 62 + "┐")
    lines.append(f"│  CYCLONE — Vorticity Analysis — {now}" + " " * (62 - 38 - len(now)) + "│")
    lines.append("│" + " " * 62 + "│")

    # Stage flow line
    stage_names = list(readings.keys())
    if stage_names:
        flow_line = " → ".join(stage_names)
        lines.append(f"│  {flow_line}" + " " * max(0, 62 - 2 - len(flow_line)) + "│")
        lines.append("│" + " " * 62 + "│")

        # Vorticity line
        zeta_parts = []
        for name in stage_names:
            r = readings[name]
            marker = ""
            if r.category.value >= 3:
                marker = "⚡"
            elif r.category.value >= 2:
                marker = "⚠"
            zeta_parts.append(f"{r.zeta:+.1f}{marker}")
        zeta_line = "  ζ:  " + "   ".join(zeta_parts)
        lines.append(f"│{zeta_line}" + " " * max(0, 62 - len(zeta_line)) + "│")

        # Category line
        cat_parts = []
        for name in stage_names:
            r = readings[name]
            cat_parts.append(r.category.label.lower())
        cat_line = "  " + "  ".join(cat_parts)
        lines.append(f"│{cat_line}" + " " * max(0, 62 - len(cat_line)) + "│")

    lines.append("│" + " " * 62 + "│")

    # Alerts
    alerts = [
        (name, r) for name, r in readings.items()
        if r.category.value >= CycloneCategory.STORM.value
    ]
    if alerts:
        for name, r in alerts:
            if r.category.value >= CycloneCategory.SEVERE_STORM.value:
                symbol = "⚡"
            else:
                symbol = "⚠"
            status = "accelerating" if r.zeta > 0 else "decelerating"
            lines.append(f"│  {symbol} {r.category.label}: {name} stage ({r.category.label})")
            lines.append(f"│    Vorticity: ζ = {r.zeta:+.2f} ({status})")
            if r.divergence < 0:
                lines.append(f"│    Convergence: {r.divergence:.2f} (data accumulating)")
            lines.append("│")

    lines.append("└" + "─" * 62 + "┘")
    return "\n".join(lines)
