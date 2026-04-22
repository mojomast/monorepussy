"""Companogram — Tympanometry for test suites.

Measures test pass rate as configuration parameters sweep, classifying
the result as Type As (over-rigid), Ad (over-compliant), B (broken),
or C (config drift).
"""

from __future__ import annotations

import math
from typing import Optional

from ussy_calibre.models import (
    CompanogramPoint,
    CompanogramResult,
    ProjectScan,
)
from ussy_calibre.utils import mean, stdev


# Default config sweep values (normalized)
DEFAULT_CONFIG_SWEEP = [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]


class CompanogramAnalyzer:
    """Analyzes test environment compliance via config perturbation."""

    def __init__(self, scan: ProjectScan) -> None:
        self.scan = scan

    def analyze(
        self,
        config_pass_rates: Optional[dict[float, float]] = None,
    ) -> CompanogramResult:
        """Compute the Companogram.

        Args:
            config_pass_rates: Optional mapping of config_value -> pass_rate.
                If None, heuristic values are computed.
        """
        if config_pass_rates is not None:
            points = [
                CompanogramPoint(
                    config_value=cv,
                    pass_rate=config_pass_rates.get(cv, 0.0),
                )
                for cv in sorted(config_pass_rates.keys())
            ]
        else:
            points = self._estimate_curve()

        if not points:
            return CompanogramResult(peak_type="B")

        # Find peak
        peak_point = max(points, key=lambda p: p.pass_rate)
        peak_location = peak_point.config_value
        peak_pass_rate = peak_point.pass_rate

        # Compute tolerance width
        tolerance_width = self._tolerance_width(points, peak_pass_rate)

        # Compute rigidity score
        rigidity_score = 1.0 / tolerance_width if tolerance_width > 0 else float("inf")

        # Classify peak type
        peak_type = self._classify_peak(points, peak_location, peak_pass_rate, tolerance_width)

        return CompanogramResult(
            points=points,
            peak_type=peak_type,
            tolerance_width=round(tolerance_width, 3),
            rigidity_score=round(rigidity_score, 3),
            peak_location=peak_location,
            peak_pass_rate=peak_pass_rate,
        )

    def _estimate_curve(self) -> list[CompanogramPoint]:
        """Heuristic estimate of pass rate vs config value from scan data."""
        # More test functions → more sensitive to config changes
        test_count = sum(
            len(mod.functions) for mod in self.scan.test_modules
        )

        points = []
        for cv in DEFAULT_CONFIG_SWEEP:
            # Gaussian-like curve centered at 0
            # Narrower for more tests (more assertions = more sensitive)
            sigma = max(0.5, 2.0 - test_count * 0.05)
            pass_rate = math.exp(-(cv ** 2) / (2 * sigma ** 2))
            points.append(
                CompanogramPoint(config_value=cv, pass_rate=round(pass_rate, 3))
            )
        return points

    def _tolerance_width(
        self, points: list[CompanogramPoint], peak_pass_rate: float
    ) -> float:
        """Compute the tolerance width (full width at half maximum).

        TW = v_right - v_left where pass_rate >= 0.5 * max
        """
        half_max = 0.5 * peak_pass_rate
        sorted_pts = sorted(points, key=lambda p: p.config_value)

        v_left = sorted_pts[0].config_value
        v_right = sorted_pts[-1].config_value

        for p in sorted_pts:
            if p.pass_rate >= half_max:
                v_left = p.config_value
                break

        for p in reversed(sorted_pts):
            if p.pass_rate >= half_max:
                v_right = p.config_value
                break

        return v_right - v_left

    def _classify_peak(
        self,
        points: list[CompanogramPoint],
        peak_location: float,
        peak_pass_rate: float,
        tolerance_width: float,
    ) -> str:
        """Classify the companogram peak type.

        Type As: Narrow peak → over-rigid (brittle)
        Type Ad: Wide peak → over-compliant (no real assertions)
        Type B:  No peak → broken (always fails)
        Type C:  Peak off-center → config drift
        """
        if peak_pass_rate < 0.1:
            return "B"  # Effectively flat at zero

        # Check for off-center peak (config drift)
        if abs(peak_location) > 0.5:
            return "C"

        # Check tolerance width
        if tolerance_width < 1.0:
            return "As"  # Narrow = over-rigid
        elif tolerance_width > 3.5:
            return "Ad"  # Wide = over-compliant

        return "As"  # Default to narrow if ambiguous


def run_companogram(
    project_path: str,
    config_pass_rates: Optional[dict[float, float]] = None,
) -> CompanogramResult:
    """Convenience entry point for Companogram analysis."""
    from ussy_calibre.scanner import scan_project

    scan = scan_project(project_path)
    analyzer = CompanogramAnalyzer(scan)
    return analyzer.analyze(config_pass_rates=config_pass_rates)
