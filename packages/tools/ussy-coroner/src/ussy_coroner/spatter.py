"""Error Spatter Reconstruction — Blood Spatter Analysis.

When a pipeline fails, multiple error indicators appear across stages.
Treats each as a blood stain and reconstructs the origin using:
- Impact angle: alpha = arcsin(breadth / depth)
- Area of convergence: least-squares intersection
- Height of origin: z_hat = (1/n) * sum(D_i * tan(alpha_i))
"""

from __future__ import annotations

import math
import re
from typing import Any

from ussy_coroner.models import (
    ErrorStain,
    PipelineRun,
    SpatterReconstruction,
    Stage,
    StageStatus,
    VelocityClass,
)


def _extract_error_components(log_content: str) -> list[str]:
    """Extract affected component names from error log content."""
    components: list[str] = []
    # Match module/component references in error messages
    patterns = [
        re.compile(r'(?:in|at|from)\s+([a-zA-Z_][\w.]*[\w])', re.IGNORECASE),
        re.compile(r'(?:module|package|component)\s+["\']?([\w.-]+)["\']?', re.IGNORECASE),
        re.compile(r'([a-zA-Z_][\w.-]*/[\w.-]+)', re.IGNORECASE),
    ]
    seen: set[str] = set()
    for p in patterns:
        for m in p.finditer(log_content):
            comp = m.group(1)
            if comp not in seen and len(comp) > 1:
                seen.add(comp)
                components.append(comp)
    return components[:10]  # Limit to top 10


def _compute_stain(stage: Stage) -> ErrorStain | None:
    """Compute an error stain from a failing stage."""
    if stage.status != StageStatus.FAILURE:
        return None

    components = _extract_error_components(stage.log_content)
    breadth = len(components) if components else 1

    # Depth: number of consecutive failing stages starting from this one
    # (will be corrected later when we have the full run context)
    depth = 1

    # Primary component
    component = components[0] if components else "unknown"

    return ErrorStain(
        stage_name=stage.name,
        stage_index=stage.index,
        breadth=breadth,
        depth=depth,
        component=component,
    )


def _compute_depths(run: PipelineRun) -> dict[str, int]:
    """Compute the depth (consecutive failing stages) for each failing stage."""
    depths: dict[str, int] = {}
    stages = run.stages
    i = 0
    while i < len(stages):
        if stages[i].status == StageStatus.FAILURE:
            # Count consecutive failures
            depth = 0
            j = i
            while j < len(stages) and stages[j].status == StageStatus.FAILURE:
                depth += 1
                j += 1
            # Assign the depth to all consecutive failures
            for k in range(i, j):
                depths[stages[k].name] = depth
            i = j
        else:
            i += 1
    return depths


def _classify_velocity(stains: list[ErrorStain]) -> VelocityClass:
    """Classify the velocity (severity pattern) of the failure."""
    if not stains:
        return VelocityClass.MEDIUM

    avg_breadth = sum(s.breadth for s in stains) / len(stains)
    avg_angle = sum(s.impact_angle for s in stains) / len(stains)

    if avg_breadth > 5 or avg_angle > 70:
        # Wide impact — catastrophic failure
        return VelocityClass.HIGH
    elif avg_breadth <= 2 or avg_angle < 40:
        # Narrow, focused — gradual degradation
        return VelocityClass.LOW
    else:
        # Medium — sudden failure (assertion/type error pattern)
        return VelocityClass.MEDIUM


def _find_convergence(stains: list[ErrorStain], run: PipelineRun) -> tuple[str, str]:
    """Find the area of convergence using least-squares backtracking.

    Returns (stage_name, component) of the estimated root cause location.
    """
    if not stains:
        return ("unknown", "unknown")

    if len(stains) == 1:
        # Single stain — root cause is one stage before
        idx = max(0, stains[0].stage_index - 1)
        if idx < len(run.stages):
            return (run.stages[idx].name, stains[0].component)
        return (stains[0].stage_name, stains[0].component)

    # Use weighted backtracking to find convergence
    # Each stain backtracks by tan(alpha) * depth stages
    backtrack_scores: dict[int, float] = {}
    component_scores: dict[str, float] = {}

    for stain in stains:
        if stain.impact_angle > 0:
            back_dist = math.tan(math.radians(stain.impact_angle))
        else:
            back_dist = 1.0
        origin_idx = max(0, int(stain.stage_index - back_dist))

        # Weight by inverse angle (more vertical = more reliable)
        weight = 1.0 / max(stain.impact_angle, 1.0)
        backtrack_scores[origin_idx] = backtrack_scores.get(origin_idx, 0) + weight
        component_scores[stain.component] = component_scores.get(stain.component, 0) + weight

    # Find stage with highest convergence score
    best_idx = max(backtrack_scores, key=backtrack_scores.get)  # type: ignore[arg-type]
    best_component = max(component_scores, key=component_scores.get)  # type: ignore[arg-type]

    stage_name = "unknown"
    if best_idx < len(run.stages):
        stage_name = run.stages[best_idx].name
    elif stains:
        stage_name = stains[0].stage_name

    return (stage_name, best_component)


