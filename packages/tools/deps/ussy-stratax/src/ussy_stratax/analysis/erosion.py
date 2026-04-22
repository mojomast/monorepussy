"""Erosion analysis — slow deprecation of features across versions."""

from __future__ import annotations

from typing import Dict, List

from ussy_stratax.models import ErosionReport, VersionProbeResult


class ErosionAnalyzer:
    """Detect erosion — slow deprecation where probe pass rates decline over versions.

    Erosion is when features are gradually deprecated or broken across "compatible"
    versions. Unlike a sudden quake, erosion is a slow decline in pass rates.
    """

    def __init__(self, erosion_threshold: float = -0.02):
        """Args:
            erosion_threshold: Minimum decline rate (per version) to flag as erosion.
                Negative values indicate declining pass rates. Default: -0.02 (2% decline per version).
        """
        self.erosion_threshold = erosion_threshold

    def analyze_function(
        self,
        package: str,
        function: str,
        version_results: List[VersionProbeResult],
    ) -> ErosionReport:
        """Compute erosion for a single function across versions."""
        if len(version_results) < 2:
            return ErosionReport(
                package=package,
                function=function,
                erosion_rate=0.0,
                initial_pass_rate=version_results[0].pass_rate if version_results else 0.0,
                current_pass_rate=version_results[0].pass_rate if version_results else 0.0,
                versions_declining=0,
                is_eroding=False,
            )

        # Compute pass rates across versions
        pass_rates = [vr.pass_rate for vr in version_results]

        initial_pass_rate = pass_rates[0]
        current_pass_rate = pass_rates[-1]

        # Compute erosion rate using linear regression slope
        # Simple least-squares: slope = (n*sum(xi*yi) - sum(xi)*sum(yi)) / (n*sum(xi^2) - (sum(xi))^2)
        n = len(pass_rates)
        x_vals = list(range(n))
        sum_x = sum(x_vals)
        sum_y = sum(pass_rates)
        sum_xy = sum(x * y for x, y in zip(x_vals, pass_rates))
        sum_x2 = sum(x * x for x in x_vals)

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            erosion_rate = 0.0
        else:
            erosion_rate = (n * sum_xy - sum_x * sum_y) / denominator

        # Count versions with declining pass rate vs previous
        versions_declining = 0
        for i in range(1, len(pass_rates)):
            if pass_rates[i] < pass_rates[i - 1]:
                versions_declining += 1

        is_eroding = erosion_rate < self.erosion_threshold

        return ErosionReport(
            package=package,
            function=function,
            erosion_rate=round(erosion_rate, 4),
            initial_pass_rate=round(initial_pass_rate, 4),
            current_pass_rate=round(current_pass_rate, 4),
            versions_declining=versions_declining,
            is_eroding=is_eroding,
        )

    def analyze_package(
        self,
        package: str,
        version_results_by_function: Dict[str, List[VersionProbeResult]],
    ) -> List[ErosionReport]:
        """Compute erosion for all functions in a package."""
        reports = []
        for function, version_results in version_results_by_function.items():
            reports.append(
                self.analyze_function(package, function, version_results)
            )
        return reports
