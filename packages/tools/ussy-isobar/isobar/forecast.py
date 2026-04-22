"""Forecast model — semi-Lagrangian advection of atmospheric fields.

Projects current atmospheric fields forward in time using the "wind" field
(co-change patterns). Like weather forecasting, accuracy decreases with range.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from isobar.fields import AtmosphericField, AtmosphericProfile


@dataclass
class ForecastStep:
    """A single forecast step (one sprint ahead)."""
    sprint_offset: int  # 1 = next sprint, 2 = two sprints ahead, etc.
    profiles: Dict[str, AtmosphericProfile] = field(default_factory=dict)
    confidence: float = 1.0  # Confidence decreases with range


@dataclass
class Forecast:
    """Complete forecast result."""
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    steps: List[ForecastStep] = field(default_factory=list)
    file_forecast: Optional[str] = None  # If forecasting a specific file

    def get_step(self, sprint_offset: int) -> Optional[ForecastStep]:
        for step in self.steps:
            if step.sprint_offset == sprint_offset:
                return step
        return None


def _advect_temperature(profile: AtmosphericProfile, wind_factor: float,
                        current_field: AtmosphericField) -> float:
    """Advect temperature forward using wind field.

    Temperature tends to: increase if wind brings hot air, decrease if calm.
    """
    # Base: current temperature
    base_temp = profile.temperature

    # Advection: wind moves temperature from co-change sources
    advection = 0.0
    for co_file, strength in profile.co_change_files.items():
        co_profile = current_field.get_profile(co_file)
        if co_profile:
            # Wind carries temperature from co-change partners
            weight = strength / max(sum(profile.co_change_files.values()), 1)
            advection += (co_profile.temperature - base_temp) * weight * 0.3

    # Barometric tendency adds momentum
    tendency_factor = profile.barometric_tendency * 0.5

    # Damping toward mean (regression to mean)
    all_temps = [p.temperature for p in current_field.profiles.values()]
    mean_temp = sum(all_temps) / max(len(all_temps), 1)
    regression = (mean_temp - base_temp) * 0.1

    new_temp = base_temp + advection + tendency_factor + regression
    return max(0.0, min(100.0, new_temp))


def _advect_humidity(profile: AtmosphericProfile, temperature_change: float) -> float:
    """Advect humidity — coupling tends to increase with temperature."""
    base = profile.humidity
    # Higher temperature → more changes → more coupling
    humidity_change = temperature_change * 0.2
    # Slight regression to mean
    regression = (50.0 - base) * 0.05
    return max(0.0, min(100.0, base + humidity_change + regression))


def _advect_pressure(profile: AtmosphericProfile, humidity_change: float) -> float:
    """Advect pressure — more coupling → more dependents → higher pressure."""
    base = profile.pressure
    pressure_change = humidity_change * 0.5
    regression = -base * 0.05  # Slight decay
    return max(0.0, base + pressure_change + regression)


def generate_forecast(atm_field: AtmosphericField,
                      num_sprints: int = 5,
                      file_filter: Optional[str] = None) -> Forecast:
    """Generate a forecast using semi-Lagrangian advection.

    Each sprint is approximately 2 weeks.
    Confidence decreases with range (like real weather forecasts).
    """
    forecast = Forecast(file_forecast=file_filter)

    # Start with current field as the basis
    current_profiles = {
        fp: AtmosphericProfile(
            filepath=p.filepath,
            temperature=p.temperature,
            pressure=p.pressure,
            humidity=p.humidity,
            wind_speed=p.wind_speed,
            wind_direction=p.wind_direction,
            dew_point=p.dew_point,
            bug_vorticity=p.bug_vorticity,
            barometric_tendency=p.barometric_tendency,
            dependents=set(p.dependents),
            dependencies=set(p.dependencies),
            co_change_files=dict(p.co_change_files),
        )
        for fp, p in atm_field.profiles.items()
    }

    prev_profiles = current_profiles

    for sprint in range(1, num_sprints + 1):
        step = ForecastStep(
            sprint_offset=sprint,
            confidence=max(0.1, 1.0 / (1.0 + sprint * 0.3)),  # Decay with range
        )

        for fp, prev in prev_profiles.items():
            if file_filter and fp != file_filter:
                continue

            new_temp = _advect_temperature(prev, prev.wind_speed, atm_field)
            new_humidity = _advect_humidity(prev, new_temp - prev.temperature)
            new_pressure = _advect_pressure(prev, new_humidity - prev.humidity)
            new_dew_point = prev.dew_point + (new_temp - prev.temperature) * 0.5

            new_profile = AtmosphericProfile(
                filepath=fp,
                temperature=new_temp,
                pressure=new_pressure,
                humidity=new_humidity,
                wind_speed=prev.wind_speed * (1.0 + sprint * 0.02),  # Slight increase
                wind_direction=prev.wind_direction,
                dew_point=max(-20.0, min(100.0, new_dew_point)),
                bug_vorticity=prev.bug_vorticity * (1.0 - sprint * 0.05),  # Decay
                barometric_tendency=prev.barometric_tendency * 0.8,  # Decay
                dependents=set(prev.dependents),
                dependencies=set(prev.dependencies),
                co_change_files=dict(prev.co_change_files),
            )
            step.profiles[fp] = new_profile

        forecast.steps.append(step)
        prev_profiles = step.profiles

    return forecast


def format_forecast(forecast: Forecast) -> str:
    """Format forecast into a human-readable report."""
    lines: List[str] = []
    lines.append("FORECAST — Semi-Lagrangian Advection Model")
    lines.append("=" * 55)
    lines.append("")

    if forecast.file_forecast:
        lines.append(f"Target: {forecast.file_forecast}")
        lines.append("")

    for step in forecast.steps:
        lines.append(f"  Sprint +{step.sprint_offset} "
                     f"(confidence: {step.confidence:.0%})")
        lines.append("  " + "-" * 45)

        # Show top files by temperature
        sorted_profiles = sorted(
            step.profiles.values(),
            key=lambda p: p.temperature,
            reverse=True,
        )

        for p in sorted_profiles[:8]:
            name = p.filepath.split("/")[-1] if "/" in p.filepath else p.filepath
            trend = ""
            if p.barometric_tendency > 0.5:
                trend = "↑"
            elif p.barometric_tendency < -0.5:
                trend = "↓"
            lines.append(
                f"    {name:30s}  {p.temperature:5.1f}°C  "
                f"{p.pressure:5.1f}mb  {p.humidity:4.0f}%rh  {trend}"
            )
        lines.append("")

    return "\n".join(lines)
