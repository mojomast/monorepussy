"""Synoptic weather map renderer — ASCII art of codebase atmospheric conditions."""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from ussy_isobar.fields import AtmosphericField, AtmosphericProfile
from ussy_isobar.fronts import Front, FrontType
from ussy_isobar.cyclones import Cyclone, Anticyclone


def _module_name(filepath: str) -> str:
    """Extract module name from filepath."""
    parts = filepath.replace("\\", "/").split("/")
    if len(parts) > 1:
        return parts[-2] + "/" + parts[-1]
    return parts[-1]


def _short_name(filepath: str) -> str:
    """Short name for display."""
    parts = filepath.replace("\\", "/").split("/")
    if len(parts) >= 2:
        return parts[-2] + "/"
    return parts[-1][:12]


def _temp_bar(temp: float, width: int = 10) -> str:
    """Generate a temperature bar."""
    filled = int(temp / 100 * width)
    if temp >= 70:
        char = "█"
    elif temp >= 40:
        char = "▓"
    elif temp >= 15:
        char = "░"
    else:
        char = "·"
    return char * filled + " " * (width - filled)


def _pressure_indicator(pressure: float) -> str:
    """Generate pressure indicator."""
    if pressure >= 30:
        return f"{pressure:.0f}mb"
    elif pressure >= 10:
        return f"{pressure:.0f}mb"
    else:
        return f" {pressure:.0f}mb"


def render_synoptic_map(
    atm_field: AtmosphericField,
    fronts: Optional[List[Front]] = None,
    cyclones: Optional[List[Cyclone]] = None,
    anticyclones: Optional[List[Anticyclone]] = None,
    module_filter: Optional[str] = None,
) -> str:
    """Render an ASCII synoptic weather map of the codebase."""
    if fronts is None:
        fronts = []
    if cyclones is None:
        cyclones = []
    if anticyclones is None:
        anticyclones = []

    lines: List[str] = []
    width = 57
    date_str = atm_field.computed_at.strftime("%Y-%m-%d")

    # Header
    lines.append("┌" + "─" * width + "┐")
    header = f"  ISOBAR — Synoptic Analysis — {date_str}"
    lines.append("│" + header.ljust(width) + "│")
    lines.append("│" + " " * width + "│")

    # Collect profiles to display
    profiles = list(atm_field.profiles.values())
    if module_filter:
        profiles = [p for p in profiles if module_filter in p.filepath]

    # Sort: cyclones first, then by temperature
    cyclone_eyes = {c.eye for c in cyclones}
    cyclone_profiles = sorted(
        [p for p in profiles if p.filepath in cyclone_eyes],
        key=lambda p: p.bug_vorticity,
        reverse=True,
    )
    other_profiles = sorted(
        [p for p in profiles if p.filepath not in cyclone_eyes],
        key=lambda p: p.temperature,
        reverse=True,
    )

    # Show top 6 profiles (prioritize cyclones and hot files)
    display_profiles = cyclone_profiles[:3] + other_profiles[:3]

    for p in display_profiles:
        name = _short_name(p.filepath)
        is_cyclone = p.filepath in cyclone_eyes
        is_anticyclone = any(a.center == p.filepath for a in anticyclones)

        if is_cyclone:
            symbol = "(L)"
        elif is_anticyclone:
            symbol = "(H)"
        elif p.is_high_pressure:
            symbol = "(H)"
        elif p.is_hot:
            symbol = "(L)"
        else:
            symbol = "   "

        temp_str = f"{p.temperature:.0f}°C"
        pressure_str = _pressure_indicator(p.pressure)
        humidity_str = f"{p.humidity:.0f}%rh"

        line1 = f"    ┌─{symbol}─┐  {name}"
        lines.append("│" + line1.ljust(width) + "│")

        detail = f"    │{pressure_str}│  {temp_str} {humidity_str}"
        lines.append("│" + detail.ljust(width) + "│")

        # Warning annotations
        if is_cyclone:
            cyclone_obj = next((c for c in cyclones if c.eye == p.filepath), None)
            if cyclone_obj:
                warn = f"    └─────┘  ← Cyclone! ζ={p.bug_vorticity:+.1f}"
                lines.append("│" + warn.ljust(width) + "│")
        elif is_anticyclone:
            lines.append("│" + "    └─────┘  ← Anticyclone: stable".ljust(width) + "│")
        else:
            cat = p.category_label()
            lines.append("│" + f"    └─────┘  ← {cat}".ljust(width) + "│")

        lines.append("│" + " " * width + "│")

    # Front lines
    if fronts:
        for front in fronts[:3]:
            hot_short = _short_name(front.hot_side)
            cold_short = _short_name(front.cold_side)
            if front.front_type == FrontType.WARM:
                front_line = f"  ░░░░░░░░▓▓▓▓▓▓▓░░░░░░░░  ← Warm front"
            elif front.front_type == FrontType.COLD:
                front_line = f"  ▓▓▓▓▓▓▓░░░░░░░░▓▓▓▓▓▓▓  ← Cold front"
            elif front.front_type == FrontType.OCCLUDED:
                front_line = f"  ▓▓▓▓░░░░▓▓▓▓░░░░▓▓▓▓▓  ← Occluded front"
            else:
                front_line = f"  ░░░░░░░░░░░░░░░░░░░░░░  ← Stationary front"

            lines.append("│" + front_line.ljust(width) + "│")
            detail = f"    {hot_short} ↔ {cold_short}  ΔT={front.temperature_gradient:.0f}°C"
            lines.append("│" + detail.ljust(width) + "│")
            lines.append("│" + " " * width + "│")

    # Storm warnings
    severe_cyclones = [c for c in cyclones if c.warning_level.value in ("severe", "critical")]
    if severe_cyclones:
        for c in severe_cyclones[:2]:
            eye_name = c.eye.split("/")[-1] if "/" in c.eye else c.eye
            warn1 = f"  ⛈ STORM WARNING: {eye_name} — cyclonic spiral"
            lines.append("│" + warn1.ljust(width) + "│")
            warn2 = f"    Bug vorticity {c.vorticity:+.1f}, {c.probability:.0%} prob."
            lines.append("│" + warn2.ljust(width) + "│")
            warn3 = f"    of breaking change in dependents within 2 sprints."
            lines.append("│" + warn3.ljust(width) + "│")

    lines.append("│" + " " * width + "│")

    # Footer
    lines.append("└" + "─" * width + "┘")

    return "\n".join(lines)


