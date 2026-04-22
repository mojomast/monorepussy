"""Data models for Calibre metrological analysis."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


class TestResult(enum.Enum):
    __test__ = False
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"


class UncertaintyType(enum.Enum):
    TYPE_A = "type_a"  # statistical / random
    TYPE_B = "type_b"  # systematic


class RRCategory(enum.Enum):
    ACCEPTABLE = "acceptable"       # %GRR < 10%
    CONDITIONAL = "conditional"     # 10% <= %GRR <= 30%
    UNACCEPTABLE = "unacceptable"   # %GRR > 30%


@dataclass
class TestRun:
    __test__ = False
    """A single test execution result."""
    test_name: str
    module: str
    suite: str
    build_id: str
    environment: str
    result: TestResult
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration: float = 0.0

    @property
    def passed(self) -> bool:
        return self.result == TestResult.PASS

    @property
    def numeric_result(self) -> float:
        """1.0 for pass, 0.0 for fail/error/skip."""
        return 1.0 if self.passed else 0.0


@dataclass
class UncertaintySource:
    """A single uncertainty source in the GUM budget."""
    name: str
    uncertainty_value: float  # u(x_i)
    sensitivity_coefficient: float  # c_i = df/dx_i
    correlation_with: Optional[str] = None  # name of correlated source
    correlation_coefficient: float = 0.0  # r(x_i, x_j)
    uncertainty_type: Optional[UncertaintyType] = None

    @property
    def contribution(self) -> float:
        """Contribution to combined variance: (c_i * u(x_i))^2."""
        return (self.sensitivity_coefficient * self.uncertainty_value) ** 2


@dataclass
class UncertaintyBudget:
    """Complete GUM uncertainty budget for a measurand."""
    measurand: str
    sources: List[UncertaintySource] = field(default_factory=list)
    combined_uncertainty: float = 0.0
    expanded_uncertainty: float = 0.0
    coverage_factor: float = 2.0
    dominant_source: str = ""

    @property
    def confidence_level(self) -> float:
        """Approximate confidence level for k=2."""
        return 0.9545 if self.coverage_factor == 2.0 else 0.6827


@dataclass
class RRObservation:
    """A single observation in an R&R study."""
    build_id: str
    environment: str
    test_name: str
    replicate: int
    value: float


@dataclass
class RRSummary:
    """Summary of a Gauge R&R study."""
    suite: str
    sigma_part: float = 0.0
    sigma_operator: float = 0.0
    sigma_interaction: float = 0.0
    sigma_equipment: float = 0.0
    sigma_total: float = 0.0
    grr_percent: float = 0.0
    ndc: int = 0
    category: RRCategory = RRCategory.UNACCEPTABLE
    part_variance_pct: float = 0.0
    operator_variance_pct: float = 0.0
    interaction_variance_pct: float = 0.0
    equipment_variance_pct: float = 0.0
    diagnosis: str = ""


@dataclass
class CapabilitySpec:
    """Specification limits for capability analysis."""
    test_name: str
    usl: float  # Upper Specification Limit
    lsl: float  # Lower Specification Limit
    target: Optional[float] = None


@dataclass
class CapabilityResult:
    """Process capability indices for a test."""
    test_name: str
    cp: float = 0.0
    cpk: float = 0.0
    pp: float = 0.0
    ppk: float = 0.0
    mean: float = 0.0
    sigma_within: float = 0.0
    sigma_overall: float = 0.0
    usl: float = 0.0
    lsl: float = 0.0
    capable: bool = False
    diagnosis: str = ""


@dataclass
class FlakinessClassification:
    """Type A vs Type B uncertainty classification for a test."""
    test_name: str
    type_a_uncertainty: float = 0.0
    type_b_uncertainty: float = 0.0
    combined_uncertainty: float = 0.0
    dominant_type: UncertaintyType = UncertaintyType.TYPE_A
    correlation_ab: float = 0.0
    remediation: str = ""
    cross_env_failure_rate: float = 0.0
    single_env_failure_rate: float = 0.0


@dataclass
class DriftObservation:
    """A single observation for drift analysis."""
    test_name: str
    timestamp: datetime
    observed_value: float


@dataclass
class DriftResult:
    """Drift analysis result for a test."""
    test_name: str
    drift_rate: float = 0.0  # alpha
    initial_bias: float = 0.0  # d_0
    cumulative_drift: float = 0.0
    mpe: float = 0.0  # Maximum Permissible Error
    exceeds_mpe: bool = False
    is_zombie: bool = False
    shock_events: List[datetime] = field(default_factory=list)
    cusum_alerts: List[int] = field(default_factory=list)
    recalibration_interval_days: float = 0.0
    diagnosis: str = ""


@dataclass
class TraceabilityLink:
    """A single link in the traceability chain."""
    test_name: str
    level: str  # stakeholder_need, specification, acceptance_criteria, test_plan, assertion
    reference: str  # ID or name of the requirement artifact
    uncertainty: float  # ambiguity at this link
    last_verified: Optional[datetime] = None
    review_interval_days: int = 365


@dataclass
class TraceabilityResult:
    """Traceability chain analysis for a test."""
    test_name: str
    chain: List[TraceabilityLink] = field(default_factory=list)
    chain_uncertainty: float = 0.0
    is_orphan: bool = False
    has_stale_links: bool = False
    integrity_score: float = 0.0
    stale_links: List[str] = field(default_factory=list)
    diagnosis: str = ""
