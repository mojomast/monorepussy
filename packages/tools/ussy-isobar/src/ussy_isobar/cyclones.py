"""Cyclone and anticyclone detection — self-reinforcing instability/stability spirals.

Cyclone: Hot file → bugs in dependents → hot dependents → more bugs
  Vorticity ζ = ∂(bug_rate)/∂(change_freq) - ∂(fix_rate)/∂(severity)
  Positive ζ > threshold triggers cyclone warning.

Anticyclone: Cold file → clean dependents → easy to maintain
  Negative ζ indicates anticyclonic stability.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from ussy_isobar.fields import AtmosphericField, AtmosphericProfile, CYCLONE_VORTICITY_THRESHOLD


class CycloneCategory(Enum):
    TROPICAL_DEPRESSION = "tropical_depression"
    TROPICAL_STORM = "tropical_storm"
    CATEGORY_1 = "category_1"
    CATEGORY_2 = "category_2"
    CATEGORY_3 = "category_3"
    CATEGORY_4 = "category_4"
    CATEGORY_5 = "category_5"


class WarningLevel(Enum):
    WATCH = "watch"       # Conditions possible
    WARNING = "warning"   # Conditions expected
    SEVERE = "severe"     # Major impact expected
    CRITICAL = "critical"  # Extreme impact


@dataclass
class Cyclone:
    """A self-reinforcing instability spiral in the codebase."""
    eye: str  # Central file (the hot file driving the spiral)
    vorticity: float
    category: CycloneCategory
    spiral_files: List[str] = field(default_factory=list)  # Files in the spiral
    path_forecast: List[str] = field(default_factory=list)  # Predicted spiral path
    warning_level: WarningLevel = WarningLevel.WATCH
    probability: float = 0.0  # Probability of breaking changes

    @property
    def category_label(self) -> str:
        labels = {
            CycloneCategory.TROPICAL_DEPRESSION: "Tropical Depression",
            CycloneCategory.TROPICAL_STORM: "Tropical Storm",
            CycloneCategory.CATEGORY_1: "Category 1",
            CycloneCategory.CATEGORY_2: "Category 2",
            CycloneCategory.CATEGORY_3: "Category 3 — Major",
            CycloneCategory.CATEGORY_4: "Category 4 — Severe",
            CycloneCategory.CATEGORY_5: "Category 5 — Extreme",
        }
        return labels.get(self.category, "Unknown")

    @property
    def symbol(self) -> str:
        if self.category in (CycloneCategory.CATEGORY_4, CycloneCategory.CATEGORY_5):
            return "⛈"
        if self.category == CycloneCategory.CATEGORY_3:
            return "🌪"
        if self.category in (CycloneCategory.TROPICAL_STORM, CycloneCategory.CATEGORY_1,
                             CycloneCategory.CATEGORY_2):
            return "🌀"
        return "☉"


@dataclass
class Anticyclone:
    """A self-reinforcing stability zone in the codebase."""
    center: str  # Central stable file
    stability_index: float
    protected_files: List[str] = field(default_factory=list)

    @property
    def symbol(self) -> str:
        return "(H)"


def classify_cyclone(vorticity: float) -> CycloneCategory:
    """Classify a cyclone by its vorticity."""
    abs_vort = abs(vorticity)
    if abs_vort < 1.5:
        return CycloneCategory.TROPICAL_DEPRESSION
    elif abs_vort < 2.0:
        return CycloneCategory.TROPICAL_STORM
    elif abs_vort < 2.5:
        return CycloneCategory.CATEGORY_1
    elif abs_vort < 3.0:
        return CycloneCategory.CATEGORY_2
    elif abs_vort < 4.0:
        return CycloneCategory.CATEGORY_3
    elif abs_vort < 5.0:
        return CycloneCategory.CATEGORY_4
    else:
        return CycloneCategory.CATEGORY_5


def determine_warning_level(cyclone: Cyclone, profile: AtmosphericProfile) -> WarningLevel:
    """Determine the warning level for a cyclone."""
    if cyclone.category in (CycloneCategory.CATEGORY_4, CycloneCategory.CATEGORY_5):
        return WarningLevel.CRITICAL
    if cyclone.category == CycloneCategory.CATEGORY_3:
        return WarningLevel.SEVERE
    if cyclone.category in (CycloneCategory.CATEGORY_1, CycloneCategory.CATEGORY_2):
        return WarningLevel.WARNING
    if profile.storm_probability > 0.5:
        return WarningLevel.WARNING
    return WarningLevel.WATCH


def detect_cyclones(atm_field: AtmosphericField) -> List[Cyclone]:
    """Detect cyclonic patterns in the atmospheric field.

    A cyclone forms when: hot file → bugs in dependents → hot dependents → more bugs.
    """
    cyclones: List[Cyclone] = []

    for filepath, profile in atm_field.profiles.items():
        if not profile.is_cyclonic:
            continue

        # Build the spiral: find dependents that are also hot/humid
        spiral_files = _build_spiral(filepath, atm_field)
        path_forecast = _forecast_spiral_path(filepath, atm_field)

        category = classify_cyclone(profile.bug_vorticity)

        cyclone = Cyclone(
            eye=filepath,
            vorticity=profile.bug_vorticity,
            category=category,
            spiral_files=spiral_files,
            path_forecast=path_forecast,
            probability=profile.storm_probability,
        )
        cyclone.warning_level = determine_warning_level(cyclone, profile)
        cyclones.append(cyclone)

    # Sort by severity
    cyclones.sort(key=lambda c: abs(c.vorticity), reverse=True)
    return cyclones


def detect_anticyclones(atm_field: AtmosphericField) -> List[Anticyclone]:
    """Detect anticyclonic stability zones — cold, stable, high-pressure areas."""
    anticyclones: List[Anticyclone] = []

    for filepath, profile in atm_field.profiles.items():
        # Anticyclone: cold + high pressure + low humidity
        if profile.is_cold and profile.is_high_pressure and not profile.is_humid:
            # Find protected files (dependents that are also stable)
            protected = []
            for dep in profile.dependents:
                dep_profile = atm_field.get_profile(dep)
                if dep_profile and dep_profile.temperature < 30:
                    protected.append(dep)

            stability_index = (100 - profile.temperature) * (profile.pressure / 10.0)

            anticyclones.append(Anticyclone(
                center=filepath,
                stability_index=stability_index,
                protected_files=protected,
            ))

    anticyclones.sort(key=lambda a: a.stability_index, reverse=True)
    return anticyclones


def _build_spiral(eye: str, atm_field: AtmosphericField) -> List[str]:
    """Build the spiral of files caught in a cyclone."""
    profile = atm_field.get_profile(eye)
    if not profile:
        return []

    spiral = [eye]
    visited = {eye}

    # BFS through dependents, following hot/humid paths
    queue = [eye]
    while queue:
        current = queue.pop(0)
        current_profile = atm_field.get_profile(current)
        if not current_profile:
            continue

        for dep in current_profile.dependents:
            if dep in visited:
                continue
            dep_profile = atm_field.get_profile(dep)
            if dep_profile and (dep_profile.is_hot or dep_profile.is_humid):
                spiral.append(dep)
                visited.add(dep)
                queue.append(dep)

    return spiral


def _forecast_spiral_path(eye: str, atm_field: AtmosphericField) -> List[str]:
    """Predict which files the cyclone will affect next."""
    profile = atm_field.get_profile(eye)
    if not profile:
        return []

    path = []
    # Follow wind direction to predict movement
    for co_change_file, strength in sorted(
        profile.co_change_files.items(), key=lambda x: x[1], reverse=True
    ):
        co_profile = atm_field.get_profile(co_change_file)
        if co_profile and co_profile.temperature < profile.temperature:
            # Cyclone moving toward colder areas (high gradient)
            path.append(co_change_file)
            if len(path) >= 5:
                break

    return path


def generate_storm_warnings(cyclones: List[Cyclone],
                            threshold: str = "watch") -> List[str]:
    """Generate storm warning messages."""
    level_order = {
        "watch": [WarningLevel.WATCH, WarningLevel.WARNING, WarningLevel.SEVERE, WarningLevel.CRITICAL],
        "warning": [WarningLevel.WARNING, WarningLevel.SEVERE, WarningLevel.CRITICAL],
        "severe": [WarningLevel.SEVERE, WarningLevel.CRITICAL],
        "critical": [WarningLevel.CRITICAL],
    }
    allowed_levels = level_order.get(threshold, level_order["watch"])

    warnings: List[str] = []

    for cyclone in cyclones:
        if cyclone.warning_level not in allowed_levels:
            continue

        eye_name = cyclone.eye.split("/")[-1] if "/" in cyclone.eye else cyclone.eye

        if cyclone.warning_level == WarningLevel.CRITICAL:
            warnings.append(
                f"⛈ CRITICAL STORM WARNING: {cyclone.eye} — {cyclone.category_label}. "
                f"Bug vorticity {cyclone.vorticity:+.1f}, "
                f"{cyclone.probability:.0%} probability of breaking change "
                f"in dependents within 2 sprints. "
                f"Spiral includes: {', '.join(cyclone.spiral_files[:5])}"
            )
        elif cyclone.warning_level == WarningLevel.SEVERE:
            warnings.append(
                f"🌪 SEVERE WARNING: {cyclone.eye} — {cyclone.category_label}. "
                f"Bug vorticity {cyclone.vorticity:+.1f}. "
                f"Forecast path: {' → '.join(cyclone.path_forecast[:3])}"
            )
        elif cyclone.warning_level == WarningLevel.WARNING:
            warnings.append(
                f"🌀 WARNING: {cyclone.eye} — {cyclone.category_label}. "
                f"Bug vorticity {cyclone.vorticity:+.1f}. "
                f"Monitor for escalation."
            )
        else:
            warnings.append(
                f"☉ WATCH: {cyclone.eye} — potential instability detected. "
                f"Vorticity {cyclone.vorticity:+.1f}."
            )

    return warnings
