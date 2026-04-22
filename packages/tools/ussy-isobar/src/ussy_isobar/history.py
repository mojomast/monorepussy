"""History analysis — weather conditions over time, sprint comparisons."""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from ussy_isobar.fields import AtmosphericField, AtmosphericProfile, compute_fields
from ussy_isobar.scanner import ScanResult, GitScanner, FileHistory


def compute_historical_fields(
    scan_result: ScanResult,
    period_days: int = 30,
    interval_days: int = 7,
    now: Optional[datetime] = None,
) -> List[Tuple[datetime, AtmosphericField]]:
    """Compute atmospheric fields at regular intervals over a time period.

    Returns a list of (timestamp, field) tuples showing how the weather evolved.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    results: List[Tuple[datetime, AtmosphericField]] = []
    start = now - timedelta(days=period_days)

    # Generate intervals
    current = start
    while current <= now:
        # Filter commits to only those before 'current'
        filtered_result = ScanResult(
            root=scan_result.root,
            scan_time=current,
        )

        for filepath, history in scan_result.file_histories.items():
            filtered_commits = [c for c in history.commits if c.timestamp <= current]
            if filtered_commits:
                from ussy_isobar.scanner import FileHistory as FH
                filtered_history = FH(filepath=filepath, commits=filtered_commits)
                filtered_result.file_histories[filepath] = filtered_history

        filtered_result.import_graph = scan_result.import_graph

        # Rebuild co-change map from filtered commits
        from collections import defaultdict
        for filepath, history in filtered_result.file_histories.items():
            for commit in history.commits:
                files = commit.files_changed
                for i in range(len(files)):
                    for j in range(i + 1, len(files)):
                        pair = tuple(sorted([files[i], files[j]]))
                        filtered_result.co_changes[pair] = (
                            filtered_result.co_changes.get(pair, 0) + 1
                        )

        field = compute_fields(filtered_result, now=current)
        results.append((current, field))

        current += timedelta(days=interval_days)

    return results


def compare_sprints(
    field_a: AtmosphericField,
    field_b: AtmosphericField,
    label_a: str = "Sprint A",
    label_b: str = "Sprint B",
) -> str:
    """Compare atmospheric conditions between two sprints."""
    lines: List[str] = []
    lines.append(f"WEATHER COMPARISON: {label_a} vs {label_b}")
    lines.append("=" * 55)
    lines.append("")

    # Find common files
    common = set(field_a.profiles.keys()) & set(field_b.profiles.keys())
    if not common:
        lines.append("  No common files found between the two periods.")
        return "\n".join(lines)

    # Compute deltas
    deltas: Dict[str, Dict[str, float]] = {}
    for fp in common:
        pa = field_a.profiles[fp]
        pb = field_b.profiles[fp]
        deltas[fp] = {
            "temp": pb.temperature - pa.temperature,
            "pressure": pb.pressure - pa.pressure,
            "humidity": pb.humidity - pa.humidity,
            "vorticity": pb.bug_vorticity - pa.bug_vorticity,
        }

    # Biggest temperature changes
    lines.append("  TEMPERATURE CHANGES:")
    by_temp = sorted(deltas.items(), key=lambda x: abs(x[1]["temp"]), reverse=True)
    for fp, delta in by_temp[:8]:
        name = fp.split("/")[-1] if "/" in fp else fp
        arrow = "↑" if delta["temp"] > 0 else "↓"
        lines.append(f"    {name:25s} {delta['temp']:+6.1f}°C {arrow}")
    lines.append("")

    # Biggest pressure changes
    lines.append("  PRESSURE CHANGES:")
    by_pres = sorted(deltas.items(), key=lambda x: abs(x[1]["pressure"]), reverse=True)
    for fp, delta in by_pres[:5]:
        name = fp.split("/")[-1] if "/" in fp else fp
        arrow = "↑" if delta["pressure"] > 0 else "↓"
        lines.append(f"    {name:25s} {delta['pressure']:+6.1f}mb {arrow}")
    lines.append("")

    # Aggregate
    avg_temp_delta = sum(d["temp"] for d in deltas.values()) / len(deltas)
    avg_pres_delta = sum(d["pressure"] for d in deltas.values()) / len(deltas)

    lines.append(f"  Average temperature change: {avg_temp_delta:+.1f}°C")
    lines.append(f"  Average pressure change:    {avg_pres_delta:+.1f}mb")

    hotter = sum(1 for d in deltas.values() if d["temp"] > 5)
    colder = sum(1 for d in deltas.values() if d["temp"] < -5)
    lines.append(f"  Files warming:  {hotter}")
    lines.append(f"  Files cooling:  {colder}")

    return "\n".join(lines)


def format_history(history_data: List[Tuple[datetime, AtmosphericField]]) -> str:
    """Format historical weather data into a readable report."""
    lines: List[str] = []
    lines.append("HISTORICAL WEATHER")
    lines.append("=" * 50)
    lines.append("")

    if not history_data:
        lines.append("  No historical data available.")
        return "\n".join(lines)

    for timestamp, field in history_data:
        date_str = timestamp.strftime("%Y-%m-%d")
        if not field.profiles:
            lines.append(f"  {date_str}: No data")
            continue

        temps = [p.temperature for p in field.profiles.values()]
        avg_temp = sum(temps) / len(temps)
        max_temp = max(temps)

        cyclone_count = sum(1 for p in field.profiles.values() if p.is_cyclonic)

        lines.append(f"  {date_str}: avg {avg_temp:.1f}°C, "
                     f"max {max_temp:.1f}°C, "
                     f"{cyclone_count} cyclone(s)")

    return "\n".join(lines)