def render_current_conditions(atm_field: AtmosphericField) -> str:
    """Render a summary of current atmospheric conditions."""
    lines: List[str] = []
    lines.append("CURRENT CONDITIONS")
    lines.append("=" * 50)
    lines.append("")

    if not atm_field.profiles:
        lines.append("  No data available. Run 'isobar survey' first.")
        return "\n".join(lines)

    # Aggregate stats
    temps = [p.temperature for p in atm_field.profiles.values()]
    pressures = [p.pressure for p in atm_field.profiles.values()]
    humidities = [p.humidity for p in atm_field.profiles.values()]

    avg_temp = sum(temps) / len(temps)
    max_temp = max(temps)
    avg_pressure = sum(pressures) / len(pressures)
    max_pressure = max(pressures)
    avg_humidity = sum(humidities) / len(humidities)
    max_humidity = max(humidities)

    lines.append(f"  Files analyzed:     {len(atm_field.profiles)}")
    lines.append(f"  Avg temperature:    {avg_temp:.1f}°C")
    lines.append(f"  Max temperature:    {max_temp:.1f}°C")
    lines.append(f"  Avg pressure:       {avg_pressure:.1f}mb")
    lines.append(f"  Max pressure:       {max_pressure:.1f}mb")
    lines.append(f"  Avg humidity:       {avg_humidity:.1f}%rh")
    lines.append(f"  Max humidity:       {max_humidity:.1f}%rh")
    lines.append("")

    # Hot files
    hot = atm_field.hot_files()
    if hot:
        lines.append("  HOT SPOTS:")
        for p in hot[:5]:
            name = _module_name(p.filepath)
            lines.append(f"    {name:30s} {p.temperature:5.1f}°C")
        lines.append("")

    # High pressure
    high_p = atm_field.high_pressure_files()
    if high_p:
        lines.append("  HIGH PRESSURE:")
        for p in high_p[:5]:
            name = _module_name(p.filepath)
            lines.append(f"    {name:30s} {p.pressure:5.1f}mb")
        lines.append("")

    return "\n".join(lines)


def render_climate_report(profile: AtmosphericProfile) -> str:
    """Render a detailed atmospheric profile for a single file."""
    lines: List[str] = []
    lines.append(f"MICRO-CLIMATE: {profile.filepath}")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"  Temperature:       {profile.temperature:.1f}°C  ({'HOT' if profile.is_hot else 'warm' if profile.temperature > 25 else 'cool' if profile.temperature > 10 else 'COLD'})")
    lines.append(f"  Pressure:          {profile.pressure:.1f}mb  ({'HIGH' if profile.is_high_pressure else 'low'})")
    lines.append(f"  Humidity:          {profile.humidity:.1f}%rh  ({'HUMID' if profile.is_humid else 'dry'})")
    lines.append(f"  Dew point:         {profile.dew_point:.1f}°C")
    lines.append(f"  Wind:              {profile.wind_speed:.1f}kt {profile.wind_direction}")
    lines.append(f"  Bug vorticity:     {profile.bug_vorticity:+.2f}  ({'CYCLONIC' if profile.is_cyclonic else 'stable'})")
    lines.append(f"  Baro. tendency:    {profile.barometric_tendency:+.2f}")
    lines.append(f"  Internal energy:   {profile.internal_energy:.1f}")
    lines.append(f"  Storm probability: {profile.storm_probability:.1%}")
    lines.append(f"  Category:          {profile.category_label()}")
    lines.append("")

    # Dependencies
    if profile.dependencies:
        lines.append(f"  Depends on ({len(profile.dependencies)}):")
        for dep in sorted(profile.dependencies)[:8]:
            lines.append(f"    → {dep}")
        lines.append("")

    # Dependents
    if profile.dependents:
        lines.append(f"  Imported by ({len(profile.dependents)}):")
        for dep in sorted(profile.dependents)[:8]:
            lines.append(f"    ← {dep}")
        lines.append("")

    # Co-changes
    if profile.co_change_files:
        lines.append("  Co-change partners:")
        for f, count in sorted(profile.co_change_files.items(), key=lambda x: x[1], reverse=True)[:5]:
            lines.append(f"    ↔ {f} (strength: {count})")
        lines.append("")

    return "\n".join(lines)
