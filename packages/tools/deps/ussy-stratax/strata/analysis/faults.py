"""Fault line detection — boundaries between stable and unstable regions."""

from __future__ import annotations

from typing import List, Optional

from strata.models import BedrockReport, FaultLine


class FaultLineDetector:
    """Detect fault lines — boundaries between bedrock and unstable API regions.

    A fault line exists when two related functions in the same package have
    dramatically different stability profiles — one is bedrock, the other is
    unstable.
    """

    def __init__(self, score_gap_threshold: float = 40.0):
        self.score_gap_threshold = score_gap_threshold

    def detect(
        self,
        package: str,
        bedrock_reports: List[BedrockReport],
        related_functions: Optional[List[tuple]] = None,
    ) -> List[FaultLine]:
        """Detect fault lines from bedrock reports.

        Args:
            package: Package name
            bedrock_reports: List of bedrock reports for functions
            related_functions: Optional list of (func_a, func_b) tuples
                indicating related functions. If not provided, all pairs
                are checked.
        """
        fault_lines = []

        # Build a lookup
        report_map = {r.function: r for r in bedrock_reports}
        functions = [r.function for r in bedrock_reports]

        if related_functions:
            pairs = related_functions
        else:
            # Check all pairs (O(n^2) but fine for typical API sizes)
            pairs = []
            for i in range(len(functions)):
                for j in range(i + 1, len(functions)):
                    pairs.append((functions[i], functions[j]))

        for func_a, func_b in pairs:
            if func_a not in report_map or func_b not in report_map:
                continue

            report_a = report_map[func_a]
            report_b = report_map[func_b]

            score_gap = abs(report_a.bedrock_score - report_b.bedrock_score)

            if score_gap >= self.score_gap_threshold:
                # Determine which is stable and which is unstable
                if report_a.bedrock_score >= report_b.bedrock_score:
                    stable_func = func_a
                    unstable_func = func_b
                    stable_score = report_a.bedrock_score
                    unstable_score = report_b.bedrock_score
                else:
                    stable_func = func_b
                    unstable_func = func_a
                    stable_score = report_b.bedrock_score
                    unstable_score = report_a.bedrock_score

                description = (
                    f"{stable_func} is bedrock (score: {stable_score:.0f}) "
                    f"but {unstable_func} is unstable (score: {unstable_score:.0f})"
                )

                fault_lines.append(
                    FaultLine(
                        package=package,
                        bedrock_function=stable_func,
                        unstable_function=unstable_func,
                        bedrock_score=stable_score,
                        unstable_score=unstable_score,
                        description=description,
                    )
                )

        return fault_lines

    def detect_from_reports(
        self, reports: List[BedrockReport]
    ) -> List[FaultLine]:
        """Detect fault lines from bedrock reports, grouping by package."""
        by_package = {}
        for r in reports:
            by_package.setdefault(r.package, []).append(r)

        all_faults = []
        for package, pkg_reports in by_package.items():
            all_faults.extend(self.detect(package, pkg_reports))

        return all_faults
