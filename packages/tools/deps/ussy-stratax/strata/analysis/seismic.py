"""Seismic hazard analysis — frequency of behavioral changes."""

from __future__ import annotations

from typing import Dict, List, Optional

from strata.models import ProbeResult, SeismicReport, VersionProbeResult


class SeismicAnalyzer:
    """Analyze seismic hazard — how frequently does behavior shift?

    Measures behavioral quakes per version. A quake is a probe result that
    differs from the previous version's result for the same probe.
    """

    def __init__(self, recent_window: int = 5):
        self.recent_window = recent_window

    def analyze_function(
        self,
        package: str,
        function: str,
        version_results: List[VersionProbeResult],
    ) -> SeismicReport:
        """Compute seismic hazard for a single function."""
        if not version_results:
            return SeismicReport(
                package=package,
                function=function,
                quakes_per_version=0.0,
                total_quakes=0,
                versions_scanned=0,
                recent_quakes=0,
            )

        versions_scanned = len(version_results)
        total_quakes = 0

        # Build probe timelines
        probe_timelines: Dict[str, List[bool]] = {}
        for vr in version_results:
            for result in vr.results:
                if result.probe_name not in probe_timelines:
                    probe_timelines[result.probe_name] = []
                probe_timelines[result.probe_name].append(result.passed)

        # Count quakes (transitions from pass->fail or fail->pass)
        for probe_name, timeline in probe_timelines.items():
            for i in range(1, len(timeline)):
                if timeline[i] != timeline[i - 1]:
                    total_quakes += 1

        # Count recent quakes (last N versions)
        recent_quakes = 0
        recent_versions = version_results[-self.recent_window:]
        recent_probe_timelines: Dict[str, List[bool]] = {}
        for vr in recent_versions:
            for result in vr.results:
                if result.probe_name not in recent_probe_timelines:
                    recent_probe_timelines[result.probe_name] = []
                recent_probe_timelines[result.probe_name].append(result.passed)

        for probe_name, timeline in recent_probe_timelines.items():
            for i in range(1, len(timeline)):
                if timeline[i] != timeline[i - 1]:
                    recent_quakes += 1

        quakes_per_version = total_quakes / versions_scanned if versions_scanned else 0.0

        return SeismicReport(
            package=package,
            function=function,
            quakes_per_version=round(quakes_per_version, 3),
            total_quakes=total_quakes,
            versions_scanned=versions_scanned,
            recent_quakes=recent_quakes,
        )

    def analyze_package(
        self,
        package: str,
        version_results_by_function: Dict[str, List[VersionProbeResult]],
    ) -> List[SeismicReport]:
        """Compute seismic hazards for all functions in a package."""
        reports = []
        for function, version_results in version_results_by_function.items():
            reports.append(
                self.analyze_function(package, function, version_results)
            )
        return reports
