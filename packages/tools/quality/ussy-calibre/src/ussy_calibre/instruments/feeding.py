"""Feeding Schedule — Test Maintenance Cadence.

Ensures your test culture is fed regularly, not just when someone remembers.
Tracks feeding gaps, code-to-test change ratios, and recommends schedules.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional

from ussy_calibre.models import (
    FeedingReport,
    FeedingResult,
    TestResult,
)


class FeedingSchedule:
    """Analyze and recommend test feeding schedules."""

    def __init__(
        self,
        unfed_threshold_days: int = 30,
        starving_threshold_days: int = 60,
        base_interval_days: int = 14,
    ):
        self.unfed_threshold_days = unfed_threshold_days
        self.starving_threshold_days = starving_threshold_days
        self.base_interval_days = base_interval_days

    def audit(
        self,
        test_results: list[TestResult],
        module_change_data: Optional[dict[str, dict]] = None,
        now: Optional[datetime] = None,
    ) -> FeedingReport:
        """Audit feeding schedule adherence.

        Args:
            test_results: Current test results.
            module_change_data: Dict of module -> {
                'last_test_change_days_ago': float,
                'code_changes_since_test': int,
                'total_code_commits': int,
            }
            now: Current datetime for testing.

        Returns:
            FeedingReport with per-module adherence and recommendations.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # Group tests by module
        module_tests: dict[str, list[TestResult]] = defaultdict(list)
        for tr in test_results:
            module_tests[tr.module].append(tr)

        modules = []
        starving = []
        warnings = []

        for module, tests in module_tests.items():
            # Get change data for this module
            change_data = (module_change_data or {}).get(module, {})

            last_fed_days = change_data.get("last_test_change_days_ago", 0.0)
            code_changes = change_data.get("code_changes_since_test", 0)
            total_commits = change_data.get("total_code_commits", 0)

            # Calculate feeding adherence
            adherence = self._calculate_adherence(
                last_fed_days, code_changes, total_commits
            )

            # Determine status
            status = self._determine_status(last_fed_days, code_changes)

            # Recommend interval
            recommended = self._recommend_interval(last_fed_days, code_changes, total_commits)

            result = FeedingResult(
                module=module,
                last_fed_days_ago=last_fed_days,
                code_changes_since_feed=code_changes,
                feeding_adherence=adherence,
                status=status,
                recommended_interval_days=recommended,
            )
            modules.append(result)

            if status == "starving":
                starving.append(module)
                warnings.append(
                    f"Module '{module}' is starving — {code_changes} code changes "
                    f"without test updates in {last_fed_days:.0f} days"
                )
            elif status == "hungry":
                warnings.append(
                    f"Module '{module}' is hungry — last fed {last_fed_days:.0f} days ago"
                )

        # Overall adherence
        overall_adherence = (
            sum(m.feeding_adherence for m in modules) / len(modules)
            if modules
            else 0.0
        )

        return FeedingReport(
            modules=modules,
            overall_adherence=overall_adherence,
            starving_modules=starving,
            warnings=warnings,
        )

    def _calculate_adherence(
        self,
        last_fed_days: float,
        code_changes: int,
        total_commits: int,
    ) -> float:
        """Calculate feeding adherence score (0-1).

        High adherence = fed recently relative to code change rate.
        """
        # Time-based component: how recently was it fed?
        if last_fed_days <= 0:
            time_score = 1.0
        elif last_fed_days <= self.unfed_threshold_days:
            time_score = 1.0 - (last_fed_days / self.unfed_threshold_days) * 0.5
        elif last_fed_days <= self.starving_threshold_days:
            time_score = 0.5 - (
                (last_fed_days - self.unfed_threshold_days)
                / (self.starving_threshold_days - self.unfed_threshold_days)
            ) * 0.3
        else:
            time_score = max(0.0, 0.2 - (last_fed_days - self.starving_threshold_days) * 0.005)

        # Code-change-based component: are tests keeping up with code?
        if code_changes <= 0:
            change_score = 1.0
        elif code_changes <= 5:
            change_score = 0.8
        elif code_changes <= 20:
            change_score = 0.5
        elif code_changes <= 50:
            change_score = 0.2
        else:
            change_score = 0.1

        # Weighted combination
        return time_score * 0.6 + change_score * 0.4

    def _determine_status(self, last_fed_days: float, code_changes: int) -> str:
        """Determine feeding status: healthy, hungry, or starving."""
        if last_fed_days <= self.unfed_threshold_days and code_changes <= 5:
            return "healthy"
        if last_fed_days > self.starving_threshold_days or code_changes > 20:
            return "starving"
        return "hungry"

    def _recommend_interval(
        self,
        last_fed_days: float,
        code_changes: int,
        total_commits: int,
    ) -> float:
        """Recommend feeding interval in days.

        Higher code change velocity = more frequent feeding needed.
        """
        # Base interval
        interval = float(self.base_interval_days)

        # Adjust for code change rate
        if total_commits > 0:
            # If there are many commits, tests need more frequent feeding
            commits_per_week = total_commits / max(1, last_fed_days / 7)
            if commits_per_week > 5:
                interval *= 0.5
            elif commits_per_week > 2:
                interval *= 0.75

        # Adjust for unfed gap
        if code_changes > 20:
            interval *= 0.5  # Need more frequent feeding

        return max(7.0, interval)  # Minimum weekly
