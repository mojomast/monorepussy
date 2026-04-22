"""Rain Gauge — drift frequency and convergence/divergence tracking."""

from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from .db import SoilDB


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DriftTrend:
    """Classification of drift direction for a path."""
    CONVERGING = "converging"
    DIVERGING = "diverging"
    CHAOTIC = "chaotic"
    STABLE = "stable"


class RainGauge:
    """Measures drift frequency and detects convergence/divergence patterns."""

    def __init__(self, db: SoilDB):
        self.db = db

    def measure(self, days: int = 30) -> Dict:
        """Run the rain gauge over the tracked paths.

        Args:
            days: Number of days to analyze.

        Returns:
            Dict with 'high', 'moderate', 'stable' categories,
            each containing a list of path drift info dicts.
        """
        counts = self.db.get_path_drift_counts(days)
        tracked = self.db.get_tracked_paths()

        # Include tracked paths with 0 drifts
        for path in tracked:
            if path not in counts:
                counts[path] = 0

        high = []
        moderate = []
        stable = []

        for path, count in counts.items():
            trend = self._classify_trend(path, days)
            info = {
                "path": path,
                "drift_count": count,
                "trend": trend,
            }
            if count >= 4:
                high.append(info)
            elif count >= 1:
                moderate.append(info)
            else:
                stable.append(info)

        # Sort by drift count descending
        high.sort(key=lambda x: x["drift_count"], reverse=True)
        moderate.sort(key=lambda x: x["drift_count"], reverse=True)
        stable.sort(key=lambda x: x["path"])

        return {
            "high": high,
            "moderate": moderate,
            "stable": stable,
        }

    def _classify_trend(self, path: str, days: int = 30) -> str:
        """Classify the drift trend for a single path.

        Converging: drifts are becoming less frequent.
        Diverging: drifts are becoming more frequent.
        Chaotic: no clear trend.
        Stable: no drifts.

        Args:
            path: File path.
            days: Analysis window in days.

        Returns:
            One of DriftTrend constants.
        """
        drifts = self.db.get_drift_layers(path, days)
        if not drifts:
            return DriftTrend.STABLE

        if len(drifts) < 2:
            return DriftTrend.CONVERGING

        # Split drifts into first half and second half by time
        drifts_sorted = sorted(drifts, key=lambda x: x["timestamp"])
        mid = len(drifts_sorted) // 2
        first_half = drifts_sorted[:mid]
        second_half = drifts_sorted[mid:]

        if not first_half or not second_half:
            return DriftTrend.CHAOTIC

        # Count drifts in each half
        first_count = len(first_half)
        second_count = len(second_half)

        if second_count < first_count:
            return DriftTrend.CONVERGING
        elif second_count > first_count:
            return DriftTrend.DIVERGING
        else:
            return DriftTrend.CHAOTIC

    def detect_patterns(self, days: int = 30) -> List[Dict]:
        """Detect temporal patterns in drift events.

        Looks for day-of-week patterns, actor correlations, etc.

        Args:
            days: Analysis window in days.

        Returns:
            List of pattern dicts.
        """
        drifts = self.db.get_all_drift_layers(days)
        if not drifts:
            return []

        patterns = []

        # Day-of-week pattern
        dow_counts: Dict[int, List] = {}
        for d in drifts:
            try:
                ts = datetime.fromisoformat(d["timestamp"])
            except (ValueError, TypeError):
                continue
            dow = ts.weekday()
            if dow not in dow_counts:
                dow_counts[dow] = []
            dow_counts[dow].append(d["path"])

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for dow, paths in dow_counts.items():
            path_counts = Counter(paths)
            for path, count in path_counts.items():
                total_drifts_for_path = sum(
                    1 for d in drifts if d["path"] == path
                )
                if total_drifts_for_path >= 2 and count >= total_drifts_for_path * 0.5:
                    patterns.append({
                        "type": "day_of_week",
                        "day": day_names[dow],
                        "path": path,
                        "count": count,
                        "total": total_drifts_for_path,
                        "confidence": count / total_drifts_for_path if total_drifts_for_path > 0 else 0,
                    })

        # Actor pattern
        actor_counts: Dict[str, List] = {}
        for d in drifts:
            actor = d.get("actor", "")
            if not actor:
                continue
            if actor not in actor_counts:
                actor_counts[actor] = []
            actor_counts[actor].append(d["path"])

        for actor, paths in actor_counts.items():
            path_counts = Counter(paths)
            for path, count in path_counts.items():
                if count >= 2:
                    patterns.append({
                        "type": "actor_correlation",
                        "actor": actor,
                        "path": path,
                        "count": count,
                    })

        return patterns

    def format_gauge(self, days: int = 30) -> str:
        """Format the rain gauge as a human-readable string.

        Args:
            days: Analysis window in days.

        Returns:
            Formatted string.
        """
        result = self.measure(days)
        patterns = self.detect_patterns(days)

        lines = [
            f"Rain Gauge — Drift Frequency ({days} days)",
            "═" * 47,
        ]

        trend_symbols = {
            DriftTrend.CONVERGING: "↑",
            DriftTrend.DIVERGING: "↓",
            DriftTrend.CHAOTIC: "⟳",
            DriftTrend.STABLE: "—",
        }

        if result["high"]:
            lines.append("")
            lines.append("⛈️ HIGH DRIFT — These files never stay put:")
            for info in result["high"]:
                sym = trend_symbols.get(info["trend"], "?")
                lines.append(f"  {info['path']:<40} {info['drift_count']} drifts ({info['trend']} {sym})")

        if result["moderate"]:
            lines.append("")
            lines.append("🌤️ MODERATE — Occasional drift:")
            for info in result["moderate"]:
                sym = trend_symbols.get(info["trend"], "?")
                lines.append(f"  {info['path']:<40} {info['drift_count']} drifts ({info['trend']} {sym})")

        if result["stable"]:
            lines.append("")
            lines.append("☀️ STABLE — Rock solid:")
            for info in result["stable"]:
                lines.append(f"  {info['path']:<40} {info['drift_count']} drifts")

        if patterns:
            lines.append("")
            for p in patterns:
                if p["type"] == "day_of_week":
                    lines.append(
                        f"Pattern detected: {p['path']} drifts on {p['day']} "
                        f"({p['count']}/{p['total']} times)"
                    )
                elif p["type"] == "actor_correlation":
                    lines.append(
                        f"Pattern detected: {p['path']} drifts when {p['actor']} is active"
                    )

        return "\n".join(lines)
