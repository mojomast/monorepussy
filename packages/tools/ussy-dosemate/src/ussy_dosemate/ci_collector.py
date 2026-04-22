"""CI/CD metrics collector — gathers pipeline throughput data.

For repos without CI/CD integration, provides sensible defaults
based on commit/merge patterns.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from ussy_dosemate.git_parser import GitHistoryParser, CommitInfo


@dataclass
class CIMetrics:
    """CI/CD throughput metrics."""
    pr_arrival_rate: float  # PRs per day
    max_ci_capacity: float  # Vmax: max PRs/day
    half_saturation_size: float  # Km: lines of change at half-saturation
    ci_thoroughness: float  # CL_int: higher = stricter CI
    avg_pr_size_lines: float
    avg_review_time_hours: float
    merge_rate: float  # fraction of PRs that get merged
    lint_pass_rate: float
    review_survival_rate: float


class CICollector:
    """Collect and compute CI/CD metrics from git history."""

    # Sensible defaults for unknown CI systems
    DEFAULT_VMAX = 15.0  # PRs per day
    DEFAULT_KM = 800.0  # lines at half-saturation
    DEFAULT_CL_INT = 5.0  # thoroughness coefficient

    def __init__(self, git_parser: GitHistoryParser):
        self.git_parser = git_parser

    def collect(self, since: Optional[str] = None) -> CIMetrics:
        """Collect CI metrics from git history.

        When actual CI data isn't available, infers from commit patterns.
        """
        commits = self.git_parser.parse_commits(since=since)
        merge_commits = self.git_parser.get_merge_commits(since=since)

        if not commits:
            return CIMetrics(
                pr_arrival_rate=0,
                max_ci_capacity=self.DEFAULT_VMAX,
                half_saturation_size=self.DEFAULT_KM,
                ci_thoroughness=self.DEFAULT_CL_INT,
                avg_pr_size_lines=0,
                avg_review_time_hours=0,
                merge_rate=0,
                lint_pass_rate=0.85,
                review_survival_rate=0.78,
            )

        # Compute time span
        dates = [c.date for c in commits]
        span_days = max((max(dates) - min(dates)).total_seconds() / 86400, 1.0)

        # PR arrival rate
        pr_arrival_rate = len(merge_commits) / span_days

        # Average PR size
        total_lines = sum(c.insertions + c.deletions for c in merge_commits)
        avg_pr_size = total_lines / max(len(merge_commits), 1)

        # Vmax: estimate based on peak throughput
        # Group commits by day, find the busiest day
        daily_counts: Dict[str, int] = {}
        for c in merge_commits:
            day = c.date.strftime("%Y-%m-%d")
            daily_counts[day] = daily_counts.get(day, 0) + 1
        peak_throughput = max(daily_counts.values()) if daily_counts else 1
        vmax = max(peak_throughput * 1.5, self.DEFAULT_VMAX)

        # Km: scale with average PR size
        km = max(avg_pr_size * 2, self.DEFAULT_KM)

        # CI thoroughness: inverse of merge rate (more rejections = stricter)
        merge_rate = len(merge_commits) / max(len(commits), 1)
        ci_thoroughness = (1.0 - merge_rate) * 10  # scale up

        # Review time estimation (from commit patterns)
        review_time_hours = self._estimate_review_time(commits)

        return CIMetrics(
            pr_arrival_rate=pr_arrival_rate,
            max_ci_capacity=vmax,
            half_saturation_size=km,
            ci_thoroughness=ci_thoroughness,
            avg_pr_size_lines=avg_pr_size,
            avg_review_time_hours=review_time_hours,
            merge_rate=merge_rate,
            lint_pass_rate=0.85,
            review_survival_rate=0.78,
        )

    def _estimate_review_time(self, commits: List[CommitInfo]) -> float:
        """Estimate average review time from commit timestamps."""
        if len(commits) < 2:
            return 24.0  # default 1 day
        # Use median time between non-merge commits as proxy
        sorted_commits = sorted(commits, key=lambda c: c.date)
        intervals = []
        for i in range(1, len(sorted_commits)):
            delta = (sorted_commits[i].date - sorted_commits[i-1].date).total_seconds() / 3600
            if 0 < delta < 720:  # ignore gaps > 30 days
                intervals.append(delta)
        if not intervals:
            return 24.0
        intervals.sort()
        return intervals[len(intervals) // 2]
