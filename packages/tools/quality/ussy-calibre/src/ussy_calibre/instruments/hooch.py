"""Hooch Detector — Stale Test Identification.

Finds tests that are the fermentation equivalent of hooch: waste products
of a culture that hasn't been fed properly.

Detection criteria:
- Dead hooch: Tests that haven't failed in >180 days AND cover code that hasn't changed
- Stale hooch: Tests with trivial assertions (assert True, assert result is not None)
- Dormant hooch: Tests marked @skip or @xfail for >90 days without re-evaluation
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from ussy_calibre.models import (
    TestOutcomeLevain as TestOutcome,
    TestOutcomeLevain as TestOutcome,
    HoochReport,
    HoochResult,
    HoochType,

    TestResult,
)
from ussy_calibre.analyzer import analyze_assertion_quality, check_skip_staleness


class HoochDetector:
    """Detect stale, trivial, and dormant tests (hooch)."""

    def __init__(
        self,
        dead_threshold_days: int = 180,
        stale_assertion_threshold: float = 0.3,
        dormant_threshold_days: int = 90,
    ):
        self.dead_threshold_days = dead_threshold_days
        self.stale_assertion_threshold = stale_assertion_threshold
        self.dormant_threshold_days = dormant_threshold_days

    def detect(
        self,
        test_results: list[TestResult],
        source_map: Optional[dict[str, str]] = None,
        now: Optional[datetime] = None,
    ) -> HoochReport:
        """Run hooch detection on a set of test results.

        Args:
            test_results: List of test results from parser.
            source_map: Optional mapping of test filepath -> source code.
            now: Current datetime (for testing; defaults to utcnow).

        Returns:
            HoochReport with hooch indices and individual results.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        hooch_tests: list[HoochResult] = []
        module_tests: dict[str, list[TestResult]] = {}

        # Group by module
        for tr in test_results:
            module_tests.setdefault(tr.module, []).append(tr)

        for tr in test_results:
            hooch = self._check_hooch(tr, source_map, now)
            if hooch is not None:
                hooch_tests.append(hooch)

        # Calculate hooch index per module
        module_hooch_index = {}
        for module, tests in module_tests.items():
            module_hooch_count = sum(
                1 for h in hooch_tests if h.module == module
            )
            if tests:
                module_hooch_index[module] = (module_hooch_count / len(tests)) * 100
            else:
                module_hooch_index[module] = 0.0

        total_tests = len(test_results)
        overall_hooch_index = (
            (len(hooch_tests) / total_tests * 100) if total_tests > 0 else 0.0
        )

        return HoochReport(
            module_hooch_index=module_hooch_index,
            total_tests=total_tests,
            hooch_tests=hooch_tests,
            overall_hooch_index=overall_hooch_index,
        )

    def _check_hooch(
        self,
        tr: TestResult,
        source_map: Optional[dict[str, str]],
        now: datetime,
    ) -> Optional[HoochResult]:
        """Check if a single test is hooch. Returns HoochResult or None."""

        # Check dormant hooch (skipped/xfail tests)
        if tr.outcome in (TestOutcome.SKIPPED, TestOutcome.XFAIL):
            # Estimate how long it's been dormant from skip duration
            skip_duration = None
            if source_map and tr.filepath in source_map:
                skip_info = check_skip_staleness(source_map[tr.filepath])
                if skip_info["has_skip"] or skip_info["has_xfail"]:
                    # We can't determine exact skip date from AST alone,
                    # so we estimate based on test age heuristic
                    skip_duration = self.dormant_threshold_days  # Assume at threshold

            # Mark as dormant if skipped
            confidence = 0.7 if skip_duration is not None else 0.5
            return HoochResult(
                test_id=tr.test_id,
                name=tr.name,
                module=tr.module,
                hooch_type=HoochType.DORMANT,
                confidence=confidence,
                reason=f"Test is {tr.outcome.value} — dormant like a forgotten starter in the fridge",
                skip_duration_days=skip_duration,
            )

        # Check dead hooch (tests that never fail)
        # Use message heuristic: if test has passed and has no failure history
        days_since_failure = self._estimate_days_since_failure(tr, now)
        if days_since_failure is not None and days_since_failure > self.dead_threshold_days:
            confidence = min(1.0, days_since_failure / (self.dead_threshold_days * 2))
            return HoochResult(
                test_id=tr.test_id,
                name=tr.name,
                module=tr.module,
                hooch_type=HoochType.DEAD,
                confidence=confidence,
                reason=f"Test hasn't failed in {days_since_failure} days — tautological, testing nothing real",
                last_failed_days_ago=days_since_failure,
            )

        # Check stale hooch (trivial assertions)
        if source_map and tr.filepath in source_map:
            quality = analyze_assertion_quality(source_map[tr.filepath])
            if quality["score"] < self.stale_assertion_threshold:
                return HoochResult(
                    test_id=tr.test_id,
                    name=tr.name,
                    module=tr.module,
                    hooch_type=HoochType.STALE,
                    confidence=1.0 - quality["score"],
                    reason=f"Trivial assertions (quality={quality['score']:.2f}): "
                           + "; ".join(quality["issues"][:3]),
                    assertion_quality=quality["score"],
                )

        return None

    def _estimate_days_since_failure(
        self, tr: TestResult, now: datetime
    ) -> Optional[int]:
        """Estimate days since last failure for a test.

        In a real implementation this would query historical data.
        For now, use a heuristic: if the test has only ever passed,
        we estimate based on test metadata.
        """
        # Simple heuristic: if outcome is PASSED and no failure message,
        # estimate a long time. This is a conservative approach.
        if tr.outcome == TestOutcome.PASSED and not tr.message:
            # Without historical data, we can't determine exactly.
            # Return None to indicate we don't have enough data.
            return None
        return None


class HoochDetectorWithHistory(HoochDetector):
    """Hooch detector with access to historical test run data."""

    def __init__(self, history: Optional[list[list[TestResult]]] = None, **kwargs):
        super().__init__(**kwargs)
        self.history = history or []

    def _estimate_days_since_failure(
        self, tr: TestResult, now: datetime
    ) -> Optional[int]:
        """Use historical data to determine days since last failure."""
        last_failure: Optional[datetime] = None

        for run in self.history:
            for result in run:
                if result.test_id == tr.test_id and result.outcome in (
                    TestOutcome.FAILED,
                    TestOutcome.ERROR,
                ):
                    if last_failure is None or result.timestamp > last_failure:
                        last_failure = result.timestamp

        if last_failure is None:
            # Never failed — assume it's been at least dead_threshold_days
            return self.dead_threshold_days + 1

        delta = now - last_failure
        return delta.days
