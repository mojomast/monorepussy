"""Attenuation Budget — Cumulative Fidelity Decay Analysis.

Models signal attenuation across pipeline hops, computing multiplicative
fidelity decay (M(n) = M0 * prod(1 - epsilon_i)) and the Heaviside
condition for distortionless processing.
"""

from __future__ import annotations

import math
from typing import Any

from .models import AttenuationResult, Hop, Route


# Default fidelity threshold — below this, warnings are raised
DEFAULT_FIDELITY_THRESHOLD = 0.90

# Distortionless condition tolerance: if |sum(ser) - sum(deser)| < tolerance, pipeline is distortionless
DISTORTIONLESS_TOLERANCE = 0.005


def compute_fidelity(route: Route) -> float:
    """Compute cumulative fidelity across a route.

    M(n) = M0 * prod(1 - epsilon_i) where M0 = 1.0
    """
    fidelity = 1.0
    for hop in route.hops:
        fidelity *= 1.0 - hop.degradation
    return fidelity


def check_distortionless(route: Route, tolerance: float = DISTORTIONLESS_TOLERANCE) -> bool:
    """Check the Heaviside condition for distortionless pipeline.

    If sum(serialization_degradation) ≈ sum(deserialization_degradation),
    the pipeline is distortionless — degradation is uniform and predictable.
    """
    total_ser = sum(h.serialization_degradation for h in route.hops)
    total_deser = sum(h.deserialization_degradation for h in route.hops)
    return abs(total_ser - total_deser) < tolerance


def find_loading_coil_position(route: Route, threshold: float = DEFAULT_FIDELITY_THRESHOLD) -> int | None:
    """Find the optimal position to inject a loading coil (schema validation).

    Returns the 1-indexed hop position after which to inject validation,
    or None if no loading coil is needed.
    """
    running_fidelity = 1.0
    for i, hop in enumerate(route.hops):
        running_fidelity *= 1.0 - hop.degradation
        if running_fidelity < threshold:
            # Loading coil should be placed at the hop BEFORE fidelity drops below threshold
            # or at the current hop if it's the first
            return max(1, i)
    return None


def analyze_attenuation(
    route: Route,
    threshold: float = DEFAULT_FIDELITY_THRESHOLD,
) -> AttenuationResult:
    """Perform full attenuation budget analysis on a pipeline route.

    Args:
        route: Pipeline route with hops and degradation factors.
        threshold: Minimum acceptable fidelity at sink.

    Returns:
        AttenuationResult with fidelity, warnings, and recommendations.
    """
    fidelity = compute_fidelity(route)
    is_distortionless = check_distortionless(route)
    warnings: list[str] = []
    recommendations: list[str] = []

    if fidelity < threshold:
        degradation_pct = (1.0 - fidelity) * 100
        warnings.append(
            f"Fidelity below {threshold:.0%} threshold at sink "
            f"({degradation_pct:.1f}% cumulative degradation)"
        )

    if not is_distortionless:
        total_ser = sum(h.serialization_degradation for h in route.hops)
        total_deser = sum(h.deserialization_degradation for h in route.hops)
        warnings.append(
            f"Pipeline is NOT distortionless: "
            f"Σ(ε_ser)={total_ser:.4f} ≠ Σ(ε_deser)={total_deser:.4f} — "
            f"distortion accumulates non-linearly"
        )
        recommendations.append(
            "Consider loading coils (validation injection) to balance "
            "serialization/deserialization degradation"
        )

    # Identify high-degradation hops
    high_degradation_hops = [
        h for h in route.hops if h.degradation >= 0.02
    ]
    for hop in high_degradation_hops:
        recommendations.append(
            f"High degradation at '{hop.name}': ε={hop.degradation:.3f} — "
            f"investigate and consider schema validation (loading coil)"
        )

    # Loading coil recommendation
    coil_pos = find_loading_coil_position(route, threshold)
    if coil_pos is not None:
        recommendations.append(
            f"Inject schema validation at hop {coil_pos} (loading coil) "
            f"to prevent fidelity from dropping below {threshold:.0%}"
        )

    return AttenuationResult(
        route=route,
        fidelity=fidelity,
        cumulative_degradation=1.0 - fidelity,
        is_distortionless=is_distortionless,
        warnings=warnings,
        recommendations=recommendations,
    )


def format_attenuation_report(result: AttenuationResult) -> str:
    """Format attenuation result as a human-readable report."""
    lines: list[str] = []

    route = result.route
    lines.append(f"Route: {route.name} ({route.hop_count} hops)")
    lines.append(
        f"Fidelity at sink: {result.fidelity:.3f} "
        f"({result.cumulative_degradation * 100:.1f}% cumulative degradation)"
    )

    running_fidelity = 1.0
    for i, hop in enumerate(route.hops, 1):
        running_fidelity *= 1.0 - hop.degradation
        detail = f" {hop.details}" if hop.details else ""
        lines.append(
            f"  Hop {i}: ε={hop.degradation:.3f}{detail} "
            f"(cumulative fidelity: {running_fidelity:.3f})"
        )

    if result.is_distortionless:
        lines.append("✓ Pipeline is distortionless (Heaviside condition met)")
    else:
        lines.append("⚠ Pipeline is NOT distortionless (Heaviside condition NOT met)")

    for w in result.warnings:
        lines.append(f"⚠ WARNING: {w}")

    for r in result.recommendations:
        lines.append(f"  → {r}")

    return "\n".join(lines)


def attenuation_to_dict(result: AttenuationResult) -> dict[str, Any]:
    """Convert attenuation result to a JSON-serializable dictionary."""
    return {
        "route": result.route.name,
        "hop_count": result.route.hop_count,
        "fidelity": round(result.fidelity, 6),
        "cumulative_degradation": round(result.cumulative_degradation, 6),
        "is_distortionless": result.is_distortionless,
        "warnings": result.warnings,
        "recommendations": result.recommendations,
        "hops": [
            {
                "name": h.name,
                "degradation": h.degradation,
                "details": h.details,
                "serialization_degradation": h.serialization_degradation,
                "deserialization_degradation": h.deserialization_degradation,
            }
            for h in result.route.hops
        ],
    }
