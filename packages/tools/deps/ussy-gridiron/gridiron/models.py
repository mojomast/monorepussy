"""Core data models for Gridiron analysis."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class HealthStatus(Enum):
    """Overall health status analogous to grid operating state."""
    NORMAL = "normal"
    WARNING = "warning"
    ALERT = "alert"
    EMERGENCY = "emergency"


class SystemState(Enum):
    """Post-contingency system state."""
    FUNCTIONAL = "functional"
    DEGRADED = "degraded"
    FAILED = "failed"


class ComplianceCategory(Enum):
    """IEEE 1547 interconnection category."""
    CATEGORY_I = "I"       # patch-safe
    CATEGORY_II = "II"     # minor-safe
    CATEGORY_III = "III"   # major-safe with fallbacks


class ComplianceResult(Enum):
    """Pass/fail for a single compliance check."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


class HandlerZone(Enum):
    """Protection zone for error handlers."""
    ZONE_1 = "zone_1"  # Immediate / < 80% of stack distance
    ZONE_2 = "zone_2"  # Backup / < 120%
    ZONE_3 = "zone_3"  # Remote / < 200%


# ---------------------------------------------------------------------------
# Package & dependency graph
# ---------------------------------------------------------------------------

@dataclass
class PackageInfo:
    """Metadata about a single package in the dependency graph."""
    name: str
    version: str = "0.0.0"
    is_direct: bool = False
    maintainers: int = 1
    last_release: Optional[datetime] = None
    release_frequency_days: float = 30.0
    issue_response_days: float = 7.0
    has_types: bool = False
    has_docs: bool = False
    has_tests: bool = False
    api_surface_size: int = 1
    side_effect_ratio: float = 0.0
    type_pollution: float = 0.0
    metadata_completeness: float = 1.0
    semver_compliance: float = 1.0
    risk_weight: float = 1.0
    version_rigidity: float = 0.5  # 0 = flexible (wide semver), 1 = rigid (pinned)
    has_error_handler: bool = False
    handler_timeout_ms: float = 1000.0
    handler_retry_count: int = 3
    handler_tds: float = 1.0  # Time dial setting
    handler_pickup: float = 1.0  # Pickup current
    backup_packages: List[str] = field(default_factory=list)

    @property
    def major(self) -> int:
        parts = self.version.split(".")
        return int(parts[0]) if parts else 0

    @property
    def minor(self) -> int:
        parts = self.version.split(".")
        return int(parts[1]) if len(parts) > 1 else 0

    @property
    def patch(self) -> int:
        parts = self.version.split(".")
        return int(parts[2]) if len(parts) > 2 else 0


@dataclass
class DependencyEdge:
    """A directed edge in the dependency graph."""
    source: str  # consumer package
    target: str  # consumed package
    version_constraint: str = "*"
    coupling_strength: float = 1.0  # 0-1, how tightly coupled
    is_dev: bool = False


@dataclass
class ErrorHandlerContext:
    """Error handler metadata for relay coordination."""
    package: str
    zone: HandlerZone = HandlerZone.ZONE_1
    timeout_ms: float = 1000.0
    retry_count: int = 3
    tds: float = 1.0  # Time dial setting
    pickup: float = 1.0  # Pickup current level
    error_types: List[str] = field(default_factory=lambda: ["Exception"])

    def trip_time(self, fault_current: float = 1.0) -> float:
        """Calculate trip time using inverse time-current characteristic.

        t_trip = TDS × (A / (I/I_pickup)^p - 1)
        Using IEEE moderately inverse curve: A=0.0515, p=0.02
        """
        if fault_current <= 0 or self.pickup <= 0:
            return float("inf")
        ratio = fault_current / self.pickup
        if ratio <= 1.0:
            return float("inf")
        # IEEE moderately inverse
        a, p = 0.0515, 0.02
        try:
            t = self.tds * (a / (ratio ** p - 1.0))
            return max(t, 0.001)
        except (ZeroDivisionError, OverflowError):
            return float("inf")


@dataclass
class VersionShock:
    """A version shock event (breaking change, deprecation, etc.)."""
    package: str
    old_version: str = ""
    new_version: str = ""
    severity: float = 1.0  # 0-1
    is_breaking: bool = False
    timestamp: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Analysis results
# ---------------------------------------------------------------------------

@dataclass
class ContingencyResult:
    """Result of N-1 contingency analysis for one removed package."""
    removed_package: str
    system_state: SystemState = SystemState.FUNCTIONAL
    affected_packages: List[str] = field(default_factory=list)
    blast_radius: float = 0.0
    is_spof: bool = False
    recommendation: str = ""


