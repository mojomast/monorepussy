"""Atmospheric field computation — temperature, pressure, humidity, wind, dew point.

Maps git/code properties to meteorological analogues using real equations.
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple

from ussy_isobar.scanner import ScanResult, FileHistory


# ── Constants ──────────────────────────────────────────────────────────
R_SPRINT = 8.314  # "Code gas constant" — average change energy per commit in a sprint
GRAVITY = 9.81  # Base dependency pull
FRONT_THRESHOLD = 15.0  # Min temperature gradient for front detection
CYCLONE_VORTICITY_THRESHOLD = 1.0  # Min vorticity for cyclone warning
DEW_POINT_BASE = 20.0  # Base dew point temperature


@dataclass
class AtmosphericProfile:
    """Complete atmospheric profile for a single file."""
    filepath: str
    temperature: float = 0.0  # °C — change velocity
    pressure: float = 0.0  # "mb" — dependency load
    humidity: float = 0.0  # % — coupling density
    wind_speed: float = 0.0  # "kt" — co-change speed
    wind_direction: str = "N"  # co-change direction
    dew_point: float = 0.0  # °C — bug emergence threshold
    bug_vorticity: float = 0.0  # cyclonic rotation
    barometric_tendency: float = 0.0  # pressure trend
    dependents: Set[str] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)
    co_change_files: Dict[str, float] = field(default_factory=dict)

    @property
    def is_hot(self) -> bool:
        return self.temperature > 50.0

    @property
    def is_cold(self) -> bool:
        return self.temperature < 10.0

    @property
    def is_high_pressure(self) -> bool:
        return self.pressure > 20.0

    @property
    def is_humid(self) -> bool:
        return self.humidity > 70.0

    @property
    def is_cyclonic(self) -> bool:
        return self.bug_vorticity > CYCLONE_VORTICITY_THRESHOLD

    @property
    def internal_energy(self) -> float:
        """PV = nRT — files with high temp AND high pressure are volatile AND impactful."""
        return self.pressure * (self.temperature / 100.0 + 0.01)

    @property
    def storm_probability(self) -> float:
        """Probability of breaking changes in dependents within 2 sprints."""
        if self.temperature < 10 and self.humidity < 50:
            return 0.05
        prob = 0.1
        prob += (self.temperature / 100.0) * 0.4
        prob += (self.humidity / 100.0) * 0.2
        prob += min(self.bug_vorticity / 5.0, 1.0) * 0.2
        return min(prob, 1.0)

    def category_label(self) -> str:
        """Human-readable weather category."""
        if self.is_cyclonic and self.is_hot:
            return "TROPICAL STORM"
        if self.is_hot and self.is_humid:
            return "THUNDERSTORM"
        if self.is_hot and self.is_high_pressure:
            return "HEAT DOME"
        if self.is_cold and self.is_high_pressure:
            return "ANTICYCLONE"
        if self.is_hot:
            return "WARM"
        if self.is_cold:
            return "COLD"
        if self.is_humid:
            return "HUMID"
        return "FAIR"


@dataclass
class AtmosphericField:
    """Complete atmospheric field for a workspace."""
    profiles: Dict[str, AtmosphericProfile] = field(default_factory=dict)
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    root: str = ""
    sprint_number: int = 0

    def get_profile(self, filepath: str) -> Optional[AtmosphericProfile]:
        return self.profiles.get(filepath)

    def hot_files(self, threshold: float = 50.0) -> List[AtmosphericProfile]:
        return sorted(
            [p for p in self.profiles.values() if p.temperature >= threshold],
            key=lambda p: p.temperature,
            reverse=True,
        )

    def cold_files(self, threshold: float = 10.0) -> List[AtmosphericProfile]:
        return sorted(
            [p for p in self.profiles.values() if p.temperature <= threshold],
            key=lambda p: p.temperature,
        )

    def high_pressure_files(self, threshold: float = 20.0) -> List[AtmosphericProfile]:
        return sorted(
            [p for p in self.profiles.values() if p.pressure >= threshold],
            key=lambda p: p.pressure,
            reverse=True,
        )

    def cyclonic_files(self) -> List[AtmosphericProfile]:
        return sorted(
            [p for p in self.profiles.values() if p.is_cyclonic],
            key=lambda p: p.bug_vorticity,
            reverse=True,
        )


def compute_temperature(history: FileHistory, num_weeks: int = 4,
                        now: Optional[datetime] = None) -> float:
    """Compute temperature field using exponential moving average.

    0°C = no changes in 4 weeks, 100°C = daily changes.
    Uses exponential weighting by recency (recent commits matter more).
    """
    if not history.commits:
        return 0.0
    if now is None:
        now = datetime.now(timezone.utc)

    start = now - timedelta(weeks=num_weeks)
    recent_commits = history.commits_in_period(start, now)

    if not recent_commits:
        return 0.0

    # Weighted by recency: more recent = more weight
    total_weight = 0.0
    for commit in recent_commits:
        age_days = (now - commit.timestamp).total_seconds() / 86400.0
        weight = math.exp(-age_days / (num_weeks * 3.5))  # decay constant
        total_weight += weight

    # Normalize: 1 commit/day for 4 weeks = ~28 commits → 100°C
    max_weighted_commits = num_weeks * 7  # daily commits over the period
    temperature = (total_weight / max_weighted_commits) * 100.0

    return min(max(temperature, 0.0), 100.0)


def compute_pressure(filepath: str, profiles: Dict[str, AtmosphericProfile],
                     import_graph: Dict[str, Set[str]]) -> float:
    """Compute pressure field using the hydrostatic equation.

    dp/dz = -ρg → dependency load = (coupling_density)(gravity)
    Pressure = count of unique importers × their average temperature.
    A file imported by 50 hot files has much higher pressure than one imported by 50 cold.
    """
    # Find who imports this file
    importers: Set[str] = set()
    for src, deps in import_graph.items():
        if filepath in deps:
            importers.add(src)

    if not importers:
        return 0.0

    # Average temperature of importers
    avg_temp = 0.0
    count = 0
    for imp in importers:
        if imp in profiles:
            avg_temp += profiles[imp].temperature
            count += 1

    if count > 0:
        avg_temp /= count

    # Pressure = number of importers * (1 + avg_temp/100)
    # More importers = higher pressure; hotter importers = more pressure
    pressure = len(importers) * (1.0 + avg_temp / 100.0) * (GRAVITY / 10.0)

    return pressure


def compute_humidity(filepath: str, import_graph: Dict[str, Set[str]]) -> float:
    """Compute humidity — coupling density (bidirectional import count).

    High humidity = tangled imports. 0% = no imports, 100% = maximally coupled.
    """
    deps_of_file = import_graph.get(filepath, set())

    # Who imports this file
    importers = set()
    for src, deps in import_graph.items():
        if filepath in deps:
            importers.add(src)

    total_connections = len(deps_of_file) + len(importers)

    if total_connections == 0:
        return 0.0

    # Normalize to 0-100 range (capped at ~20 connections → 100%)
    humidity = min(total_connections * 5.0, 100.0)
    return humidity


def compute_wind(filepath: str, co_changes: Dict[Tuple[str, str], int],
                 profiles: Dict[str, AtmosphericProfile]) -> Tuple[float, str, Dict[str, float]]:
    """Compute wind — change propagation direction and speed from co-change analysis.

    Returns (speed, direction, co_change_map).
    """
    co_change_map: Dict[str, float] = {}

    for (f1, f2), count in co_changes.items():
        if f1 == filepath:
            co_change_map[f2] = count
        elif f2 == filepath:
            co_change_map[f1] = count

    if not co_change_map:
        return 0.0, "CALM", co_change_map

    # Wind speed: total co-change count
    total_co = sum(co_change_map.values())
    speed = min(total_co * 2.0, 100.0)  # scale to "knots"

    # Wind direction: strongest co-change partner determines direction
    strongest = max(co_change_map, key=co_change_map.get)  # type: ignore
    direction = _direction_from_path(filepath, strongest)

    return speed, direction, co_change_map


def _direction_from_path(source: str, target: str) -> str:
    """Derive a compass direction from file paths (metaphorical)."""
    # Compare directory depth and position
    s_parts = source.replace("\\", "/").split("/")
    t_parts = target.replace("\\", "/").split("/")

    if len(t_parts) > len(s_parts):
        return "S"  # deeper = south
    elif len(t_parts) < len(s_parts):
        return "N"  # shallower = north
    elif t_parts < s_parts:
        return "W"
    else:
        return "E"


def compute_dew_point(temperature: float, humidity: float) -> float:
    """Compute dew point — bug emergence threshold.

    Uses Magnus formula approximation:
    Td ≈ T - (100 - RH) / 5

    Temperature × humidity → predicted defect rate.
    """
    if humidity <= 0:
        return temperature - 20.0
    # Magnus approximation
    dew_point = temperature - ((100.0 - humidity) / 5.0)
    return dew_point


def compute_vorticity(history: FileHistory, now: Optional[datetime] = None) -> float:
    """Compute vorticity — cyclonic bug spiral indicator.

    ζ = ∂(bug_rate)/∂(change_freq) - ∂(fix_rate)/∂(severity)

    Positive vorticity = cyclonic rotation (bugs generating more bugs).
    """
    if not history.commits:
        return 0.0
    if now is None:
        now = datetime.now(timezone.utc)

    # Split into recent and older periods
    recent_start = now - timedelta(weeks=4)
    older_start = now - timedelta(weeks=8)

    recent_commits = history.commits_in_period(recent_start, now)
    older_commits = history.commits_in_period(older_start, recent_start)

    recent_bug_rate = sum(1 for c in recent_commits if c.is_bug_fix)
    older_bug_rate = sum(1 for c in older_commits if c.is_bug_fix)

    recent_change_freq = len(recent_commits)
    older_change_freq = len(older_commits)

    # ∂(bug_rate)/∂(change_freq)
    if recent_change_freq + older_change_freq > 0:
        delta_bug = recent_bug_rate - older_bug_rate
        delta_freq = recent_change_freq - older_change_freq
        if delta_freq != 0:
            bug_gradient = delta_bug / delta_freq
        else:
            bug_gradient = float(delta_bug)
    else:
        bug_gradient = 0.0

    # Severity proxy: insertions/deletions ratio
    recent_ins = sum(c.insertions for c in recent_commits)
    recent_del = sum(c.deletions for c in recent_commits)
    older_ins = sum(c.insertions for c in older_commits)
    older_del = sum(c.deletions for c in older_commits)

    recent_severity = recent_del / max(recent_ins, 1)
    older_severity = older_del / max(older_ins, 1)

    recent_fix_rate = recent_bug_rate / max(recent_change_freq, 1)
    older_fix_rate = older_bug_rate / max(older_change_freq, 1)

    delta_fix = recent_fix_rate - older_fix_rate
    delta_severity = recent_severity - older_severity

    fix_gradient = delta_fix / delta_severity if delta_severity != 0 else 0.0

    vorticity = bug_gradient - fix_gradient
    return vorticity


def compute_barometric_tendency(history: FileHistory, now: Optional[datetime] = None) -> float:
    """Compute barometric tendency — 3-sprint pressure trend.

    Change in dependency load over last 3 sprints (6 weeks).
    """
    if not history.commits:
        return 0.0
    if now is None:
        now = datetime.now(timezone.utc)

    # Compare activity in last 2 weeks vs previous 4 weeks
    recent_start = now - timedelta(weeks=2)
    older_start = now - timedelta(weeks=6)

    recent = history.commits_in_period(recent_start, now)
    older = history.commits_in_period(older_start, recent_start)

    recent_activity = len(recent)
    older_activity = len(older)

    if older_activity == 0:
        return float(recent_activity) * 0.5

    return (recent_activity - older_activity) / max(older_activity, 1) * 10.0


def compute_fields(scan_result: ScanResult, now: Optional[datetime] = None) -> AtmosphericField:
    """Compute all atmospheric fields from a scan result."""
    if now is None:
        now = datetime.now(timezone.utc)

    field_result = AtmosphericField(
        root=scan_result.root,
        computed_at=now,
    )

    # First pass: compute temperature and humidity (don't depend on other profiles)
    for filepath, history in scan_result.file_histories.items():
        profile = AtmosphericProfile(filepath=filepath)
        profile.temperature = compute_temperature(history, now=now)
        profile.humidity = compute_humidity(filepath, scan_result.import_graph)
        profile.bug_vorticity = compute_vorticity(history, now)
        profile.barometric_tendency = compute_barometric_tendency(history, now)
        field_result.profiles[filepath] = profile

    # Second pass: compute pressure (depends on other profiles' temperatures)
    for filepath, profile in field_result.profiles.items():
        profile.pressure = compute_pressure(
            filepath, field_result.profiles, scan_result.import_graph
        )
        profile.dew_point = compute_dew_point(profile.temperature, profile.humidity)

    # Third pass: compute wind (depends on co-changes)
    for filepath, profile in field_result.profiles.items():
        speed, direction, co_change_map = compute_wind(
            filepath, scan_result.co_changes, field_result.profiles
        )
        profile.wind_speed = speed
        profile.wind_direction = direction
        profile.co_change_files = co_change_map

    # Populate dependents and dependencies
    for filepath, profile in field_result.profiles.items():
        deps = scan_result.import_graph.get(filepath, set())
        profile.dependencies = set(deps)
        for src, src_deps in scan_result.import_graph.items():
            if filepath in src_deps:
                profile.dependents.add(src)

    return field_result
