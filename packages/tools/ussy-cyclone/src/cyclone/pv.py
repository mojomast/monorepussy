"""Potential Vorticity (PV) analysis and scaling predictions.

PV conservation:
    PV = (ζ + f) / H = constant along a fluid parcel

Pipeline mapping:
    (reprocessing_tendency + base_retry_rate) / queue_depth = conserved

When queue depth H decreases (a stage is under-provisioned), (ζ + f) must
increase — reprocessing tendency rises. This is the bathtub vortex effect:
narrower drain = faster spin.

Cyclone uses PV conservation to predict that when a pipeline stage is scaled
down, reprocessing vorticity will intensify proportionally.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Optional, Tuple

from cyclone.models import PipelineStage, PipelineTopology, VorticityReading
from cyclone.vorticity import compute_vorticity_field


def compute_pv(topology: PipelineTopology) -> Dict[str, float]:
    """Compute potential vorticity at each pipeline stage.

    PV = (ζ + f) / H

    Where:
    - ζ = relative vorticity
    - f = Coriolis parameter (base retry rate)
    - H = queue depth (depth of the fluid layer)

    Returns mapping from stage name to PV value.
    """
    readings = compute_vorticity_field(topology)
    pv_map: Dict[str, float] = {}

    for name, stage in topology.stages.items():
        if name in readings:
            reading = readings[name]
            H = max(stage.queue_depth, 1)
            pv = reading.absolute_vorticity / H
            pv_map[name] = pv

    return pv_map


def check_pv_conservation(
    topology: PipelineTopology,
    current_pv: Optional[Dict[str, float]] = None,
    previous_pv: Optional[Dict[str, float]] = None,
    tolerance: float = 0.1,
) -> Dict[str, str]:
    """Check PV conservation at each stage.

    Stages where PV is conserved (within tolerance) are in "geostrophic balance".
    Stages where PV is changing are experiencing "diabatic forcing" —
    external perturbation (new error source, consumer crash, etc.).

    Args:
        topology: Pipeline topology.
        current_pv: Current PV values (computed if not provided).
        previous_pv: Previous PV values for comparison.
        tolerance: Fractional change tolerance for "conserved".

    Returns:
        Mapping from stage name to status: "conserved" or "forcing".
    """
    if current_pv is None:
        current_pv = compute_pv(topology)

    if previous_pv is None:
        # Without previous data, assume conserved
        return {name: "conserved" for name in current_pv}

    results: Dict[str, str] = {}
    for name in current_pv:
        if name in previous_pv and previous_pv[name] != 0:
            change = abs(current_pv[name] - previous_pv[name]) / abs(previous_pv[name])
            if change <= tolerance:
                results[name] = "conserved"
            else:
                results[name] = "forcing"
        else:
            results[name] = "unknown"

    return results


def simulate_scale_down(
    topology: PipelineTopology,
    stage_name: str,
    target_consumers: int,
) -> Dict[str, float]:
    """Simulate the effect of scaling down a stage on vorticity.

    PV conservation predicts: when H decreases, ζ must increase.
    Scaling down consumers → lower effective H → higher vorticity.

    Args:
        topology: Current pipeline topology.
        stage_name: The stage to scale down.
        target_consumers: Target number of consumers.

    Returns:
        Dictionary with predicted vorticity changes per stage.
    """
    if stage_name not in topology.stages:
        raise ValueError(f"Stage '{stage_name}' not found in topology")

    stage = topology.stages[stage_name]

    if target_consumers >= stage.consumer_count:
        return {name: 0.0 for name in topology.stages}

    # Current PV
    current_pv = compute_pv(topology)

    # Simulate: reduce consumer count → effectively reduce queue capacity
    # H_new = H * (target_consumers / current_consumers)
    consumer_ratio = target_consumers / stage.consumer_count

    # Create modified topology
    sim_topo = deepcopy(topology)
    sim_stage = sim_topo.stages[stage_name]
    original_consumers = sim_stage.consumer_count
    sim_stage.consumer_count = target_consumers

    # Simulate reduced effective queue depth
    sim_stage.queue_depth = max(1, int(sim_stage.queue_depth * consumer_ratio))

    # Forward rate per consumer stays the same, total forward rate decreases
    rate_per_consumer = sim_stage.forward_rate / original_consumers
    sim_stage.forward_rate = rate_per_consumer * target_consumers
    sim_stage.velocity.u = sim_stage.forward_rate

    # Recompute vorticity with modified topology
    sim_readings = compute_vorticity_field(sim_topo)
    orig_readings = compute_vorticity_field(topology)

    changes: Dict[str, float] = {}
    for name in topology.stages:
        if name in sim_readings and name in orig_readings:
            changes[name] = sim_readings[name].zeta - orig_readings[name].zeta

    return changes


def predict_vorticity_intensification(
    topology: PipelineTopology,
    stage_name: str,
    target_consumers: int,
) -> Dict[str, float]:
    """Predict vorticity intensification factor when scaling down.

    Returns the predicted vorticity multiplier at each stage.
    """
    changes = simulate_scale_down(topology, stage_name, target_consumers)
    orig_readings = compute_vorticity_field(topology)

    multipliers: Dict[str, float] = {}
    for name in topology.stages:
        orig_zeta = abs(orig_readings[name].zeta) if name in orig_readings else 1.0
        if orig_zeta > 0.001:
            multipliers[name] = (orig_zeta + changes.get(name, 0.0)) / orig_zeta
        else:
            multipliers[name] = 1.0

    return multipliers


def format_pv(
    pv_map: Dict[str, float],
    conservation: Optional[Dict[str, str]] = None,
) -> str:
    """Format PV analysis as a human-readable string."""
    lines: List[str] = []

    lines.append("🧭 Potential Vorticity Analysis")
    lines.append("=" * 55)

    if not pv_map:
        lines.append("  No stages to analyze.")
        return "\n".join(lines)

    lines.append("")
    lines.append(f"  {'Stage':<20} {'PV':>10} {'Status':<15}")
    lines.append("  " + "-" * 45)

    for name, pv in sorted(pv_map.items()):
        status = ""
        if conservation and name in conservation:
            status = conservation[name]
            if status == "forcing":
                status = "⚠ diabatic forcing"
            elif status == "conserved":
                status = "✓ geostrophic balance"
        lines.append(f"  {name:<20} {pv:>10.4f} {status:<15}")

    lines.append("")
    lines.append("=" * 55)
    return "\n".join(lines)
