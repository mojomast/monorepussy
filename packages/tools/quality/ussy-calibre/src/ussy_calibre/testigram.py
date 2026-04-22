"""Testigram — Pure-Tone Audiometry for test suites.

Measures test detection threshold across code complexity bands,
producing an audiogram-shaped profile of the suite's "hearing."
"""

from __future__ import annotations

import math
from typing import Optional

from ussy_calibre.models import (
    COMPLEXITY_BANDS,
    ProjectScan,
    TestigramPoint,
    TestigramResult,
)
from ussy_calibre.utils import mean, severity_label


class TestigramAnalyzer:
    """Analyzes test detection thresholds per complexity band."""
    __test__ = False

    # Estimated detection threshold based on test-to-code ratio and coverage.
    # In a real system this would use mutation testing data; here we compute
    # a heuristic from structural information.

    def __init__(self, scan: ProjectScan) -> None:
        self.scan = scan

    def analyze(self) -> TestigramResult:
        """Compute the Testigram for the scanned project."""
        points: list[TestigramPoint] = []

        # Count source and test functions per complexity band
        band_source_counts: dict[str, int] = {label: 0 for label, _, _ in COMPLEXITY_BANDS}
        band_test_counts: dict[str, dict[str, int]] = {
            label: {"unit": 0, "integration": 0}
            for label, _, _ in COMPLEXITY_BANDS
        }
        band_total_complexity: dict[str, int] = {label: 0 for label, _, _ in COMPLEXITY_BANDS}

        # Accumulate source function data
        for mod in self.scan.source_modules:
            for func in mod.functions:
                band = func.complexity_band
                band_source_counts[band] += 1
                band_total_complexity[band] += func.cyclomatic_complexity

        # Accumulate test function data
        for mod in self.scan.test_modules:
            for func in mod.functions:
                if func.test_type:
                    band = func.complexity_band
                    # Tests exercise code across bands; we map tests to the
                    # band of their own complexity as a proxy
                    band_test_counts[band][func.test_type] += 1

        # Compute detection thresholds for each band and test type
        for label, lo, hi in COMPLEXITY_BANDS:
            for test_type in ("unit", "integration"):
                threshold = self._estimate_threshold(
                    band_source_counts[label],
                    band_test_counts[label][test_type],
                    label,
                )
                points.append(
                    TestigramPoint(
                        complexity_band=label,
                        test_type=test_type,
                        detection_threshold=threshold,
                    )
                )

        result = TestigramResult(points=points)
        result.shape = self._classify_shape(points)
        return result

    def _estimate_threshold(
        self,
        source_count: int,
        test_count: int,
        band_label: str,
    ) -> float:
        """Estimate detection threshold for a complexity band.

        Lower threshold = better detection (tests can detect smaller defects).
        If no source code in this band, threshold is 0 (nothing to detect).
        If source but no tests, threshold is very high (deaf).
        Otherwise, threshold decreases as test-to-source ratio increases.
        """
        if source_count == 0:
            return 0.0  # Nothing to detect

        if test_count == 0:
            # Completely deaf in this band
            # Higher complexity bands start with higher baseline
            band_idx = next(
                i for i, (l, _, _) in enumerate(COMPLEXITY_BANDS) if l == band_label
            )
            return 50.0 + band_idx * 5.0  # 50, 55, 60, 65, 70

        # Ratio-based heuristic: more tests per source function = lower threshold
        ratio = test_count / source_count
        # Threshold in dB: 0 = perfect, higher = worse
        # At ratio=1.0 we expect ~10 dB, at ratio=0.1 we expect ~30 dB
        if ratio >= 1.0:
            threshold = max(0.0, 10.0 - 5.0 * math.log2(ratio))
        else:
            threshold = 10.0 + 20.0 * (-math.log2(ratio + 0.001))

        # Complexity penalty: higher bands are harder to test
        band_idx = next(
            i for i, (l, _, _) in enumerate(COMPLEXITY_BANDS) if l == band_label
        )
        threshold += band_idx * 3.0

        return round(min(threshold, 70.0), 1)

    def _classify_shape(self, points: list[TestigramPoint]) -> str:
        """Classify the audiogram shape from unit-test thresholds."""
        unit_points = sorted(
            [p for p in points if p.test_type == "unit"],
            key=lambda p: COMPLEXITY_BANDS.index(
                next(b for b in COMPLEXITY_BANDS if b[0] == p.complexity_band)
            ),
        )
        if len(unit_points) < 3:
            return "flat"

        thresholds = [p.detection_threshold for p in unit_points]
        low_avg = mean(thresholds[:2])
        high_avg = mean(thresholds[-2:])

        # Check for notch: one band significantly higher than neighbors
        for i in range(1, len(thresholds) - 1):
            if thresholds[i] > thresholds[i - 1] + 10 and thresholds[i] > thresholds[i + 1] + 10:
                return "notched"

        # Sloping: high complexity much worse than low
        if high_avg - low_avg > 15:
            return "sloping"

        return "flat"


def run_testigram(project_path: str) -> TestigramResult:
    """Convenience entry point for Testigram analysis."""
    from ussy_calibre.scanner import scan_project

    scan = scan_project(project_path)
    analyzer = TestigramAnalyzer(scan)
    return analyzer.analyze()
