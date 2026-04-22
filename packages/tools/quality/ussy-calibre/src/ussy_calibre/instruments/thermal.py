"""Thermal Profiler — Environment Sensitivity Analysis.

Maps how tests respond to environmental "temperature" changes.
Classifies tests by their thermal tolerance:
- Thermophilic: tests that only pass under specific conditions
- Mesophilic: tests that tolerate normal environmental variation
- Psychrophilic: tests that pass in any environment (hardiest)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from ussy_calibre.models import (
    TestOutcomeLevain as TestOutcome,
    ThermalProfile,
    ThermalReport,
    ThermalTolerance,

    TestResult,
)


class ThermalProfiler:
    """Profile environment sensitivity of tests."""

    def __init__(
        self,
        thermophilic_threshold: float = 0.6,
        psychrophilic_threshold: float = 0.2,
    ):
        self.thermophilic_threshold = thermophilic_threshold
        self.psychrophilic_threshold = psychrophilic_threshold

    def profile(
        self,
        test_results: list[TestResult],
        environment_data: Optional[dict[str, list[dict]]] = None,
    ) -> ThermalReport:
        """Profile thermal sensitivity of tests.

        Args:
            test_results: Current test results.
            environment_data: Dict of test_id -> list of {
                'environment': str (e.g., "linux", "windows"),
                'outcome': TestOutcome,
                'factors': dict of environment factor values
            }

        Returns:
            ThermalReport with profiles and climate control suggestions.
        """
        if environment_data is None:
            # Without environment data, use heuristic classification
            return self._profile_without_env(test_results)

        profiles = []
        suggestions = []

        # Gather all environment factors
        all_factors: set[str] = set()
        for env_list in environment_data.values():
            for entry in env_list:
                if "factors" in entry:
                    all_factors.update(entry["factors"].keys())

        for tr in test_results:
            env_entries = environment_data.get(tr.test_id, [])

            if not env_entries:
                # No environment data — assume mesophilic
                profiles.append(ThermalProfile(
                    test_id=tr.test_id,
                    name=tr.name,
                    tolerance=ThermalTolerance.MESOPHILIC,
                    environment_correlations={},
                    sensitivity_factors=[],
                ))
                continue

            # Calculate environment-failure correlations
            correlations = self._compute_correlations(env_entries, all_factors)

            # Classify thermal tolerance
            max_correlation = max(correlations.values()) if correlations else 0.0
            sensitive_factors = [
                factor
                for factor, corr in correlations.items()
                if corr > self.psychrophilic_threshold
            ]

            if max_correlation >= self.thermophilic_threshold:
                tolerance = ThermalTolerance.THERMOPHILIC
            elif max_correlation <= self.psychrophilic_threshold:
                tolerance = ThermalTolerance.PSYCHROPHILIC
            else:
                tolerance = ThermalTolerance.MESOPHILIC

            profiles.append(ThermalProfile(
                test_id=tr.test_id,
                name=tr.name,
                tolerance=tolerance,
                environment_correlations=correlations,
                sensitivity_factors=sensitive_factors,
            ))

        # Generate climate control suggestions
        thermophilic = [p for p in profiles if p.tolerance == ThermalTolerance.THERMOPHILIC]
        if thermophilic:
            suggestions.append(
                f"{len(thermophilic)} thermophilic tests detected — these require specific "
                "environmental conditions. Consider mocking external services, fixing timezone "
                "assumptions, and using deterministic test data."
            )
            for p in thermophilic[:5]:
                if p.sensitivity_factors:
                    suggestions.append(
                        f"  Test '{p.name}' is sensitive to: {', '.join(p.sensitivity_factors)}"
                    )

        # Environment summary
        env_summary = {
            "thermophilic": str(len([p for p in profiles if p.tolerance == ThermalTolerance.THERMOPHILIC])),
            "mesophilic": str(len([p for p in profiles if p.tolerance == ThermalTolerance.MESOPHILIC])),
            "psychrophilic": str(len([p for p in profiles if p.tolerance == ThermalTolerance.PSYCHROPHILIC])),
        }

        if not suggestions:
            suggestions.append("All tests show good environmental tolerance — culture is robust.")

        return ThermalReport(
            profiles=profiles,
            climate_control_suggestions=suggestions,
            environment_summary=env_summary,
        )

    def _profile_without_env(self, test_results: list[TestResult]) -> ThermalReport:
        """Generate a basic thermal profile without explicit environment data.

        Uses heuristics based on test names, modules, and timing.
        """
        profiles = []
        env_sensitive_keywords = {
            "timezone", "network", "http", "api", "socket", "time",
            "date", "locale", "os", "platform", "env", "config",
            "external", "remote", "integration", "e2e",
        }

        for tr in test_results:
            # Heuristic: check test name and module for environment-sensitive keywords
            test_lower = (tr.name + " " + tr.module).lower()
            sensitive = [kw for kw in env_sensitive_keywords if kw in test_lower]

            # Long-running tests are more likely environment-sensitive
            if tr.duration > 5.0:
                sensitive.append("slow_duration")

            # Estimate correlation
            correlation = min(1.0, len(sensitive) * 0.25)

            if correlation >= self.thermophilic_threshold:
                tolerance = ThermalTolerance.THERMOPHILIC
            elif correlation <= self.psychrophilic_threshold:
                tolerance = ThermalTolerance.PSYCHROPHILIC
            else:
                tolerance = ThermalTolerance.MESOPHILIC

            profiles.append(ThermalProfile(
                test_id=tr.test_id,
                name=tr.name,
                tolerance=tolerance,
                environment_correlations={
                    "heuristic": correlation,
                },
                sensitivity_factors=sensitive,
            ))

        # Summary
        env_summary = {
            "thermophilic": str(len([p for p in profiles if p.tolerance == ThermalTolerance.THERMOPHILIC])),
            "mesophilic": str(len([p for p in profiles if p.tolerance == ThermalTolerance.MESOPHILIC])),
            "psychrophilic": str(len([p for p in profiles if p.tolerance == ThermalTolerance.PSYCHROPHILIC])),
            "note": "Profiled without explicit environment data (using heuristics)",
        }

        thermophilic = [p for p in profiles if p.tolerance == ThermalTolerance.THERMOPHILIC]
        suggestions = []
        if thermophilic:
            suggestions.append(
                f"{len(thermophilic)} potentially thermophilic tests detected by heuristic. "
                "Run with explicit environment data for accurate profiling."
            )
        else:
            suggestions.append("No obviously thermophilic tests detected by heuristic.")

        return ThermalReport(
            profiles=profiles,
            climate_control_suggestions=suggestions,
            environment_summary=env_summary,
        )

    def _compute_correlations(
        self,
        env_entries: list[dict],
        factors: set[str],
    ) -> dict[str, float]:
        """Compute correlation between environment factors and test failures."""
        correlations = {}

        for factor in factors:
            # Simple correlation: does this factor value predict failures?
            factor_values = []
            outcomes = []
            for entry in env_entries:
                entry_factors = entry.get("factors", {})
                if factor in entry_factors:
                    try:
                        factor_values.append(float(entry_factors[factor]))
                    except (ValueError, TypeError):
                        # Categorical factor: encode as 0/1 for presence
                        factor_values.append(1.0)
                    outcomes.append(
                        1.0 if entry.get("outcome") in (TestOutcome.FAILED, TestOutcome.ERROR)
                        else 0.0
                    )

            if not factor_values:
                continue

            # Simple Pearson-like correlation
            correlations[factor] = self._pearson_r(factor_values, outcomes)

        return correlations

    @staticmethod
    def _pearson_r(x: list[float], y: list[float]) -> float:
        """Compute Pearson correlation coefficient."""
        n = len(x)
        if n < 2:
            return 0.0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denom_x = sum((xi - mean_x) ** 2 for xi in x)
        denom_y = sum((yi - mean_y) ** 2 for yi in y)

        denominator = (denom_x * denom_y) ** 0.5
        if denominator == 0:
            return 0.0

        return abs(numerator / denominator)
