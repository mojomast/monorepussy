"""Scent — predictive drift detection based on historical patterns."""

from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from .db import SoilDB


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DriftPrediction:
    """A single drift prediction for a path."""

    def __init__(
        self,
        path: str,
        predicted_time: datetime,
        confidence: float,
        reason: str,
        likely_hash: str = "",
        pattern_type: str = "",
    ):
        self.path = path
        self.predicted_time = predicted_time
        self.confidence = confidence
        self.reason = reason
        self.likely_hash = likely_hash
        self.pattern_type = pattern_type


class ScentDetector:
    """Predicts future drift based on historical patterns."""

    def __init__(self, db: SoilDB):
        self.db = db

    def predict(self, days: int = 7, min_confidence: float = 0.3) -> List[DriftPrediction]:
        """Predict likely drifts in the next N days.

        Uses day-of-week patterns, actor patterns, and recurrence analysis
        to predict future drifts. No ML needed — just statistical analysis.

        Args:
            days: Number of days to predict ahead.
            min_confidence: Minimum confidence threshold (0.0-1.0).

        Returns:
            List of DriftPrediction objects, sorted by confidence desc.
        """
        drifts = self.db.get_all_drift_layers(90)  # Use 90 days of history
        if not drifts:
            return []

        predictions = []
        now = _now()
        future_end = now + timedelta(days=days)

        # Day-of-week prediction
        dow_predictions = self._predict_by_day_of_week(drifts, now, future_end, min_confidence)
        predictions.extend(dow_predictions)

        # Recurrence prediction (same drift keeps happening)
        recurrence_predictions = self._predict_by_recurrence(drifts, now, future_end, min_confidence)
        predictions.extend(recurrence_predictions)

        # Deduplicate by (path, predicted_date)
        seen = set()
        unique = []
        for p in predictions:
            key = (p.path, p.predicted_time.date())
            if key not in seen:
                seen.add(key)
                unique.append(p)

        # Filter by confidence
        unique = [p for p in unique if p.confidence >= min_confidence]

        # Sort by confidence descending, then by time
        unique.sort(key=lambda p: (-p.confidence, p.predicted_time))
        return unique

    def _predict_by_day_of_week(
        self,
        drifts: List[Dict],
        now: datetime,
        future_end: datetime,
        min_confidence: float,
    ) -> List[DriftPrediction]:
        """Predict drifts based on day-of-week patterns.

        Args:
            drifts: Historical drift layers.
            now: Current time.
            future_end: End of prediction window.
            min_confidence: Minimum confidence.

        Returns:
            List of predictions.
        """
        predictions = []

        # Group drifts by (path, day_of_week)
        path_dow: Dict[Tuple[str, int], List[Dict]] = {}
        for d in drifts:
            try:
                ts = datetime.fromisoformat(d["timestamp"])
            except (ValueError, TypeError):
                continue
            key = (d["path"], ts.weekday())
            if key not in path_dow:
                path_dow[key] = []
            path_dow[key].append(d)

        # For each path, calculate total drifts and per-dow count
        path_total: Dict[str, int] = Counter(d["path"] for d in drifts)

        for (path, dow), dow_drifts in path_dow.items():
            total = path_total.get(path, 0)
            if total < 2:
                continue

            dow_count = len(dow_drifts)
            confidence = dow_count / total

            if confidence < min_confidence:
                continue

            # Find the next occurrence of this day-of-week
            days_ahead = dow - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            predicted_time = now + timedelta(days=days_ahead)
            predicted_time = predicted_time.replace(hour=14, minute=0, second=0, microsecond=0)

            if predicted_time > future_end:
                continue

            # Find the most common drift hash for this pattern
            drift_hashes = [d["content_hash"] for d in dow_drifts if d.get("content_hash")]
            likely_hash = Counter(drift_hashes).most_common(1)[0][0] if drift_hashes else ""

            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

            predictions.append(DriftPrediction(
                path=path,
                predicted_time=predicted_time,
                confidence=round(confidence, 2),
                reason=f"Pattern: drifts on {day_names[dow]} ({dow_count}/{total} times)",
                likely_hash=likely_hash,
                pattern_type="day_of_week",
            ))

        return predictions

    def _predict_by_recurrence(
        self,
        drifts: List[Dict],
        now: datetime,
        future_end: datetime,
        min_confidence: float,
    ) -> List[DriftPrediction]:
        """Predict drifts based on recurrence of the same drift value.

        If a path keeps drifting to the same value, predict it will happen again.

        Args:
            drifts: Historical drift layers.
            now: Current time.
            future_end: End of prediction window.
            min_confidence: Minimum confidence.

        Returns:
            List of predictions.
        """
        predictions = []

        # Group drifts by path
        path_drifts: Dict[str, List[Dict]] = {}
        for d in drifts:
            path = d["path"]
            if path not in path_drifts:
                path_drifts[path] = []
            path_drifts[path].append(d)

        for path, p_drifts in path_drifts.items():
            if len(p_drifts) < 2:
                continue

            # Find the most common drift hash
            drift_hashes = [d["content_hash"] for d in p_drifts]
            hash_counter = Counter(drift_hashes)
            most_common_hash, count = hash_counter.most_common(1)[0]

            if count < 2:
                continue

            # Calculate average interval between drifts
            sorted_drifts = sorted(p_drifts, key=lambda x: x["timestamp"])
            intervals = []
            for i in range(1, len(sorted_drifts)):
                try:
                    t1 = datetime.fromisoformat(sorted_drifts[i - 1]["timestamp"])
                    t2 = datetime.fromisoformat(sorted_drifts[i]["timestamp"])
                    intervals.append((t2 - t1).total_seconds())
                except (ValueError, TypeError):
                    continue

            if not intervals:
                continue

            avg_interval = sum(intervals) / len(intervals)
            if avg_interval < 60:  # Less than 1 minute — too noisy
                continue

            # Predict next drift
            try:
                last_drift_time = datetime.fromisoformat(sorted_drifts[-1]["timestamp"])
            except (ValueError, TypeError):
                continue

            next_drift_time = last_drift_time + timedelta(seconds=avg_interval)

            # If the predicted time is in the past but within the window,
            # project forward
            while next_drift_time < now:
                next_drift_time += timedelta(seconds=avg_interval)

            if next_drift_time > future_end:
                continue

            confidence = min(count / len(p_drifts), 1.0)

            predictions.append(DriftPrediction(
                path=path,
                predicted_time=next_drift_time,
                confidence=round(confidence, 2),
                reason=f"Recurring drift: same value {count}/{len(p_drifts)} times, avg interval {avg_interval / 86400:.1f} days",
                likely_hash=most_common_hash,
                pattern_type="recurrence",
            ))

        return predictions

    def format_predictions(self, days: int = 7) -> str:
        """Format drift predictions as a human-readable string.

        Args:
            days: Number of days to predict.

        Returns:
            Formatted string.
        """
        predictions = self.predict(days)

        lines = [
            f"Petrichor Scent — Drift Prediction (next {days} days)",
            "═" * 55,
        ]

        if not predictions:
            lines.append("")
            lines.append("No drift predicted this period.")
            return "\n".join(lines)

        for pred in predictions:
            lines.append("")
            time_str = pred.predicted_time.strftime("%A %H:%M")
            lines.append(f"{time_str} — {int(pred.confidence * 100)}% chance {pred.path} drifts")
            lines.append(f"  ({pred.reason})")

        lines.append("")
        return "\n".join(lines)