def _compute_origin_depth(stains: list[ErrorStain], first_failure_index: int) -> tuple[float, float]:
    """Compute origin depth before first observed error.

    z_hat = (1/n) * sum(D_i * tan(alpha_i))
    Returns (origin_depth, variance).
    """
    if not stains:
        return (0.0, 0.0)

    n = len(stains)
    depths = []
    for stain in stains:
        if stain.impact_angle > 0:
            d = stain.depth * math.tan(math.radians(stain.impact_angle))
        else:
            d = float(stain.depth)
        depths.append(d)

    z_hat = sum(depths) / n

    # Variance
    if n > 1:
        variance = sum((d - z_hat) ** 2 for d in depths) / (n - 1)
    else:
        variance = 0.0

    return (z_hat, variance)


def _compute_confidence(variance: float, n_stains: int) -> float:
    """Compute confidence score from variance and number of stains.

    Higher confidence with more stains and lower variance.
    """
    if n_stains == 0:
        return 0.0
    # Confidence increases with more stains, decreases with variance
    raw_conf = min(1.0, n_stains / 5.0) * max(0.0, 1.0 - variance / 10.0)
    return round(raw_conf, 2)


def analyze_spatter(run: PipelineRun) -> SpatterReconstruction:
    """Analyze error spatter for a pipeline run using blood spatter reconstruction.

    Args:
        run: The pipeline run to analyze.

    Returns:
        SpatterReconstruction with estimated root cause origin.
    """
    result = SpatterReconstruction()

    if not run.failed_stages:
        return result

    # Compute depths for consecutive failures
    depths = _compute_depths(run)

    # Generate stains from failing stages
    stains: list[ErrorStain] = []
    for stage in run.stages:
        if stage.status == StageStatus.FAILURE:
            stain = _compute_stain(stage)
            if stain:
                stain.depth = depths.get(stain.stage_name, 1)
                stains.append(stain)

    result.stains = stains

    if not stains:
        return result

    # Find convergence zone
    conv_stage, conv_component = _find_convergence(stains, run)
    result.convergence_stage = conv_stage
    result.convergence_component = conv_component

    # Compute origin depth
    first_failure = run.first_failure
    first_idx = first_failure.index if first_failure else 0
    origin_depth, variance = _compute_origin_depth(stains, first_idx)
    result.origin_depth = round(origin_depth, 1)
    result.variance = round(variance, 1)

    # Compute confidence
    result.confidence = _compute_confidence(variance, len(stains))

    # Classify velocity
    result.velocity_class = _classify_velocity(stains)

    # Generate likely cause description
    result.likely_cause = (
        f"Root cause likely in stage '{conv_stage}', component '{conv_component}', "
        f"approximately {origin_depth:.1f} stages before first observed error"
    )

    return result


def format_spatter(result: SpatterReconstruction) -> str:
    """Format spatter reconstruction results for display."""
    lines: list[str] = []

    if not result.stains:
        lines.append("No error stains found — pipeline may have passed.")
        return "\n".join(lines)

    # Individual stains
    for i, stain in enumerate(result.stains, 1):
        lines.append(
            f"Stain {i}: Stage {stain.stage_name} "
            f"(breadth={stain.breadth}, depth={stain.depth}, "
            f"α={stain.impact_angle:.1f}°)"
        )

    lines.append("")

    # Convergence zone
    lines.append(f"Convergence zone: Stage {result.convergence_stage}, component {result.convergence_component}")

    # Origin depth
    lines.append(
        f"Origin depth: {result.origin_depth} stages BEFORE first observed error "
        f"(σ²={result.variance}, confidence={result.confidence})"
    )

    lines.append("")

    # Velocity classification
    if result.velocity_class == VelocityClass.HIGH:
        vdesc = "catastrophic failure (OOM, segfault pattern)"
    elif result.velocity_class == VelocityClass.MEDIUM:
        vdesc = "sudden failure (assertion/type error pattern)"
    else:
        vdesc = "gradual degradation"
    lines.append(f"Velocity classification: {result.velocity_class.value.upper()} → {vdesc}")

    # Likely cause
    if result.likely_cause:
        lines.append(result.likely_cause)

    return "\n".join(lines)
