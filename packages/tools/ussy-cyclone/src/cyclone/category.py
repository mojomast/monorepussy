"""Saffir-Simpson severity classification for pipeline cyclones.

Category 1 (Depression):   ζ > 0, reprocessing < 5% of throughput
Category 2 (Storm):        ζ > threshold_1, reprocessing 5-15%
Category 3 (Severe Storm): ζ > threshold_2, reprocessing 15-30%, CISK detected
Category 4 (Cyclone):      ζ > threshold_3, reprocessing 30-50%, cascading across >2 stages
Category 5 (Hurricane):    ζ > threshold_4, reprocessing >50%, pipeline effectively stalled
"""

from __future__ import annotations

from typing import Dict, List, Optional

from cyclone.models import (
    CycloneCategory,
    CycloneDetection,
    PipelineTopology,
    VorticityReading,
    classify_vorticity,
)
from cyclone.vorticity import compute_vorticity_field


def classify_pipeline(
    topology: PipelineTopology,
    readings: Optional[Dict[str, VorticityReading]] = None,
    cisk_cycles: Optional[List[List[str]]] = None,
) -> Dict[str, CycloneCategory]:
    """Classify each pipeline stage by cyclone severity.

    Args:
        topology: Pipeline topology.
        readings: Pre-computed vorticity readings (computed if not provided).
        cisk_cycles: CISK cycles to upgrade categories.

    Returns:
        Mapping from stage name to CycloneCategory.
    """
    if readings is None:
        readings = compute_vorticity_field(topology)

    categories: Dict[str, CycloneCategory] = {}

    cisk_stages: set = set()
    if cisk_cycles:
        for cycle in cisk_cycles:
            for stage in cycle:
                cisk_stages.add(stage)

    for name, reading in readings.items():
        stage = topology.stages.get(name)
        if stage is None:
            categories[name] = CycloneCategory.CALM
            continue

        cat = classify_vorticity(reading.zeta, stage.reprocessing_fraction)

        # Upgrade to Severe Storm if CISK detected
        if name in cisk_stages and cat.value < CycloneCategory.SEVERE_STORM.value:
            cat = CycloneCategory.SEVERE_STORM

        # Upgrade to Cyclone if affecting >2 stages
        if cat.value >= CycloneCategory.STORM.value:
            # Count affected downstream stages
            affected = _count_cascading_stages(name, topology, readings)
            if affected > 2 and cat.value < CycloneCategory.CYCLONE.value:
                cat = CycloneCategory.CYCLONE

        categories[name] = cat

    return categories


def _count_cascading_stages(
    start: str,
    topology: PipelineTopology,
    readings: Dict[str, VorticityReading],
    threshold: float = 0.3,
) -> int:
    """Count stages affected by cascading from a starting stage."""
    count = 0
    visited: set = set()
    queue = [start]

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        if current in readings and readings[current].zeta > threshold:
            count += 1
            for ds in topology.downstream.get(current, []):
                if ds not in visited:
                    queue.append(ds)

    return count


def classify_all_cyclones(
    topology: PipelineTopology,
    detections: Optional[List[CycloneDetection]] = None,
) -> List[CycloneDetection]:
    """Classify all detected cyclones and return with updated categories.

    If no detections provided, runs full detection pipeline.
    """
    from cyclone.detect import detect_cyclones
    from cyclone.cisk import detect_cisk

    if detections is None:
        cycles, gains = detect_cisk(topology)
        detections = detect_cyclones(topology, cisk_cycles=cycles, cycle_gains=gains)

    return detections


def overall_pipeline_status(
    categories: Dict[str, CycloneCategory],
) -> CycloneCategory:
    """Determine the overall pipeline status (maximum category)."""
    if not categories:
        return CycloneCategory.CALM
    return max(categories.values())


def format_category(
    categories: Dict[str, CycloneCategory],
    detections: Optional[List[CycloneDetection]] = None,
    show_all: bool = False,
) -> str:
    """Format severity classification as a human-readable string."""
    lines: List[str] = []

    lines.append("🌀 Cyclone Severity Classification — Saffir-Simpson Analog")
    lines.append("=" * 60)

    overall = overall_pipeline_status(categories)
    lines.append(f"  Overall Status: {overall.emoji} {overall.label}")
    lines.append("")

    # Group by category
    by_category: Dict[CycloneCategory, List[str]] = {}
    for name, cat in categories.items():
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(name)

    # Show from highest to lowest severity
    for cat in reversed(CycloneCategory):
        stages = by_category.get(cat, [])
        if not stages:
            continue
        if not show_all and cat == CycloneCategory.CALM:
            continue
        lines.append(f"  {cat.emoji} Category {cat.value} — {cat.label}")
        for stage in stages:
            lines.append(f"    • {stage}")
        lines.append("")

    if detections:
        lines.append("  Active Cyclones:")
        for d in detections:
            lines.append(f"    {d.category.emoji} {d.id}: {d.center_stage} ({d.severity_label})")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
