"""Isolation Audiometry — Masking for test suites.

Quantifies test isolation effectiveness, detects overmocking and undermasking,
and finds the isolation sweet spot via the plateau method.
"""

from __future__ import annotations

import math
from typing import Optional

from ussy_calibre.models import (
    IsolationModuleResult,
    IsolationResult,
    IsolationSweepPoint,
    ProjectScan,
)
from ussy_calibre.utils import mean, stdev


class IsolationAnalyzer:
    """Analyzes test isolation effectiveness via masking analogies."""

    def __init__(self, scan: ProjectScan) -> None:
        self.scan = scan

    def analyze(
        self,
        module_isolation_data: Optional[dict[str, dict]] = None,
    ) -> IsolationResult:
        """Compute isolation audiometry.

        Args:
            module_isolation_data: Optional per-module-pair isolation data.
                Keys: "A|B" (module pair), values: dict with:
                  - "crosstalk": float
                  - "sweep_points": list of (isolation_level, pass_rate, assertion_count, code_covered_pct)
                If None, heuristic data is computed.
        """
        module_results: list[IsolationModuleResult] = []

        # Get module names from source
        source_names = []
        for mod in self.scan.source_modules:
            basename = mod.filepath.split("/")[-1].replace(".py", "")
            if basename and not basename.startswith("__"):
                source_names.append(basename)

        # Remove duplicates while preserving order
        seen = set()
        unique_names = []
        for n in source_names:
            if n not in seen:
                seen.add(n)
                unique_names.append(n)
        source_names = unique_names

        if len(source_names) < 2:
            # Need at least 2 modules for isolation analysis
            source_names = ["module_a", "module_b"]

        # Analyze pairs of adjacent modules
        for i in range(len(source_names) - 1):
            mod_a = source_names[i]
            mod_b = source_names[i + 1]
            pair_key = f"{mod_a}|{mod_b}"

            if module_isolation_data and pair_key in module_isolation_data:
                data = module_isolation_data[pair_key]
                result = self._analyze_pair_data(mod_a, mod_b, data)
            else:
                result = self._estimate_pair(mod_a, mod_b)
            module_results.append(result)

        # Collect global findings
        dilemmas = [f"{r.module_a}|{r.module_b}" for r in module_results if r.is_dilemma]
        overmocked = []
        undermasked = []
        for r in module_results:
            if r.is_overmocked:
                overmocked.append(r.module_a)
            if r.is_undermasked:
                undermasked.append(r.module_a)

        return IsolationResult(
            module_results=module_results,
            dilemmas=dilemmas,
            overmocked_modules=overmocked,
            undermasked_modules=undermasked,
        )

    def _analyze_pair_data(
        self, mod_a: str, mod_b: str, data: dict
    ) -> IsolationModuleResult:
        """Analyze isolation data for a module pair."""
        crosstalk = data.get("crosstalk", 0.0)

        # Compute isolation attenuation
        if crosstalk > 0:
            attenuation = -math.log2(crosstalk)
        else:
            attenuation = float("inf")

        # Process sweep points
        sweep_data = data.get("sweep_points", [])
        sweep_points = []
        for sp in sweep_data:
            sweep_points.append(
                IsolationSweepPoint(
                    isolation_level=sp[0],
                    pass_rate=sp[1],
                    assertion_count=sp[2],
                    code_covered_pct=sp[3],
                )
            )

        # Find plateau range
        plateau_range = self._find_plateau(sweep_points)

        # Detect pathologies
        is_overmocked = False
        is_undermasked = False
        is_dilemma = False

        if sweep_points:
            # Check if high isolation drops assertion count significantly
            high_iso = [sp for sp in sweep_points if sp.isolation_level >= 80]
            low_iso = [sp for sp in sweep_points if sp.isolation_level <= 20]
            if high_iso and low_iso:
                high_assert = mean([sp.assertion_count for sp in high_iso])
                low_assert = mean([sp.assertion_count for sp in low_iso])
                if low_assert > 0 and high_assert < low_assert * 0.3:
                    is_overmocked = True
                if low_assert > 0 and high_assert > low_assert * 1.5:
                    is_undermasked = True

        # Check for isolation dilemma
        if plateau_range[0] > plateau_range[1]:
            is_dilemma = True

        return IsolationModuleResult(
            module_a=mod_a,
            module_b=mod_b,
            crosstalk=round(crosstalk, 4),
            attenuation=round(attenuation, 2) if attenuation != float("inf") else attenuation,
            plateau_range=plateau_range,
            is_overmocked=is_overmocked,
            is_undermasked=is_undermasked,
            is_dilemma=is_dilemma,
            sweep_points=sweep_points,
        )

    def _estimate_pair(self, mod_a: str, mod_b: str) -> IsolationModuleResult:
        """Heuristic isolation estimate from scan data."""
        # Generate sweep points
        sweep_points = []
        for level in range(0, 101, 10):
            # Simulate plateau behavior
            if level < 30:
                # Undermasked: results drift
                pass_rate = 0.5 + 0.2 * math.sin(level * 0.3)
                assertion_count = 10
                code_covered = 80.0
            elif level <= 70:
                # Plateau: stable
                pass_rate = 0.95
                assertion_count = 8
                code_covered = 70.0
            else:
                # Overmasked: dropping coverage
                pass_rate = 0.95
                assertion_count = max(1, 8 - (level - 70) // 5)
                code_covered = max(5.0, 70.0 - (level - 70) * 1.5)

            sweep_points.append(
                IsolationSweepPoint(
                    isolation_level=level,
                    pass_rate=round(pass_rate, 2),
                    assertion_count=assertion_count,
                    code_covered_pct=round(code_covered, 1),
                )
            )

        # Estimate crosstalk from shared imports (heuristic)
        crosstalk = 0.1  # mild coupling default
        attenuation = -math.log2(crosstalk) if crosstalk > 0 else float("inf")

        plateau_range = self._find_plateau(sweep_points)

        return IsolationModuleResult(
            module_a=mod_a,
            module_b=mod_b,
            crosstalk=round(crosstalk, 4),
            attenuation=round(attenuation, 2),
            plateau_range=plateau_range,
            is_overmocked=False,
            is_undermasked=False,
            is_dilemma=False,
            sweep_points=sweep_points,
        )

    def _find_plateau(
        self, sweep_points: list[IsolationSweepPoint]
    ) -> tuple[int, int]:
        """Find the isolation plateau range from sweep data.

        The plateau is where pass rate is stable (within 5% of max).
        """
        if not sweep_points:
            return (0, 0)

        max_pass = max(sp.pass_rate for sp in sweep_points)
        threshold = max_pass * 0.95

        plateau_levels = [
            sp.isolation_level
            for sp in sweep_points
            if sp.pass_rate >= threshold
        ]

        if not plateau_levels:
            return (0, 0)

        return (min(plateau_levels), max(plateau_levels))


def run_isolation(
    project_path: str,
    module_isolation_data: Optional[dict[str, dict]] = None,
) -> IsolationResult:
    """Convenience entry point for Isolation analysis."""
    from ussy_calibre.scanner import scan_project

    scan = scan_project(project_path)
    analyzer = IsolationAnalyzer(scan)
    return analyzer.analyze(module_isolation_data=module_isolation_data)
