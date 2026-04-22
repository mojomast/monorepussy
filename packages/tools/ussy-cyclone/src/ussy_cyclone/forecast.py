"""Forecast model — vorticity advection prediction.

Uses Euler forward integration of the vorticity equation:

    ∂ζ/∂t = -(u·∇)ζ - ζ(∇·V) + (f + ζ)(∂w/∂z) + friction

Pipeline mapping:
    ∂(reprocessing_tendency)/∂t =
      -advection (reprocessing carried downstream)
      -convergence_amplification (ζ intensifies where flow converges)
      +stretching (vorticity amplified when pipeline narrows)
      -dissipation (retries exhausted / DLQ drained)

Short-range (1-4 hours) is reliable; long-range requires ensemble methods.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from ussy_cyclone.models import (
    CycloneCategory,
    ForecastStep,
    PipelineTopology,
    VorticityReading,
    classify_vorticity,
)
from ussy_cyclone.vorticity import compute_vorticity_field


# Default forecast parameters
DEFAULT_HORIZON_HOURS = 4
DEFAULT_TIMESTEP_MINUTES = 15
FRICTION_COEFFICIENT = 0.02  # Dissipation rate
ADVECTION_WEIGHT = 0.3
CONVERGENCE_WEIGHT = 0.5
STRETCHING_WEIGHT = 0.2


def compute_dzeta_dt(
    topology: PipelineTopology,
    readings: Dict[str, VorticityReading],
) -> Dict[str, float]:
    """Compute the rate of change of vorticity at each stage.

    ∂ζ/∂t = -advection - convergence_amplification + stretching - friction
    """
    dzeta: Dict[str, float] = {}
    downstream_map = topology.downstream

    for name, stage in topology.stages.items():
        if name not in readings:
            dzeta[name] = 0.0
            continue

        reading = readings[name]
        zeta = reading.zeta

        # Advection: reprocessing carried downstream
        downstream = downstream_map.get(name, [])
        if downstream:
            avg_zeta_down = sum(
                readings[ds].zeta for ds in downstream if ds in readings
            ) / len(downstream)
            advection = reading.zeta - avg_zeta_down  # positive = carrying vorticity away
        else:
            advection = 0.0

        # Convergence amplification: ζ intensifies where flow converges
        convergence = 0.0
        if reading.divergence < 0:
            # Negative divergence = convergence → amplification
            convergence = -reading.divergence * abs(zeta) * CONVERGENCE_WEIGHT

        # Stretching: vorticity amplified when pipeline narrows (fewer consumers)
        stretching = 0.0
        if downstream:
            for ds in downstream:
                if ds in topology.stages:
                    ds_stage = topology.stages[ds]
                    if ds_stage.consumer_count < stage.consumer_count:
                        # Pipeline narrows → stretching effect
                        ratio = stage.consumer_count / max(ds_stage.consumer_count, 1)
                        stretching += ratio * abs(zeta) * STRETCHING_WEIGHT
            stretching /= max(len(downstream), 1)

        # Friction/dissipation: retries exhausted, DLQ drained
        friction = FRICTION_COEFFICIENT * zeta

        # Total rate of change
        rate = (
            -ADVECTION_WEIGHT * advection
            + convergence
            + stretching
            - friction
        )
        dzeta[name] = rate

    return dzeta


def forecast(
    topology: PipelineTopology,
    horizon_hours: int = DEFAULT_HORIZON_HOURS,
    timestep_minutes: int = DEFAULT_TIMESTEP_MINUTES,
    initial_readings: Optional[Dict[str, VorticityReading]] = None,
) -> List[ForecastStep]:
    """Generate a vorticity forecast using Euler forward integration.

    Args:
        topology: Current pipeline topology.
        horizon_hours: How many hours ahead to forecast.
        timestep_minutes: Time step for integration.
        initial_readings: Starting vorticity readings (computed if not provided).

    Returns:
        List of ForecastStep objects at each time step.
    """
    if initial_readings is None:
        initial_readings = compute_vorticity_field(topology)

    steps: List[ForecastStep] = []
    current_zeta: Dict[str, float] = {name: r.zeta for name, r in initial_readings.items()}
    now = datetime.now(timezone.utc)

    num_steps = int(horizon_hours * 60 / timestep_minutes)
    dt = timedelta(minutes=timestep_minutes)

    for step_i in range(num_steps):
        forecast_time = now + dt * (step_i + 1)

        # Compute rate of change
        # Build temporary readings for dzeta computation
        temp_readings: Dict[str, VorticityReading] = {}
        for name, zeta in current_zeta.items():
            stage = topology.stages.get(name)
            if stage:
                temp_readings[name] = VorticityReading(
                    stage_name=name,
                    zeta=zeta,
                    absolute_vorticity=zeta + stage.coriolis_parameter,
                    divergence=initial_readings.get(name, VorticityReading(stage_name=name, zeta=0.0)).divergence,
                )

        dzeta = compute_dzeta_dt(topology, temp_readings)

        # Euler forward step
        for name in current_zeta:
            if name in dzeta:
                current_zeta[name] += dzeta[name] * (timestep_minutes / 60.0)

        # Classify categories
        categories: Dict[str, CycloneCategory] = {}
        for name, zeta in current_zeta.items():
            stage = topology.stages.get(name)
            if stage:
                categories[name] = classify_vorticity(zeta, stage.reprocessing_fraction)

        # Count cyclones
        cyclone_count = sum(1 for c in categories.values() if c.value >= CycloneCategory.STORM.value)

        steps.append(ForecastStep(
            timestamp=forecast_time,
            stage_vorticities=dict(current_zeta),
            stage_categories=categories,
            cyclone_count=cyclone_count,
        ))

    return steps


def format_forecast(steps: List[ForecastStep], with_confidence: bool = False) -> str:
    """Format forecast results as a human-readable string."""
    lines: List[str] = []

    lines.append("🌧️ Cyclone Forecast — Pipeline Weather Report")
    lines.append("=" * 60)

    if not steps:
        lines.append("  No forecast data available.")
        return "\n".join(lines)

    lines.append("")

    # Show key time points
    key_indices = [0]  # Always show first step
    if len(steps) > 4:
        key_indices.append(len(steps) // 4)
        key_indices.append(len(steps) // 2)
        key_indices.append(3 * len(steps) // 4)
    if len(steps) > 1:
        key_indices.append(len(steps) - 1)

    # Remove duplicates and sort
    key_indices = sorted(set(key_indices))

    for idx in key_indices:
        step = steps[idx]
        time_str = step.timestamp.strftime("%H:%M UTC")
        lines.append(f"  T+{(idx+1)*15}min ({time_str}):")

        # Show stages with notable activity
        active_stages = [
            (name, zeta, step.stage_categories.get(name, CycloneCategory.CALM))
            for name, zeta in step.stage_vorticities.items()
            if step.stage_categories.get(name, CycloneCategory.CALM).value >= CycloneCategory.DEPRESSION.value
        ]

        if active_stages:
            for name, zeta, cat in sorted(active_stages, key=lambda x: -abs(x[1])):
                marker = "⚡" if cat.value >= 3 else ("⚠" if cat.value >= 2 else "•")
                lines.append(f"    {marker} {name}: ζ={zeta:+.2f} ({cat.label})")
        else:
            lines.append("    All stages calm")

        if with_confidence and idx > 0:
            # Simplified confidence: decreases with time
            confidence = max(50, 95 - idx * 5)
            lines.append(f"    Confidence: ~{confidence}%")

        lines.append("")

    if steps[-1].cyclone_count > 0:
        lines.append(f"  ⚡ Forecast: {steps[-1].cyclone_count} cyclonic formation(s) expected at T+{len(steps)*15}min")
    else:
        lines.append("  ✅ Forecast: Pipeline expected to remain calm")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
