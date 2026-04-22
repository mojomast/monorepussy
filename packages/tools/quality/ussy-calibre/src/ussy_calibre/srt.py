"""SRT — Speech Reception Test for test suites.

Measures the minimum environment fidelity at which integration tests pass,
detects roll-over (tests that fail MORE in realistic environments), and
cross-validates against Testigram PTA.
"""

from __future__ import annotations

import math
from typing import Optional

from ussy_calibre.models import (
    ProjectScan,
    SRTCandidate,
    SRTResult,
)
from ussy_calibre.utils import mean, stdev, linear_regression


# Default fidelity levels to evaluate
DEFAULT_FIDELITY_LEVELS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


class SRTAnalyzer:
    """Analyzes integration test effectiveness as a function of environment fidelity."""

    def __init__(self, scan: ProjectScan) -> None:
        self.scan = scan

    def analyze(
        self,
        fidelity_pass_rates: Optional[dict[float, float]] = None,
        pta_value: float = 0.0,
        delta: float = 10.0,
    ) -> SRTResult:
        """Compute the SRT for the project.

        Args:
            fidelity_pass_rates: Optional mapping of fidelity->pass_rate.
                If None, heuristic values are computed from scan data.
            pta_value: PTA from Testigram for agreement check.
            delta: Maximum acceptable |SRT - PTA| for consistency.
        """
        # Compute or use provided pass rates at each fidelity level
        if fidelity_pass_rates is not None:
            candidates = [
                SRTCandidate(
                    environment_fidelity=fid,
                    pass_rate=fidelity_pass_rates.get(fid, 0.0),
                )
                for fid in sorted(fidelity_pass_rates.keys())
            ]
        else:
            candidates = self._estimate_pass_rates()

        # Find SRT: minimum fidelity where pass_rate >= 0.5
        srt_value = self._find_srt(candidates)

        # Detect roll-over
        has_rollover, rollover_point = self._detect_rollover(candidates)

        # Word Recognition Scores (pass rates at each fidelity)
        wrs = [c.pass_rate for c in candidates]

        # SRT-PTA agreement
        agreement_delta = abs(srt_value * 10 - pta_value)  # scale SRT to dB-like
        is_consistent = agreement_delta <= delta

        return SRTResult(
            srt_value=srt_value,
            candidates=candidates,
            has_rollover=has_rollover,
            rollover_point=rollover_point,
            word_recognition_scores=wrs,
            pta_value=pta_value,
            agreement_delta=round(agreement_delta, 1),
            is_consistent=is_consistent,
        )

    def _estimate_pass_rates(self) -> list[SRTCandidate]:
        """Heuristic: estimate pass rates from scan data.

        Integration tests with more mocking artifacts → lower fidelity needed.
        More integration tests → higher pass rates at higher fidelity.
        """
        integration_count = sum(
            1
            for mod in self.scan.test_modules
            for func in mod.functions
            if func.test_type == "integration"
        )
        total_test_count = sum(
            1 for mod in self.scan.test_modules for func in mod.functions
        )

        ratio = integration_count / max(total_test_count, 1)

        candidates = []
        for fid in DEFAULT_FIDELITY_LEVELS:
            # Heuristic: pass rate increases with fidelity, but base rate
            # depends on integration test ratio
            base_rate = 0.3 + 0.5 * ratio
            pass_rate = min(1.0, base_rate * (0.5 + 0.5 * fid))
            candidates.append(
                SRTCandidate(
                    environment_fidelity=fid,
                    pass_rate=round(pass_rate, 3),
                )
            )
        return candidates

    def _find_srt(self, candidates: list[SRTCandidate]) -> float:
        """Find minimum fidelity where pass rate >= 0.50."""
        for c in sorted(candidates, key=lambda x: x.environment_fidelity):
            if c.pass_rate >= 0.50:
                return c.environment_fidelity
        # If never reaches 50%, return max fidelity + 1
        if candidates:
            return max(c.environment_fidelity for c in candidates) + 1.0
        return 1.0

    def _detect_rollover(
        self, candidates: list[SRTCandidate]
    ) -> tuple[bool, Optional[float]]:
        """Detect roll-over: WRS decreases with increasing environment fidelity.

        This indicates tests that only pass in simplified environments.
        We look for the second derivative being negative past the peak
        (WRS decreasing after a maximum).
        """
        if len(candidates) < 3:
            return (False, None)

        sorted_cands = sorted(candidates, key=lambda c: c.environment_fidelity)
        rates = [c.pass_rate for c in sorted_cands]

        # Find first peak
        peak_idx = 0
        peak_val = rates[0]
        for i, r in enumerate(rates):
            if r > peak_val:
                peak_val = r
                peak_idx = i

        # Check if rate decreases significantly after peak
        if peak_idx < len(rates) - 1:
            post_peak = rates[peak_idx + 1:]
            if post_peak and max(post_peak) < peak_val - 0.05:
                # Significant drop after peak = roll-over
                rollover_fid = sorted_cands[peak_idx].environment_fidelity
                return (True, rollover_fid)

        return (False, None)


def run_srt(
    project_path: str,
    fidelity_pass_rates: Optional[dict[float, float]] = None,
    pta_value: float = 0.0,
    delta: float = 10.0,
) -> SRTResult:
    """Convenience entry point for SRT analysis."""
    from ussy_calibre.scanner import scan_project

    scan = scan_project(project_path)
    analyzer = SRTAnalyzer(scan)
    return analyzer.analyze(
        fidelity_pass_rates=fidelity_pass_rates,
        pta_value=pta_value,
        delta=delta,
    )
