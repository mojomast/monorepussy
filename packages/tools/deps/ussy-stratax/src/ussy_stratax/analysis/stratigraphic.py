"""Stratigraphic analysis — combine all analyzers into a full column."""

from __future__ import annotations

from typing import Dict, List, Optional

from ussy_stratax.models import (
    BedrockReport,
    ErosionReport,
    FaultLine,
    SeismicReport,
    StratigraphicColumn,
    VersionProbeResult,
)
from ussy_stratax.analysis.bedrock import BedrockAnalyzer
from ussy_stratax.analysis.seismic import SeismicAnalyzer
from ussy_stratax.analysis.faults import FaultLineDetector
from ussy_stratax.analysis.erosion import ErosionAnalyzer


class StratigraphicAnalyzer:
    """Produce a complete stratigraphic column for a package.

    Combines bedrock, seismic, fault line, and erosion analysis into
    a single coherent view.
    """

    def __init__(
        self,
        stability_threshold: float = 0.95,
        recent_window: int = 5,
        score_gap_threshold: float = 40.0,
        erosion_threshold: float = -0.02,
    ):
        self.bedrock_analyzer = BedrockAnalyzer(stability_threshold)
        self.seismic_analyzer = SeismicAnalyzer(recent_window)
        self.fault_detector = FaultLineDetector(score_gap_threshold)
        self.erosion_analyzer = ErosionAnalyzer(erosion_threshold)

    def analyze(
        self,
        package: str,
        version_results_by_function: Dict[str, List[VersionProbeResult]],
        version_dates: Optional[Dict[str, str]] = None,
    ) -> StratigraphicColumn:
        """Produce a full stratigraphic column for a package."""
        # Bedrock analysis
        bedrock_reports = []
        for function, version_results in version_results_by_function.items():
            bedrock_reports.append(
                self.bedrock_analyzer.analyze_function(
                    package, function, version_results, version_dates
                )
            )

        # Sort by bedrock score descending
        bedrock_reports.sort(key=lambda r: r.bedrock_score, reverse=True)

        # Seismic analysis
        seismic_reports = []
        for function, version_results in version_results_by_function.items():
            seismic_reports.append(
                self.seismic_analyzer.analyze_function(
                    package, function, version_results
                )
            )

        # Fault line detection
        fault_lines = self.fault_detector.detect(package, bedrock_reports)

        # Erosion analysis
        erosion_reports = []
        for function, version_results in version_results_by_function.items():
            erosion_reports.append(
                self.erosion_analyzer.analyze_function(
                    package, function, version_results
                )
            )

        return StratigraphicColumn(
            package=package,
            bedrock_reports=bedrock_reports,
            seismic_reports=seismic_reports,
            fault_lines=fault_lines,
            erosion_reports=erosion_reports,
        )