@dataclass
class N1Report:
    """Full N-1 compliance report."""
    total_packages: int = 0
    passing_packages: int = 0
    compliance_score: float = 0.0  # percentage 0-100
    spof_register: List[ContingencyResult] = field(default_factory=list)
    all_results: List[ContingencyResult] = field(default_factory=list)

    def __post_init__(self):
        if self.total_packages > 0:
            self.compliance_score = (self.passing_packages / self.total_packages) * 100
        else:
            self.compliance_score = 100.0


@dataclass
class FrequencyResult:
    """Frequency regulation analysis for one shock event."""
    shock: VersionShock = field(default_factory=VersionShock)
    frequency_deviation: float = 0.0
    droop_response: Dict[str, float] = field(default_factory=dict)  # pkg -> 1/Rv
    primary_recovery: float = 0.0  # fraction recovered by primary
    secondary_recovery: float = 0.0  # fraction recovered by secondary
    tertiary_needed: bool = False
    agc_equivalency_time: float = 0.0  # hours to 95% re-resolution
    rigid_transmitters: List[str] = field(default_factory=list)


@dataclass
class FrequencyReport:
    """Full frequency regulation report."""
    results: List[FrequencyResult] = field(default_factory=list)
    average_deviation: float = 0.0
    worst_deviation: float = 0.0
    droop_compliance_map: Dict[str, float] = field(default_factory=dict)


@dataclass
class DispatchResult:
    """Optimal dispatch result for one package."""
    package: str = ""
    optimal_weight: float = 0.0
    risk_contribution: float = 0.0
    is_congested: bool = False


@dataclass
class OPFReport:
    """Optimal Power Flow report for dependency dispatch."""
    total_risk: float = 0.0
    dispatch: List[DispatchResult] = field(default_factory=list)
    overcoupled_pairs: List[Tuple[str, str]] = field(default_factory=list)
    congestion_bottlenecks: List[str] = field(default_factory=list)
    redispatch_recommendations: List[str] = field(default_factory=list)


@dataclass
class CTIViolation:
    """Coordination Time Interval violation between two handlers."""
    primary_handler: str = ""
    backup_handler: str = ""
    primary_trip_time: float = 0.0
    backup_trip_time: float = 0.0
    cti_required: float = 0.2  # seconds
    cti_actual: float = 0.0
    violation_severity: str = "none"  # none, marginal, severe

    def __post_init__(self):
        self.cti_actual = self.backup_trip_time - self.primary_trip_time
        if self.cti_actual < 0:
            self.violation_severity = "severe"
        elif self.cti_actual < self.cti_required:
            self.violation_severity = "marginal"
        else:
            self.violation_severity = "none"


@dataclass
class RelayReport:
    """Protection coordination report."""
    handlers: List[ErrorHandlerContext] = field(default_factory=list)
    cti_violations: List[CTIViolation] = field(default_factory=list)
    zone_coverage: Dict[str, List[str]] = field(default_factory=dict)
    blind_spots: List[str] = field(default_factory=list)
    tcc_overlaps: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class VoltageResult:
    """Voltage/capability analysis for one package."""
    package: str = ""
    health_voltage: float = 1.0  # per-unit, 0-1.1
    reactive_capability: float = 0.0  # Q
    semantic_reactance: float = 0.0  # X
    q_margin: float = 0.0
    q_max: float = 0.0
    collapse_proximity_index: float = 0.0
    is_sagging: bool = False
    participation_factor: float = 0.0


@dataclass
class VoltageReport:
    """Full voltage / QV analysis report."""
    package_results: List[VoltageResult] = field(default_factory=list)
    weakest_packages: List[str] = field(default_factory=list)
    modal_eigenvalues: List[float] = field(default_factory=list)
    reactive_compensation_recommendations: List[str] = field(default_factory=list)


@dataclass
class InterconnectionCheck:
    """Single interconnection compliance check."""
    name: str = ""
    result: ComplianceResult = ComplianceResult.PASS
    value: float = 0.0
    threshold: float = 0.0
    details: str = ""


@dataclass
class GridCodeReport:
    """IEEE 1547 interconnection compliance report for one package."""
    package: str = ""
    category: ComplianceCategory = ComplianceCategory.CATEGORY_II
    checks: List[InterconnectionCheck] = field(default_factory=list)
    overall_compliance: ComplianceResult = ComplianceResult.PASS
    power_factor: float = 1.0  # metadata completeness analog
    ride_through_results: Dict[str, bool] = field(default_factory=dict)


@dataclass
class FullReport:
    """Complete Grid Reliability Assessment."""
    project_path: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    n1_report: Optional[N1Report] = None
    frequency_report: Optional[FrequencyReport] = None
    opf_report: Optional[OPFReport] = None
    relay_report: Optional[RelayReport] = None
    voltage_report: Optional[VoltageReport] = None
    grid_code_reports: List[GridCodeReport] = field(default_factory=list)
    overall_status: HealthStatus = HealthStatus.NORMAL
