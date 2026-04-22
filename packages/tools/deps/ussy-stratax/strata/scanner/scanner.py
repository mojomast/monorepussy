"""Project scanner — scan a project for seismic hazards."""

from __future__ import annotations

from typing import Dict, List, Optional

from strata.models import (
    BedrockReport,
    ErosionReport,
    FaultLine,
    ScanResult,
    VersionProbeResult,
)
from strata.scanner.lockfile import Dependency, LockfileParser
from strata.analysis.stratigraphic import StratigraphicAnalyzer
from strata.analysis.bedrock import BedrockAnalyzer
from strata.analysis.faults import FaultLineDetector
from strata.analysis.erosion import ErosionAnalyzer


class ProjectScanner:
    """Scan a project's dependencies for seismic hazards."""

    def __init__(
        self,
        analyzer: Optional[StratigraphicAnalyzer] = None,
        version_data: Optional[Dict[str, Dict[str, List[VersionProbeResult]]]] = None,
    ):
        self.parser = LockfileParser()
        self.analyzer = analyzer or StratigraphicAnalyzer()
        # version_data: {package_name: {function: [VersionProbeResult]}}
        self.version_data = version_data or {}

    def scan(self, lockfile_path: str) -> ScanResult:
        """Scan a lockfile for seismic hazards."""
        dependencies = self.parser.parse(lockfile_path)
        return self.scan_dependencies(dependencies, lockfile_path)

    def scan_dependencies(
        self, dependencies: List[Dependency], lockfile_path: str = ""
    ) -> ScanResult:
        """Scan a list of dependencies for seismic hazards."""
        all_fault_lines: List[FaultLine] = []
        all_quicksand: List[BedrockReport] = []
        all_erosion: List[ErosionReport] = []

        for dep in dependencies:
            if dep.name not in self.version_data:
                continue

            func_data = self.version_data[dep.name]

            # Run full analysis
            column = self.analyzer.analyze(dep.name, func_data)

            # Collect fault lines
            all_fault_lines.extend(column.fault_lines)

            # Collect quicksand zones (very unstable functions)
            for report in column.bedrock_reports:
                if report.stability_tier in ("quicksand", "deprecated"):
                    all_quicksand.append(report)

            # Collect erosion warnings
            for report in column.erosion_reports:
                if report.is_eroding:
                    all_erosion.append(report)

        return ScanResult(
            lockfile=lockfile_path,
            fault_lines=all_fault_lines,
            quicksand_zones=all_quicksand,
            erosion_warnings=all_erosion,
            packages_scanned=len(dependencies),
        )
