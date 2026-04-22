"""Levain Build — Essential Test Subset Selection.

Like a levain (preferment) in baking — a small, active portion of the starter
that you build up for a specific bake. Levain identifies the minimal set of
high-value tests for quick validation.
"""

from __future__ import annotations

from typing import Optional

from ussy_calibre.models import (
    TestOutcomeLevain as TestOutcome,
    BuildResult,

    TestResult,
)


class LevainBuild:
    """Build a preferment (essential test subset) for quick validation."""

    def __init__(
        self,
        time_limit_minutes: float = 5.0,
        confidence_target: float = 0.95,
        discriminative_weight: float = 0.4,
        coverage_weight: float = 0.3,
        recency_weight: float = 0.3,
    ):
        self.time_limit_minutes = time_limit_minutes
        self.confidence_target = confidence_target
        self.discriminative_weight = discriminative_weight
        self.coverage_weight = coverage_weight
        self.recency_weight = recency_weight

    def build(
        self,
        test_results: list[TestResult],
        test_history: Optional[list[list[TestResult]]] = None,
        change_scope: Optional[str] = None,
    ) -> BuildResult:
        """Build a preferment (test subset) for quick validation.

        Args:
            test_results: Current test results.
            test_history: Historical test runs for scoring.
            change_scope: Optional module/path to focus on.

        Returns:
            BuildResult with selected tests and confidence estimate.
        """
        if not test_results:
            return BuildResult(
                selected_tests=[],
                estimated_confidence=0.0,
                proofing_time_seconds=0.0,
                change_scope=change_scope,
            )

        # Score each test for preferment selection
        scored_tests = self._score_tests(test_results, test_history, change_scope)

        # Select tests within time budget
        time_budget_seconds = self.time_limit_minutes * 60
        selected = []
        total_time = 0.0

        # Sort by score descending
        scored_tests.sort(key=lambda x: x[1], reverse=True)

        for test_id, score, duration in scored_tests:
            if total_time + duration <= time_budget_seconds:
                selected.append(test_id)
                total_time += duration

            # Stop if we have enough tests for target confidence
            if len(selected) > 0:
                current_confidence = self._estimate_confidence(
                    selected, scored_tests, len(test_results)
                )
                if current_confidence >= self.confidence_target:
                    break

        # Calculate final confidence
        confidence = self._estimate_confidence(
            selected, scored_tests, len(test_results)
        )

        return BuildResult(
            selected_tests=selected,
            estimated_confidence=confidence,
            proofing_time_seconds=total_time,
            change_scope=change_scope,
        )

    def _score_tests(
        self,
        test_results: list[TestResult],
        test_history: Optional[list[list[TestResult]]],
        change_scope: Optional[str],
    ) -> list[tuple[str, float, float]]:
        """Score each test for preferment selection.

        Returns list of (test_id, score, duration) tuples.
        """
        scored = []

        # Pre-compute discriminative power from history
        discriminative_power: dict[str, float] = {}
        if test_history:
            discriminative_power = self._compute_discriminative_power(test_history)

        for tr in test_results:
            score = 0.0

            # Discriminative power component
            dp = discriminative_power.get(tr.test_id, 0.5)
            score += self.discriminative_weight * dp

            # Coverage component: tests for changed scope get higher score
            if change_scope and change_scope in tr.module:
                score += self.coverage_weight * 1.0
            else:
                score += self.coverage_weight * 0.3

            # Recency component: recently failing tests are more valuable
            if tr.outcome in (TestOutcome.FAILED, TestOutcome.ERROR):
                score += self.recency_weight * 1.0
            elif tr.outcome == TestOutcome.PASSED:
                score += self.recency_weight * 0.5
            else:
                score += self.recency_weight * 0.2

            scored.append((tr.test_id, score, tr.duration))

        return scored

    def _compute_discriminative_power(
        self, test_history: list[list[TestResult]]
    ) -> dict[str, float]:
        """Compute how discriminating each test is based on history.

        A discriminating test is one that fails when there are bugs
        and passes when there aren't.
        """
        from collections import defaultdict

        test_outcomes: dict[str, list[TestOutcome]] = defaultdict(list)
        for run in test_history:
            for tr in run:
                test_outcomes[tr.test_id].append(tr.outcome)

        power = {}
        for test_id, outcomes in test_outcomes.items():
            if not outcomes:
                power[test_id] = 0.5
                continue

            # Discriminative power = ratio of unique outcomes / possible outcomes
            # A test that always passes or always fails has low power
            # A test that sometimes passes and sometimes fails has high power
            failed_count = sum(1 for o in outcomes if o in (TestOutcome.FAILED, TestOutcome.ERROR))
            passed_count = sum(1 for o in outcomes if o == TestOutcome.PASSED)
            total = len(outcomes)

            if total == 0:
                power[test_id] = 0.5
                continue

            # Bell curve: maximum power at 50% failure rate
            fail_rate = failed_count / total
            power[test_id] = 1.0 - abs(fail_rate - 0.5) * 2  # 0 at 0% or 100%, 1 at 50%

        return power

    def _estimate_confidence(
        self,
        selected: list[str],
        scored_tests: list[tuple[str, float, float]],
        total_tests: int,
    ) -> float:
        """Estimate confidence that the preferment will catch real failures.

        Based on coverage of test space and discriminative power.
        """
        if not selected or total_tests == 0:
            return 0.0

        # Coverage ratio
        coverage_ratio = len(selected) / total_tests

        # Average discriminative score of selected tests
        selected_scores = [
            score for test_id, score, _ in scored_tests if test_id in selected
        ]
        avg_score = sum(selected_scores) / len(selected_scores) if selected_scores else 0.0

        # Confidence is a combination of coverage and quality
        confidence = coverage_ratio * 0.5 + avg_score * 0.5

        # Scale: even with 100% coverage, max confidence is ~0.98
        return min(0.98, max(0.0, confidence))
