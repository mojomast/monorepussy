"""Absorption model — merge rate and change absorption kinetics."""

import math
from dataclasses import dataclass
from typing import Optional

from dosemate.git_parser import PullRequestInfo


@dataclass
class AbsorptionParams:
    """Absorption parameters for a change/PR."""
    ka: float  # Absorption rate constant (day^-1)
    lag_time_hours: float  # Time before absorption begins
    fraction_absorbed: float  # Fraction of original change surviving review (0-1)
    dose_lines: int  # Total lines in the original change
    median_time_to_merge_days: float  # Median time to merge

    def cumulative_absorption(self, t_days: float) -> float:
        """Compute cumulative lines absorbed at time t.

        A_absorbed(t) = f * dose * (1 - e^(-ka * (t - t_lag)))
        Returns 0 if t < lag_time.
        """
        t_lag_days = self.lag_time_hours / 24.0
        if t_days < t_lag_days:
            return 0.0
        return self.fraction_absorbed * self.dose_lines * (1 - math.exp(-self.ka * (t_days - t_lag_days)))


def compute_absorption(prs: list, category: Optional[str] = None) -> AbsorptionParams:
    """Compute absorption parameters from a list of PRs.

    Args:
        prs: List of PullRequestInfo objects
        category: Optional category for filtering (not implemented yet)

    Returns:
        AbsorptionParams with computed values
    """
    if not prs:
        return AbsorptionParams(
            ka=0.0, lag_time_hours=0.0, fraction_absorbed=0.0,
            dose_lines=0, median_time_to_merge_days=0.0,
        )

    # Compute time-to-merge for each PR
    merge_times = []
    total_original_lines = 0
    total_merged_lines = 0

    for pr in prs:
        if pr.merged_at and pr.created_at:
            delta_days = (pr.merged_at - pr.created_at).total_seconds() / 86400
            merge_times.append(max(delta_days, 0.01))

        total_original_lines += pr.insertions + pr.deletions
        # Simulate review reduction: merged lines are typically 70-95% of original
        total_merged_lines += pr.insertions  # simplified

    # Median time to merge
    merge_times.sort()
    n = len(merge_times)
    if n % 2 == 0:
        median_ttm = (merge_times[n // 2 - 1] + merge_times[n // 2]) / 2
    else:
        median_ttm = merge_times[n // 2]

    # ka = ln(2) / median_time_to_merge
    ka = math.log(2) / max(median_ttm, 0.01)

    # Lag time: time from PR creation to first CI/review
    lag_times = []
    for pr in prs:
        if pr.first_ci_at and pr.created_at:
            lag_hours = (pr.first_ci_at - pr.created_at).total_seconds() / 3600
            lag_times.append(max(lag_hours, 0))
    lag_time_hours = sum(lag_times) / len(lag_times) if lag_times else 4.0

    # Fraction absorbed: lines surviving review
    if total_original_lines > 0:
        fraction_absorbed = min(total_merged_lines / total_original_lines, 1.0)
    else:
        fraction_absorbed = 0.78  # default

    # Ensure fraction_absorbed is in [0, 1]
    fraction_absorbed = max(0.0, min(1.0, fraction_absorbed))

    return AbsorptionParams(
        ka=ka,
        lag_time_hours=lag_time_hours,
        fraction_absorbed=fraction_absorbed,
        dose_lines=total_original_lines,
        median_time_to_merge_days=median_ttm,
    )
