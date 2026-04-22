"""Tests for the absorption module."""

import math
from datetime import datetime, timedelta

import pytest

from ussy_dosemate.absorption import AbsorptionParams, compute_absorption
from ussy_dosemate.git_parser import PullRequestInfo


class TestAbsorptionParams:
    """Tests for AbsorptionParams dataclass and its methods."""

    def test_cumulative_absorption_at_lag_time(self):
        """At lag_time, absorption should be 0."""
        params = AbsorptionParams(
            ka=0.5, lag_time_hours=4.0, fraction_absorbed=0.8, dose_lines=100,
            median_time_to_merge_days=1.4,
        )
        # At exactly lag_time (4 hours = 4/24 days), absorption should be 0
        assert params.cumulative_absorption(4.0 / 24.0) == 0.0

    def test_cumulative_absorption_before_lag_time(self):
        """Before lag_time, absorption should be 0."""
        params = AbsorptionParams(
            ka=0.5, lag_time_hours=4.0, fraction_absorbed=0.8, dose_lines=100,
            median_time_to_merge_days=1.4,
        )
        assert params.cumulative_absorption(0.0) == 0.0
        assert params.cumulative_absorption(0.1) == 0.0

    def test_cumulative_absorption_approaches_max(self):
        """At very long times, absorption should approach f * dose."""
        params = AbsorptionParams(
            ka=1.0, lag_time_hours=0.0, fraction_absorbed=0.8, dose_lines=100,
            median_time_to_merge_days=0.7,
        )
        result = params.cumulative_absorption(50.0)  # very long time
        assert abs(result - 80.0) < 0.01  # f * dose = 0.8 * 100

    def test_cumulative_absorption_monotonically_increasing(self):
        """Absorption should be monotonically increasing after lag time."""
        params = AbsorptionParams(
            ka=0.5, lag_time_hours=1.0, fraction_absorbed=0.9, dose_lines=200,
            median_time_to_merge_days=1.4,
        )
        values = [params.cumulative_absorption(t / 24.0) for t in range(0, 200, 5)]
        for i in range(1, len(values)):
            assert values[i] >= values[i-1]

    def test_cumulative_absorption_zero_ka(self):
        """With ka=0, absorption should be 0 (never absorbed)."""
        params = AbsorptionParams(
            ka=0.0, lag_time_hours=0.0, fraction_absorbed=1.0, dose_lines=100,
            median_time_to_merge_days=0.0,
        )
        # e^0 = 1, so 1 - e^0 = 0
        assert params.cumulative_absorption(1.0) == 0.0


class TestComputeAbsorption:
    """Tests for compute_absorption function."""

    def test_empty_prs(self):
        """Empty PR list should return zero parameters."""
        result = compute_absorption([])
        assert result.ka == 0.0
        assert result.lag_time_hours == 0.0
        assert result.fraction_absorbed == 0.0
        assert result.dose_lines == 0

    def test_single_pr(self):
        """Single PR should compute valid absorption parameters."""
        now = datetime.now()
        pr = PullRequestInfo(
            id="pr_1",
            title="Test PR",
            created_at=now - timedelta(days=2),
            merged_at=now - timedelta(days=1),
            files_changed=["file.py"],
            insertions=100,
            deletions=10,
            first_ci_at=now - timedelta(days=2, hours=1),
        )
        result = compute_absorption([pr])
        assert result.ka > 0
        assert result.fraction_absorbed > 0
        assert result.fraction_absorbed <= 1.0
        assert result.dose_lines > 0

    def test_fast_merge_high_ka(self):
        """Quickly merged PRs should have higher ka than slowly merged ones."""
        now = datetime.now()

        fast_pr = PullRequestInfo(
            id="fast",
            title="Fast PR",
            created_at=now - timedelta(hours=2),
            merged_at=now - timedelta(hours=1),
            files_changed=["f.py"],
            insertions=10,
            deletions=0,
            first_ci_at=now - timedelta(hours=2, minutes=5),
        )

        slow_pr = PullRequestInfo(
            id="slow",
            title="Slow PR",
            created_at=now - timedelta(days=7),
            merged_at=now - timedelta(days=1),
            files_changed=["f.py"],
            insertions=10,
            deletions=0,
            first_ci_at=now - timedelta(days=7, hours=1),
        )

        fast_result = compute_absorption([fast_pr])
        slow_result = compute_absorption([slow_pr])
        assert fast_result.ka > slow_result.ka

    def test_fraction_absorbed_bounded(self):
        """Fraction absorbed should always be in [0, 1]."""
        now = datetime.now()
        prs = [
            PullRequestInfo(
                id=f"pr_{i}",
                title=f"PR {i}",
                created_at=now - timedelta(days=i+1),
                merged_at=now - timedelta(days=i),
                files_changed=["f.py"],
                insertions=50 * (i + 1),
                deletions=10 * i,
                first_ci_at=now - timedelta(days=i+1, hours=1),
            )
            for i in range(10)
        ]
        result = compute_absorption(prs)
        assert 0.0 <= result.fraction_absorbed <= 1.0

    def test_auto_merge_ka_formula(self):
        """Verify ka = ln(2) / median_time_to_merge."""
        now = datetime.now()
        # PR merged after exactly 3 days
        pr = PullRequestInfo(
            id="pr_exact",
            title="Exact PR",
            created_at=now - timedelta(days=3),
            merged_at=now,
            files_changed=["f.py"],
            insertions=50,
            deletions=5,
            first_ci_at=now - timedelta(days=3, hours=1),
        )
        result = compute_absorption([pr])
        expected_ka = math.log(2) / 3.0
        assert abs(result.ka - expected_ka) < 0.01
