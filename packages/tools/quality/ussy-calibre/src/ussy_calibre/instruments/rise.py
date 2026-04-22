"""Rise Meter — Fermentation Activity Analysis.

Measures whether your test suite is *alive* — actively catching bugs —
or *dead* — passing everything without meaningful verification.

A healthy sourdough starter doubles in size. A healthy test suite catches bugs.
Key insight: 0% failure rate is NOT healthy — it means the tests aren't discriminating.
"""

from __future__ import annotations

import math
from typing import Optional

from ussy_calibre.models import (
    TestOutcomeLevain as TestOutcome,
    RiseClassification,
    RiseResult,

    TestResult,
)


class RiseMeter:
    """Analyze fermentation activity (test failure patterns)."""

    def __init__(
        self,
        window_days: int = 90,
        healthy_min_rate: float = 0.01,
        healthy_max_rate: float = 0.08,
        chaotic_threshold: float = 0.15,
    ):
        self.window_days = window_days
        self.healthy_min_rate = healthy_min_rate
        self.healthy_max_rate = healthy_max_rate
        self.chaotic_threshold = chaotic_threshold

    def measure(self, test_results: list[TestResult]) -> RiseResult:
        """Measure the rise (fermentation activity) of a test suite.

        Args:
            test_results: List of test results.

        Returns:
            RiseResult with score, classification, and pattern analysis.
        """
        if not test_results:
            return RiseResult(
                rise_score=0.0,
                classification=RiseClassification.FLAT,
                failure_rate=0.0,
                pattern_description="No test results provided",
            )

        total = len(test_results)
        failed = sum(
            1 for tr in test_results
            if tr.outcome in (TestOutcome.FAILED, TestOutcome.ERROR)
        )
        failure_rate = failed / total if total > 0 else 0.0

        # Calculate rise score (0-100)
        rise_score = self._calculate_rise_score(failure_rate, test_results)

        # Classify the pattern
        classification = self._classify(failure_rate, test_results)

        # Analyze failure positions (for peak timing)
        failure_positions = self._failure_positions(test_results)

        # Peak timing
        peak_timing = self._peak_timing(failure_positions)

        # Pattern description
        pattern_description = self._describe_pattern(classification, failure_rate, failure_positions)

        return RiseResult(
            rise_score=rise_score,
            classification=classification,
            failure_rate=failure_rate,
            pattern_description=pattern_description,
            peak_timing=peak_timing,
            failure_positions=failure_positions,
        )

    def _calculate_rise_score(
        self, failure_rate: float, test_results: list[TestResult]
    ) -> float:
        """Calculate the rise score based on failure rate.

        The sweet spot is 1-8% failure rate. 0% is suspicious (flat/dead).
        >15% is chaotic (overflowing).
        """
        if failure_rate == 0.0:
            # 0% failure = suspiciously flat
            return 10.0

        if failure_rate < self.healthy_min_rate:
            # Very low but not zero — weak fermentation
            return 20.0 + (failure_rate / self.healthy_min_rate) * 20.0

        if failure_rate <= self.healthy_max_rate:
            # Sweet spot — healthy fermentation
            # Peak at center of healthy range
            center = (self.healthy_min_rate + self.healthy_max_rate) / 2
            half_width = (self.healthy_max_rate - self.healthy_min_rate) / 2
            distance = abs(failure_rate - center) / half_width if half_width > 0 else 0
            return 80.0 + (1.0 - distance) * 20.0

        if failure_rate <= self.chaotic_threshold:
            # Between healthy and chaotic — declining
            overage = (failure_rate - self.healthy_max_rate) / (
                self.chaotic_threshold - self.healthy_max_rate
            )
            return 80.0 - overage * 40.0

        # Chaotic — overflowing
        return max(10.0, 40.0 - (failure_rate - self.chaotic_threshold) * 100)

    def _classify(
        self, failure_rate: float, test_results: list[TestResult]
    ) -> RiseClassification:
        """Classify the rise pattern."""
        if failure_rate == 0.0:
            return RiseClassification.FLAT

        if failure_rate > self.chaotic_threshold:
            return RiseClassification.CHAOTIC

        # Check for clustering (seasonal) vs scattered (healthy)
        failure_positions = self._failure_positions(test_results)

        if failure_positions and len(failure_positions) >= 3:
            # Check if failures are clustered
            if self._is_clustered(failure_positions):
                if failure_rate <= self.healthy_max_rate:
                    return RiseClassification.SEASONAL
                return RiseClassification.CHAOTIC

        if self.healthy_min_rate <= failure_rate <= self.healthy_max_rate:
            return RiseClassification.HEALTHY

        if failure_rate < self.healthy_min_rate:
            return RiseClassification.FLAT

        return RiseClassification.SEASONAL

    def _failure_positions(self, test_results: list[TestResult]) -> list[float]:
        """Get normalized positions of failures in the test run order."""
        total = len(test_results)
        if total == 0:
            return []

        positions = []
        for i, tr in enumerate(test_results):
            if tr.outcome in (TestOutcome.FAILED, TestOutcome.ERROR):
                positions.append(i / total)
        return positions

    def _is_clustered(self, positions: list[float]) -> bool:
        """Check if failure positions are clustered vs scattered.

        Uses a simple coefficient of variation test.
        """
        if len(positions) < 2:
            return False

        mean = sum(positions) / len(positions)
        if mean == 0:
            return True

        variance = sum((p - mean) ** 2 for p in positions) / len(positions)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean  # coefficient of variation

        # Low CV = clustered, high CV = scattered
        return cv < 0.5

    def _peak_timing(self, failure_positions: list[float]) -> Optional[str]:
        """Analyze when failures occur in the test run."""
        if not failure_positions:
            return None

        mean_pos = sum(failure_positions) / len(failure_positions)

        if mean_pos < 0.3:
            return "early"
        elif mean_pos < 0.7:
            return "mid-cycle"
        else:
            return "late"

    def _describe_pattern(
        self,
        classification: RiseClassification,
        failure_rate: float,
        failure_positions: list[float],
    ) -> str:
        """Generate a human-readable pattern description."""
        rate_pct = failure_rate * 100

        if classification == RiseClassification.FLAT:
            return (
                f"Flat rise ({rate_pct:.1f}% failure rate) — your starter isn't rising. "
                "Tests pass but may not be discriminating. Consider mutation testing to verify."
            )
        elif classification == RiseClassification.HEALTHY:
            return (
                f"Healthy rise ({rate_pct:.1f}% failure rate) — tests are alive and discriminating. "
                "Failures are scattered, indicating genuine bug-catching."
            )
        elif classification == RiseClassification.CHAOTIC:
            return (
                f"Chaotic rise ({rate_pct:.1f}% failure rate) — starter overflowing. "
                "Too many failures suggest systemic issues or widespread contamination."
            )
        elif classification == RiseClassification.SEASONAL:
            return (
                f"Seasonal rise ({rate_pct:.1f}% failure rate) — failures are clustered, "
                "suggesting periodic contamination or environmental sensitivity."
            )
        return f"Unknown pattern ({rate_pct:.1f}% failure rate)"
