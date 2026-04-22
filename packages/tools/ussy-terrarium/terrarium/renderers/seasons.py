"""Seasonal view — show the ecosystem evolving over time."""

import os
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ..ecosystem.model import Ecosystem, Organism, build_ecosystem
from ..ecosystem.organisms import Vitality, VITALITY_COLORS, ANSI_RESET
from ..metrics.models import ProjectMetrics, ModuleMetrics
from ..metrics.engine import MetricsEngine


# Season definitions based on development activity
SEASON_NAMES = {
    "spring": "🌱 Spring — New growth, fresh code",
    "summer": "☀️ Summer — Maturity, active maintenance",
    "autumn": "🍂 Autumn — Refactoring, decay beginning",
    "winter": "❄️ Winter — Frozen, abandoned code",
}


def classify_season(
    churn_rate: float,
    coverage: float,
    days_since_change: int,
) -> str:
    """Classify the current season for a module.

    Args:
        churn_rate: Commits per month.
        coverage: Test coverage (0-1).
        days_since_change: Days since last change.

    Returns:
        Season name: 'spring', 'summer', 'autumn', or 'winter'.
    """
    if days_since_change > 365:
        return "winter"
    elif days_since_change > 180:
        return "autumn"
    elif churn_rate > 3.0 and coverage < 0.5:
        return "spring"  # Rapid, untested growth
    elif churn_rate > 1.0 or coverage >= 0.5:
        return "summer"  # Active and maintained
    else:
        return "autumn"


def get_git_history(
    root_path: str,
    since: Optional[str] = None,
) -> List[Dict]:
    """Get project-level git history.

    Returns:
        List of dicts with 'date', 'count' keys, sorted chronologically.
    """
    cmd = ["git", "log", "--format=%ct"]
    if since:
        cmd.extend(["--since", since])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, cwd=root_path
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    timestamps = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            timestamps.append(int(line))
        except ValueError:
            continue

    if not timestamps:
        return []

    # Group by month
    month_counts: Dict[str, int] = {}
    for ts in timestamps:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        key = dt.strftime("%Y-%m")
        month_counts[key] = month_counts.get(key, 0) + 1

    history = []
    for key in sorted(month_counts.keys()):
        history.append({
            "month": key,
            "count": month_counts[key],
        })

    return history


def render_seasons_view(
    ecosystem: Ecosystem,
    history: Optional[List[Dict]] = None,
) -> str:
    """Render a seasonal view of the ecosystem.

    Args:
        ecosystem: The current ecosystem.
        history: Optional git history (list of month/count dicts).

    Returns:
        A seasonal timeline string.
    """
    lines = []
    lines.append("🌍 SEASONAL VIEW — Ecosystem Over Time")
    lines.append("=" * 50)

    # Classify each organism's season
    season_counts = {"spring": 0, "summer": 0, "autumn": 0, "winter": 0}
    season_organisms: Dict[str, List[Organism]] = {
        "spring": [], "summer": [], "autumn": [], "winter": [],
    }

    for organism in ecosystem.organisms.values():
        # We need the original metrics to compute seasons
        # Use heuristics from organism properties
        churn_rate = 0.0
        coverage = 0.0
        days_since = 0

        # Infer from symptoms
        for s in organism.symptoms:
            if "churn" in s.lower():
                import re
                match = re.search(r"([\d.]+)x", s)
                if match:
                    churn_rate = float(match.group(1))
            if "coverage" in s.lower():
                match = re.search(r"([\d.]+)%", s)
                if match:
                    coverage = float(match.group(1)) / 100.0

        # Use stability tier as proxy for days since change
        stability_days = {
            "seedling": 7,
            "sapling": 60,
            "mature": 200,
            "old_growth": 800,
        }
        days_since = stability_days.get(organism.stability_tier, 30)

        season = classify_season(churn_rate, coverage, days_since)
        season_counts[season] += 1
        season_organisms[season].append(organism)

    # Render each season
    for season in ["spring", "summer", "autumn", "winter"]:
        count = season_counts[season]
        label = SEASON_NAMES[season]
        color = {
            "spring": VITALITY_COLORS[Vitality.THRIVING],
            "summer": VITALITY_COLORS[Vitality.HEALTHY],
            "autumn": VITALITY_COLORS[Vitality.STRESSED],
            "winter": VITALITY_COLORS[Vitality.DEAD],
        }.get(season, "")

        bar = "█" * count if count else "░"
        lines.append(f"{color}{label}{ANSI_RESET}")
        lines.append(f"  {color}{bar} ({count} modules){ANSI_RESET}")

        for organism in sorted(season_organisms[season], key=lambda o: o.path)[:5]:
            lines.append(f"    {organism.emoji} {organism.path}")
        if len(season_organisms[season]) > 5:
            lines.append(f"    ... and {len(season_organisms[season]) - 5} more")

        lines.append("")

    # Timeline
    if history:
        lines.append("Timeline:")
        max_count = max(h["count"] for h in history) if history else 1
        for entry in history[-12:]:  # Last 12 months
            bar_len = int((entry["count"] / max(max_count, 1)) * 30)
            bar = "▓" * bar_len
            lines.append(f"  {entry['month']}: {bar} ({entry['count']})")

    return "\n".join(lines)


def render_seasons_from_project(
    root_path: str,
    since: Optional[str] = None,
) -> str:
    """Render the seasons view by analyzing a project.

    Args:
        root_path: Path to the project root.
        since: Optional date filter.

    Returns:
        Seasons view string.
    """
    engine = MetricsEngine(root_path, since)
    project = engine.scan()
    ecosystem = build_ecosystem(project)
    history = get_git_history(root_path, since)
    return render_seasons_view(ecosystem, history)
