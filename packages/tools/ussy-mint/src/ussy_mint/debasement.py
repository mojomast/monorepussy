"""Debasement tracking — version quality over time.

Tracks how a package's Sheldon grade changes across versions,
detects debasement patterns, and predicts when a package becomes worthless.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ussy_mint.models import DebasementCurve, get_grade_category


def compute_debasement_rate(
    versions: list[tuple[str, int, datetime]],
) -> float:
    """Compute the average grade change per month across versions.

    rate = sum(grade_i - grade_{i+1}) / sum(time_{i+1} - time_i)

    Negative rate = debasement (quality declining).
    Positive rate = improvement.
    Zero rate = stable.

    Args:
        versions: List of (version_str, sheldon_grade, date) sorted by date

    Returns:
        Grade change per month. Negative = debasement.
    """
    if len(versions) < 2:
        return 0.0

    total_grade_change = 0.0
    total_time_months = 0.0

    for i in range(len(versions) - 1):
        grade_current = versions[i][1]
        grade_next = versions[i + 1][1]
        date_current = versions[i][2]
        date_next = versions[i + 1][2]

        grade_diff = grade_current - grade_next  # positive = debasement
        time_diff = (date_next - date_current).days / 30.44  # approximate months

        total_grade_change += grade_diff
        total_time_months += time_diff

    if total_time_months == 0:
        return 0.0

    return total_grade_change / total_time_months


def project_zero_date(
    current_grade: int,
    debasement_rate: float,
    current_date: datetime,
) -> Optional[datetime]:
    """Project when a package will reach grade P-1 (abandoned).

    Args:
        current_grade: Current Sheldon grade
        debasement_rate: Grade points lost per month (positive = losing grade)
        current_date: Current date

    Returns:
        Estimated date when grade hits 1, or None if not degrading
    """
    if debasement_rate <= 0:
        # Not degrading or improving
        return None

    months_until_zero = (current_grade - 1) / debasement_rate
    if months_until_zero <= 0:
        return current_date

    days_until_zero = months_until_zero * 30.44
    from datetime import timedelta
    return current_date + timedelta(days=days_until_zero)


def detect_recoinage_events(
    versions: list[tuple[str, int, datetime]],
    threshold: int = 20,
) -> list[int]:
    """Detect recoinage events — major version rewrites.

    A recoinage event is when the Sheldon grade jumps up by more than
    `threshold` points between consecutive versions, indicating a
    major rewrite that restored quality.

    Args:
        versions: List of (version_str, sheldon_grade, date) sorted by date
        threshold: Minimum grade increase to count as recoinage (default 20)

    Returns:
        List of indices where recoinage events occurred
    """
    recoinage_events = []
    for i in range(1, len(versions)):
        grade_prev = versions[i - 1][1]
        grade_curr = versions[i][1]
        if grade_curr - grade_prev > threshold:
            recoinage_events.append(i)
    return recoinage_events


def detect_clipping(
    versions: list[tuple[str, int, datetime, dict]],
) -> list[int]:
    """Detect clipping — feature removal in minor/patch releases.

    Clipping is when a minor or patch release removes functionality
    (violating semver), reducing the package's intrinsic value.

    Args:
        versions: List of (version_str, grade, date, metadata_dict)
            metadata_dict should contain "exports_added" and "exports_removed" keys

    Returns:
        List of indices where clipping was detected
    """
    clipping_events = []
    for i, (ver, grade, date, meta) in enumerate(versions):
        exports_removed = meta.get("exports_removed", 0)
        # Check if this is a minor or patch release (not major)
        parts = ver.lstrip("v").split(".")
        if len(parts) >= 2 and parts[0] == "0" or (len(parts) >= 2 and parts[1] != "0"):
            # Minor or patch release
            if exports_removed > 0:
                clipping_events.append(i)
    return clipping_events


def analyze_debasement(
    package: str,
    versions: list[tuple[str, int, datetime]],
) -> DebasementCurve:
    """Full debasement analysis for a package.

    Args:
        package: Package name
        versions: List of (version, grade, date) sorted chronologically

    Returns:
        DebasementCurve with all computed values
    """
    rate = compute_debasement_rate(versions)
    recoinage_events = detect_recoinage_events(versions)

    projected_zero = None
    if versions and rate > 0:
        latest_grade = versions[-1][1]
        latest_date = versions[-1][2]
        projected_zero = project_zero_date(latest_grade, rate, latest_date)

    return DebasementCurve(
        package=package,
        versions=versions,
        debasement_rate=round(rate, 2),
        projected_zero_date=projected_zero,
        recoinage_events=recoinage_events,
    )


def format_debasement_bar(grade: int, max_grade: int = 70, width: int = 28) -> str:
    """Format a visual debasement bar for display.

    Args:
        grade: Sheldon grade (1-70)
        max_grade: Maximum possible grade (default 70)
        width: Bar width in characters

    Returns:
        String bar like '███████████████████████████▌'
    """
    fraction = grade / max_grade
    filled = fraction * width
    full_chars = int(filled)
    remainder = filled - full_chars

    bar = "█" * full_chars
    if remainder > 0.75:
        bar += "▋"
    elif remainder > 0.5:
        bar += "▌"
    elif remainder > 0.25:
        bar += "▍"
    elif remainder > 0:
        bar += "▎"

    return bar


def format_debasement_report(curve: DebasementCurve) -> str:
    """Format a debasement curve as a human-readable report.

    Args:
        curve: DebasementCurve to format

    Returns:
        Formatted report string
    """
    if not curve.versions:
        return f"{curve.package}: No version data available"

    lines = [f"{curve.package} debasement curve:"]

    for ver, grade, date in curve.versions:
        bar = format_debasement_bar(grade)
        category = get_grade_category(grade)
        year = date.year
        lines.append(f"  {ver} ({year}) {category} {grade:2d} {bar}")

    if curve.debasement_rate != 0:
        rate_str = f"{curve.debasement_rate:+.2f} grade/month"
    else:
        rate_str = "stable"

    lines.append(f"  Rate: {rate_str}")

    if curve.projected_zero_date:
        lines.append(f"  Projected P-1: {curve.projected_zero_date.strftime('%Y-%m')}")

    if curve.recoinage_events:
        event_vers = [curve.versions[i][0] for i in curve.recoinage_events]
        lines.append(f"  Recoinage events: {', '.join(event_vers)}")
    else:
        lines.append("  Recoinage events: None")

    return "\n".join(lines)
