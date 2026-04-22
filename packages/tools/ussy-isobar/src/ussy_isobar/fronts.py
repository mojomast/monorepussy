"""Front detection and classification — instability boundaries between code zones.

Uses the frontogenesis function from meteorology applied to code change patterns.
∂|∇θ|/∂t > 0  →  ∂|∇(change_velocity)|/∂t > 0

When the gradient of change velocity (temperature) is strengthening over time,
a front is forming.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

from ussy_isobar.fields import AtmosphericField, AtmosphericProfile, FRONT_THRESHOLD


class FrontType(Enum):
    WARM = "warm"        # Change energy flowing from unstable to stable zone
    COLD = "cold"        # Stable zone being disrupted by unstable code
    OCCLUDED = "occluded"  # Two warm fronts merging
    STATIONARY = "stationary"  # Front not moving


class FrontIntensity(Enum):
    DEVELOPING = "developing"
    ACTIVE = "active"
    INTENSIFYING = "intensifying"
    DISSIPATING = "dissipating"


@dataclass
class Front:
    """An instability boundary between two code zones."""
    front_type: FrontType
    intensity: FrontIntensity
    hot_side: str      # Filepath of the hot side
    cold_side: str     # Filepath of the cold side
    temperature_gradient: float  # |ΔT| between sides
    frontogenesis_rate: float = 0.0  # ∂|∇T|/∂t — rate of gradient strengthening
    description: str = ""

    @property
    def is_severe(self) -> bool:
        return self.temperature_gradient > FRONT_THRESHOLD * 2 or self.frontogenesis_rate > 0.5

    @property
    def risk_label(self) -> str:
        if self.front_type == FrontType.COLD and self.is_severe:
            return "⚠ SEVERE COLD FRONT"
        if self.front_type == FrontType.WARM and self.is_severe:
            return "⚠ INTENSE WARM FRONT"
        if self.front_type == FrontType.OCCLUDED:
            return "⚠ OCCLUDED FRONT"
        return f"{self.front_type.value.upper()} FRONT"


def _are_adjacent(f1: str, f2: str, import_graph: Dict) -> bool:
    """Check if two files are 'adjacent' (one imports the other or share a directory)."""
    # Direct dependency
    deps1 = import_graph.get(f1, set())
    deps2 = import_graph.get(f2, set())
    if f2 in deps1 or f1 in deps2:
        return True

    # Same directory
    dir1 = "/".join(f1.replace("\\", "/").split("/")[:-1])
    dir2 = "/".join(f2.replace("\\", "/").split("/")[:-1])
    if dir1 and dir1 == dir2:
        return True

    return False


def detect_fronts(atm_field: AtmosphericField,
                  import_graph: Optional[Dict] = None,
                  ) -> List[Front]:
    """Detect and classify fronts in the atmospheric field.

    A front forms where hot (frequently-changed) code borders cold (stable, high-dependency) code
    AND the gradient is strengthening (frontogenesis condition).
    """
    fronts: List[Front] = []
    profiles = list(atm_field.profiles.values())

    if import_graph is None:
        import_graph = {}

    # Compare all pairs of adjacent files
    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            p1 = profiles[i]
            p2 = profiles[j]

            # Only check adjacent files
            if not _are_adjacent(p1.filepath, p2.filepath, import_graph):
                continue

            temp_diff = abs(p1.temperature - p2.temperature)
            if temp_diff < FRONT_THRESHOLD:
                continue

            # Determine hot and cold sides
            if p1.temperature > p2.temperature:
                hot, cold = p1, p2
            else:
                hot, cold = p2, p1

            # Classify front type
            front_type = _classify_front(hot, cold)

            # Compute frontogenesis rate
            frontogenesis = _compute_frontogenesis(hot, cold)

            # Determine intensity
            intensity = _classify_intensity(temp_diff, frontogenesis)

            front = Front(
                front_type=front_type,
                intensity=intensity,
                hot_side=hot.filepath,
                cold_side=cold.filepath,
                temperature_gradient=temp_diff,
                frontogenesis_rate=frontogenesis,
                description=_describe_front(front_type, hot, cold, temp_diff),
            )
            fronts.append(front)

    # Sort by severity
    fronts.sort(key=lambda f: f.temperature_gradient, reverse=True)
    return fronts


def _classify_front(hot: AtmosphericProfile, cold: AtmosphericProfile) -> FrontType:
    """Classify a front based on the characteristics of hot and cold sides."""
    # Warm front: change energy flowing from unstable to stable (hot → cold, cold has high pressure)
    if cold.is_high_pressure and not hot.is_high_pressure:
        return FrontType.WARM

    # Cold front: stable zone being disrupted by unstable code (hot disrupts cold)
    if hot.is_high_pressure and not cold.is_high_pressure:
        return FrontType.COLD

    # Both are hot = occluded front (two warm fronts merging)
    if hot.temperature > 50 and cold.temperature > 30:
        return FrontType.OCCLUDED

    # Default to warm front
    return FrontType.WARM


def _compute_frontogenesis(hot: AtmosphericProfile, cold: AtmosphericProfile) -> float:
    """Compute frontogenesis rate — ∂|∇T|/∂t.

    Approximated by the difference in barometric tendencies.
    If the gradient is strengthening, frontogenesis is positive.
    """
    # If hot side is getting hotter and cold side is stable → frontogenesis
    return hot.barometric_tendency - cold.barometric_tendency


def _classify_intensity(gradient: float, frontogenesis: float) -> FrontIntensity:
    """Classify the intensity of a front."""
    if frontogenesis > 0.5:
        return FrontIntensity.INTENSIFYING
    if frontogenesis > 0:
        return FrontIntensity.ACTIVE
    if frontogenesis < -0.5:
        return FrontIntensity.DISSIPATING
    if gradient > FRONT_THRESHOLD * 2:
        return FrontIntensity.ACTIVE
    return FrontIntensity.DEVELOPING


def _describe_front(front_type: FrontType, hot: AtmosphericProfile,
                    cold: AtmosphericProfile, gradient: float) -> str:
    """Generate a human-readable description of a front."""
    hot_name = hot.filepath.split("/")[-1] if "/" in hot.filepath else hot.filepath
    cold_name = cold.filepath.split("/")[-1] if "/" in cold.filepath else cold.filepath

    if front_type == FrontType.WARM:
        return (f"Warm front: change energy flowing from {hot_name} ({hot.temperature:.0f}°C) "
                f"toward {cold_name} ({cold.temperature:.0f}°C)")
    elif front_type == FrontType.COLD:
        return (f"Cold front: unstable {hot_name} ({hot.temperature:.0f}°C) "
                f"disrupting stable {cold_name} ({cold.temperature:.0f}°C)")
    elif front_type == FrontType.OCCLUDED:
        return (f"Occluded front: merging warm zones {hot_name} ({hot.temperature:.0f}°C) "
                f"and {cold_name} ({cold.temperature:.0f}°C)")
    else:
        return (f"Stationary front between {hot_name} ({hot.temperature:.0f}°C) "
                f"and {cold_name} ({cold.temperature:.0f}°C)")


def format_fronts_report(fronts: List[Front]) -> str:
    """Format fronts into a human-readable report."""
    if not fronts:
        return "No active fronts detected — conditions are stable."

    lines: List[str] = []
    lines.append("FRONTAL ANALYSIS")
    lines.append("=" * 50)
    lines.append("")

    for i, front in enumerate(fronts, 1):
        lines.append(f"  Front #{i}: {front.risk_label}")
        lines.append(f"    {front.description}")
        lines.append(f"    Gradient: {front.temperature_gradient:.1f}°C | "
                     f"Frontogenesis: {front.frontogenesis_rate:+.2f}")
        lines.append(f"    Intensity: {front.intensity.value}")
        lines.append(f"    Hot side:  {front.hot_side}")
        lines.append(f"    Cold side: {front.cold_side}")
        lines.append("")

    # Summary
    severe = [f for f in fronts if f.is_severe]
    if severe:
        lines.append(f"  ⚠ {len(severe)} severe front(s) detected!")

    return "\n".join(lines)
