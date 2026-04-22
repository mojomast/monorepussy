"""Cyclone detection — identify active cyclonic formations.

Detects cyclonic formations by analyzing vorticity fields, convergence zones,
and CISK conditions. A cyclone is detected when:
- Relative vorticity ζ > 0 (rotation present)
- Divergence < 0 (convergence, data accumulating)
- CISK cycle may be present (positive feedback)

Tracking assigns IDs and monitors cyclone evolution over time.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ussy_cyclone.models import (
    CycloneCategory,
    CycloneDetection,
    PipelineTopology,
    VorticityReading,
    classify_vorticity,
)
from ussy_cyclone.vorticity import compute_vorticity_field


# Thresholds for cyclone detection
VORTICITY_THRESHOLD = 0.5
CONVERGENCE_THRESHOLD = 0.0


def detect_cyclones(
    topology: PipelineTopology,
    readings: Optional[Dict[str, VorticityReading]] = None,
    cisk_cycles: Optional[List[List[str]]] = None,
    cycle_gains: Optional[Dict[Tuple[str, ...], float]] = None,
) -> List[CycloneDetection]:
    """Detect cyclonic formations in the pipeline.

    Args:
        topology: The pipeline topology.
        readings: Pre-computed vorticity readings (computed if not provided).
        cisk_cycles: Pre-detected CISK cycles (optional).
        cycle_gains: Pre-computed cycle gains keyed by cycle tuple.

    Returns:
        List of CycloneDetection objects for active cyclones.
    """
    if readings is None:
        readings = compute_vorticity_field(topology)

    if cycle_gains is None:
        cycle_gains = {}

    detections: List[CycloneDetection] = []
    cyclone_id_counter = 0

    for name, reading in readings.items():
        # A cyclone requires positive vorticity above threshold
        if reading.zeta < VORTICITY_THRESHOLD:
            continue

        stage = topology.get_stage(name)
        if stage is None:
            continue

        # Check for convergence (data accumulating)
        has_convergence = reading.divergence < CONVERGENCE_THRESHOLD

        # Find CISK cycle if available
        cisk_cycle = None
        cycle_gain = 0.0
        if cisk_cycles:
            for cycle in cisk_cycles:
                if name in cycle:
                    cisk_cycle = cycle
                    cycle_key = tuple(cycle)
                    cycle_gain = cycle_gains.get(cycle_key, 0.0)
                    break

        # Find affected stages (stages with elevated vorticity nearby)
        affected = _find_affected_stages(name, topology, readings)

        # Classify severity
        category = classify_vorticity(reading.zeta, stage.reprocessing_fraction)

        # Upgrade category if CISK detected
        if cisk_cycle and cycle_gain > 1.0 and category.value < CycloneCategory.SEVERE_STORM.value:
            category = CycloneCategory.SEVERE_STORM

        # Upgrade if cascading across multiple stages
        if len(affected) > 2 and category.value < CycloneCategory.CYCLONE.value:
            category = CycloneCategory(max(category.value, CycloneCategory.CYCLONE.value))

        # Generate ID
        id_str = f"cyclone-{name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
        cyclone_id = hashlib.md5(id_str.encode()).hexdigest()[:8]

        detection = CycloneDetection(
            id=cyclone_id,
            center_stage=name,
            category=category,
            vorticity=reading.zeta,
            stages_affected=affected,
            cisk_cycle=cisk_cycle,
            cycle_gain=cycle_gain,
            dlq_depth=stage.dlq_depth,
            timestamp=datetime.now(timezone.utc),
        )
        detections.append(detection)

    return detections


def _find_affected_stages(
    center: str,
    topology: PipelineTopology,
    readings: Dict[str, VorticityReading],
) -> List[str]:
    """Find stages affected by a cyclone centered at the given stage.

    Includes the center and any directly connected stages with elevated vorticity.
    """
    affected = [center]
    downstream = topology.downstream.get(center, [])
    upstream = topology.upstream.get(center, [])

    for neighbor in downstream + upstream:
        if neighbor in readings and readings[neighbor].zeta > VORTICITY_THRESHOLD * 0.5:
            affected.append(neighbor)

    return affected


def track_cyclone(
    detections: List[CycloneDetection],
    cyclone_id: str,
) -> Optional[CycloneDetection]:
    """Find a specific cyclone by ID."""
    for d in detections:
        if d.id == cyclone_id:
            return d
    return None


def format_detection(detections: List[CycloneDetection]) -> str:
    """Format cyclone detections as a human-readable string."""
    lines: List[str] = []

    if not detections:
        lines.append("No active cyclonic formations detected. Pipeline is calm. 🌤️")
        return "\n".join(lines)

    lines.append("⚡ CYCLONE DETECTION REPORT")
    lines.append("=" * 50)

    for d in detections:
        lines.append("")
        lines.append(f"  {d.category.emoji} {d.severity_label}")
        lines.append(f"  ID: {d.id}")
        lines.append(f"  Center: {d.center_stage}")
        lines.append(f"  Vorticity: ζ = {d.vorticity:+.2f}")
        lines.append(f"  Stages affected: {', '.join(d.stages_affected)}")
        if d.cisk_cycle:
            lines.append(f"  CISK cycle: {' → '.join(d.cisk_cycle)}")
            lines.append(f"  Cycle gain: {d.cycle_gain:.2f}x")
        if d.dlq_depth > 0:
            lines.append(f"  DLQ depth: {d.dlq_depth:,} messages")
        lines.append(f"  Detected: {d.timestamp.strftime('%Y-%m-%d %H:%M UTC')}")

    lines.append("")
    lines.append("=" * 50)
    return "\n".join(lines)
