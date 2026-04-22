"""Time-gap detector — ported from unconformity."""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import List, Optional

from git import Repo

from ..missing_git import business_gap_seconds, default_branch_name
from ..missing_models import Severity, UnconformityEvent, UnconformityType


# Default: 14 days of business time
_DEFAULT_GAP_THRESHOLD = 60 * 60 * 24 * 14


def _human_duration(seconds: float) -> str:
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    if days:
        return f"{days}d {hours}h"
    return f"{hours}h"


def detect_paraconformity(
    repo: Repo,
    gap_threshold_seconds: int = _DEFAULT_GAP_THRESHOLD,
    max_commits: int = 2000,
    zscore_threshold: float = 2.0,
) -> List[UnconformityEvent]:
    """Detect temporal gaps in commit history."""
    events: List[UnconformityEvent] = []
    branch = default_branch_name(repo)

    commits = (
        list(repo.iter_commits(branch, max_count=max_commits))
        if branch
        else list(repo.iter_commits(all=True, max_count=max_commits))
    )
    if len(commits) < 2:
        return events

    ordered = list(reversed(commits))  # oldest → newest
    deltas: List[tuple] = []
    for older, newer in zip(ordered[:-1], ordered[1:]):
        delta = business_gap_seconds(older.committed_datetime, newer.committed_datetime)
        deltas.append((older, newer, delta))

    values = [d for _, _, d in deltas]
    avg = mean(values)
    spread = pstdev(values) if len(values) > 1 else 0.0

    for older, newer, delta in deltas:
        absolute_flag = delta >= gap_threshold_seconds
        zscore_flag = spread > 0 and delta > avg + zscore_threshold * spread
        if not (absolute_flag or zscore_flag):
            continue

        gap_days = delta / 86400
        severity = Severity.MEDIUM if delta >= gap_threshold_seconds * 2 else Severity.LOW

        events.append(
            UnconformityEvent(
                type=UnconformityType.PARACONFORMITY,
                severity=severity,
                description=(
                    f"Temporal break of {_human_duration(delta)} between "
                    f"{older.hexsha[:8]} and {newer.hexsha[:8]}."
                ),
                affected_commits=[older.hexsha, newer.hexsha],
                detected_at=datetime.now(timezone.utc),
                forensic_details={
                    "gap_seconds": delta,
                    "gap_days": round(gap_days, 1),
                    "gap_human": _human_duration(delta),
                    "mean_gap_seconds": round(avg, 1),
                    "stddev_gap_seconds": round(spread, 1),
                    "previous_commit_date": str(older.committed_datetime),
                    "next_commit_date": str(newer.committed_datetime),
                    "previous_message": older.message.strip()[:100],
                    "next_message": newer.message.strip()[:100],
                },
                geological_metaphor=(
                    "The sediment appears continuous, but an unconformable surface "
                    "separates layers representing vastly different time periods."
                ),
            )
        )
    return events
