"""Core data models for Strata."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Probe:
    """A behavioral probe — an assertion about a package's observable behavior."""

    name: str
    package: str
    function: str
    input_data: Any = None
    expected_output: Any = None
    output_has_keys: Optional[List[str]] = None
    target_mutated: Optional[bool] = None
    raises: Optional[str] = None
    returns_type: Optional[str] = None
    custom_assertion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class ProbeResult:
    """Result of running a single probe against a specific version."""

    probe_name: str
    package: str
    version: str
    passed: bool
    actual_output: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class VersionProbeResult:
    """Aggregated probe results for a single version of a package."""

    package: str
    version: str
    results: List[ProbeResult] = field(default_factory=list)
    timestamp: str = ""

    @property
    def total_probes(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.passed_count / self.total_probes


@dataclass
class BedrockReport:
    """Bedrock stability analysis for a function or API surface."""

    package: str
    function: str
    bedrock_score: float  # 0-100
    versions_stable: int
    versions_total: int
    years_stable: float
    stability_tier: str = ""  # Auto-set by __post_init__

    def __post_init__(self):
        if self.bedrock_score >= 90:
            self.stability_tier = "bedrock"
        elif self.bedrock_score >= 65:
            self.stability_tier = "stable"
        elif self.bedrock_score >= 35:
            self.stability_tier = "hazard"
        elif self.bedrock_score >= 15:
            self.stability_tier = "quicksand"
        else:
            self.stability_tier = "deprecated"


@dataclass
class SeismicReport:
    """Seismic hazard analysis — frequency of behavioral changes."""

    package: str
    function: str
    quakes_per_version: float
    total_quakes: int
    versions_scanned: int
    recent_quakes: int  # quakes in last 5 versions
    hazard_level: str = ""  # Auto-set by __post_init__

    def __post_init__(self):
        if self.quakes_per_version < 0.05:
            self.hazard_level = "dormant"
        elif self.quakes_per_version < 0.15:
            self.hazard_level = "minor"
        elif self.quakes_per_version < 0.35:
            self.hazard_level = "moderate"
        elif self.quakes_per_version < 0.6:
            self.hazard_level = "major"
        else:
            self.hazard_level = "catastrophic"


@dataclass
class FaultLine:
    """A boundary between bedrock and unstable regions."""

    package: str
    bedrock_function: str
    unstable_function: str
    bedrock_score: float
    unstable_score: float
    description: str = ""


@dataclass
class ErosionReport:
    """Erosion analysis — slow deprecation of features across versions."""

    package: str
    function: str
    erosion_rate: float  # decline in pass rate per version
    initial_pass_rate: float
    current_pass_rate: float
    versions_declining: int
    is_eroding: bool  # True if erosion_rate is significantly negative


@dataclass
class StratigraphicColumn:
    """A geological column showing the stability profile of a package."""

    package: str
    bedrock_reports: List[BedrockReport] = field(default_factory=list)
    seismic_reports: List[SeismicReport] = field(default_factory=list)
    fault_lines: List[FaultLine] = field(default_factory=list)
    erosion_reports: List[ErosionReport] = field(default_factory=list)

    @property
    def total_functions(self) -> int:
        return len(self.bedrock_reports)


@dataclass
class DiffResult:
    """Result of comparing two versions of a package."""

    package: str
    version_a: str
    version_b: str
    behavioral_quakes: List[Dict[str, Any]] = field(default_factory=list)
    new_behaviors: List[str] = field(default_factory=list)
    removed_behaviors: List[str] = field(default_factory=list)
    unchanged_count: int = 0

    @property
    def has_quakes(self) -> bool:
        return len(self.behavioral_quakes) > 0


@dataclass
class ScanResult:
    """Result of scanning a lockfile for seismic hazards."""

    lockfile: str
    fault_lines: List[FaultLine] = field(default_factory=list)
    quicksand_zones: List[BedrockReport] = field(default_factory=list)
    erosion_warnings: List[ErosionReport] = field(default_factory=list)
    packages_scanned: int = 0

    @property
    def has_hazards(self) -> bool:
        return bool(self.fault_lines or self.quicksand_zones or self.erosion_warnings)
