"""Bedrock Score computation — how long has behavior been stable?"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ussy_stratax.models import BedrockReport, ProbeResult, VersionProbeResult


class BedrockAnalyzer:
    """Compute bedrock scores from probe results across versions.

    Bedrock Score (0-100): How long and how consistently has this behavior
    been stable? A function that hasn't changed its observable behavior
    across many versions over many years gets 95+.
    """

    def __init__(self, stability_threshold: float = 0.95):
        self.stability_threshold = stability_threshold

    def analyze_function(
        self,
        package: str,
        function: str,
        version_results: List[VersionProbeResult],
        version_dates: Optional[Dict[str, str]] = None,
    ) -> BedrockReport:
        """Compute the bedrock score for a single function across versions."""
        if not version_results:
            return BedrockReport(
                package=package,
                function=function,
                bedrock_score=0.0,
                versions_stable=0,
                versions_total=0,
                years_stable=0.0,
            )

        # Track when each probe for this function changed behavior
        versions_total = len(version_results)
        versions_stable = 0
        consecutive_stable = 0

        # Build a timeline of probe results for this function
        probe_history: Dict[str, List[bool]] = {}
        for vr in version_results:
            for result in vr.results:
                if result.probe_name not in probe_history:
                    probe_history[result.probe_name] = []
                probe_history[result.probe_name].append(result.passed)

        # Count behavioral changes (quakes) across the timeline
        total_quakes = 0
        total_transitions = 0

        for probe_name, history in probe_history.items():
            for i in range(1, len(history)):
                if history[i] != history[i - 1]:
                    total_quakes += 1
                total_transitions += 1

        # Compute stability: ratio of non-change transitions
        if total_transitions > 0:
            stability_ratio = 1.0 - (total_quakes / total_transitions)
        else:
            stability_ratio = 1.0 if all(
                all(h) for h in probe_history.values()
            ) else 0.0

        # Count consecutive stable versions (from the end)
        for vr in reversed(version_results):
            func_results = [
                r for r in vr.results
            ]
            if func_results and all(r.passed for r in func_results):
                consecutive_stable += 1
            else:
                break

        # Count versions where all probes passed
        for vr in version_results:
            if vr.results and all(r.passed for r in vr.results):
                versions_stable += 1

        # Compute years stable
        years_stable = 0.0
        if version_dates:
            # Find the earliest version where stability started
            date_list = []
            for vr in version_results:
                if vr.version in version_dates:
                    date_list.append((vr.version, version_dates[vr.version]))

            if len(date_list) >= 2 and consecutive_stable >= 2:
                try:
                    earliest_stable = date_list[-consecutive_stable][1]
                    latest = date_list[-1][1]
                    d1 = datetime.fromisoformat(earliest_stable.replace("Z", "+00:00"))
                    d2 = datetime.fromisoformat(latest.replace("Z", "+00:00"))
                    years_stable = (d2 - d1).days / 365.25
                except (ValueError, IndexError):
                    years_stable = 0.0

        # Bedrock score formula
        # Weight: version stability (60%), consistency of results (25%), time (15%)
        version_score = (versions_stable / versions_total) * 100 if versions_total else 0
        consistency_score = stability_ratio * 100
        time_score = min(years_stable / 3.0, 1.0) * 100  # Cap at 3 years

        bedrock_score = (
            version_score * 0.60
            + consistency_score * 0.25
            + time_score * 0.15
        )

        return BedrockReport(
            package=package,
            function=function,
            bedrock_score=round(bedrock_score, 1),
            versions_stable=versions_stable,
            versions_total=versions_total,
            years_stable=round(years_stable, 2),
        )

    def analyze_package(
        self,
        package: str,
        version_results_by_function: Dict[str, List[VersionProbeResult]],
        version_dates: Optional[Dict[str, str]] = None,
    ) -> List[BedrockReport]:
        """Compute bedrock scores for all functions in a package."""
        reports = []
        for function, version_results in version_results_by_function.items():
            reports.append(
                self.analyze_function(package, function, version_results, version_dates)
            )
        return reports
