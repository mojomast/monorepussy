"""Merged data models for ussy-calibre."""

from __future__ import annotations

import dataclasses
import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


# ==================== calibre models ====================


class TestResult(enum.Enum):
    __test__ = False
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"


class UncertaintyType(enum.Enum):
    TYPE_A = "type_a"
    TYPE_B = "type_b"


class RRCategory(enum.Enum):
    ACCEPTABLE = "acceptable"
    CONDITIONAL = "conditional"
    UNACCEPTABLE = "unacceptable"


@dataclass
class TestRun:
    __test__ = False
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
        return 1.0 if self.passed else 0.0


@dataclass
class UncertaintySource:
    name: str
    uncertainty_value: float
    sensitivity_coefficient: float
    correlation_with: Optional[str] = None
    correlation_coefficient: float = 0.0
    uncertainty_type: Optional[UncertaintyType] = None

    @property
    def contribution(self) -> float:
        return (self.sensitivity_coefficient * self.uncertainty_value) ** 2


@dataclass
class UncertaintyBudget:
    measurand: str
    sources: List[UncertaintySource] = field(default_factory=list)
    combined_uncertainty: float = 0.0
    expanded_uncertainty: float = 0.0
    coverage_factor: float = 2.0
    dominant_source: str = ""

    @property
    def confidence_level(self) -> float:
        return 0.9545 if self.coverage_factor == 2.0 else 0.6827


@dataclass
class RRObservation:
    build_id: str
    environment: str
    test_name: str
    replicate: int
    value: float


@dataclass
class RRSummary:
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
    test_name: str
    usl: float
    lsl: float
    target: Optional[float] = None


@dataclass
class CapabilityResult:
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
    test_name: str
    timestamp: datetime
    observed_value: float


@dataclass
class DriftResult:
    test_name: str
    drift_rate: float = 0.0
    initial_bias: float = 0.0
    cumulative_drift: float = 0.0
    mpe: float = 0.0
    exceeds_mpe: bool = False
    is_zombie: bool = False
    shock_events: List[datetime] = field(default_factory=list)
    cusum_alerts: List[int] = field(default_factory=list)
    recalibration_interval_days: float = 0.0
    diagnosis: str = ""


@dataclass
class TraceabilityLink:
    test_name: str
    level: str
    reference: str
    uncertainty: float
    last_verified: Optional[datetime] = None
    review_interval_days: int = 365


@dataclass
class TraceabilityResult:
    test_name: str
    chain: List[TraceabilityLink] = field(default_factory=list)
    chain_uncertainty: float = 0.0
    is_orphan: bool = False
    has_stale_links: bool = False
    integrity_score: float = 0.0
    stale_links: List[str] = field(default_factory=list)
    diagnosis: str = ""


# ==================== acumen models ====================

COMPLEXITY_BANDS = [
    ("1-5", 1, 5),
    ("6-10", 6, 10),
    ("11-15", 11, 15),
    ("16-20", 16, 20),
    (">20", 21, None),
]


def band_for_complexity(cc: int) -> str:
    for label, lo, hi in COMPLEXITY_BANDS:
        if hi is None:
            if cc >= lo:
                return label
        elif lo <= cc <= hi:
            return label
    return "1-5"


@dataclass
class FunctionInfo:
    name: str
    filepath: str
    lineno: int
    cyclomatic_complexity: int
    complexity_band: str = ""
    is_test: bool = False
    test_type: str = ""

    def __post_init__(self) -> None:
        if not self.complexity_band:
            self.complexity_band = band_for_complexity(self.cyclomatic_complexity)


@dataclass
class ModuleInfo:
    filepath: str
    functions: list[FunctionInfo] = field(default_factory=list)
    avg_complexity: float = 0.0

    def __post_init__(self) -> None:
        if self.functions and not self.avg_complexity:
            self.avg_complexity = sum(f.cyclomatic_complexity for f in self.functions) / len(
                self.functions
            )


@dataclass
class ProjectScan:
    root: str
    source_modules: list[ModuleInfo] = field(default_factory=list)
    test_modules: list[ModuleInfo] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class TestigramPoint:
    __test__ = False
    complexity_band: str
    test_type: str
    detection_threshold: float


@dataclass
class TestigramResult:
    __test__ = False
    points: list[TestigramPoint] = field(default_factory=list)
    pta_unit: float = 0.0
    pta_integration: float = 0.0
    shape: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.points and not self.pta_unit:
            self._compute_pta()

    def _compute_pta(self) -> None:
        core_bands = ["6-10", "11-15", "16-20", ">20"]
        unit_thresholds = [
            p.detection_threshold
            for p in self.points
            if p.test_type == "unit" and p.complexity_band in core_bands
        ]
        int_thresholds = [
            p.detection_threshold
            for p in self.points
            if p.test_type == "integration" and p.complexity_band in core_bands
        ]
        if unit_thresholds:
            self.pta_unit = sum(unit_thresholds) / len(unit_thresholds)
        if int_thresholds:
            self.pta_integration = sum(int_thresholds) / len(int_thresholds)


@dataclass
class SRTCandidate:
    environment_fidelity: float
    pass_rate: float


@dataclass
class SRTResult:
    srt_value: float = 0.0
    candidates: list[SRTCandidate] = field(default_factory=list)
    has_rollover: bool = False
    rollover_point: Optional[float] = None
    word_recognition_scores: list[float] = field(default_factory=list)
    pta_value: float = 0.0
    agreement_delta: float = 0.0
    is_consistent: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class CompanogramPoint:
    config_value: float
    pass_rate: float


@dataclass
class CompanogramResult:
    points: list[CompanogramPoint] = field(default_factory=list)
    peak_type: str = ""
    tolerance_width: float = 0.0
    rigidity_score: float = 0.0
    peak_location: float = 0.0
    peak_pass_rate: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class FlakegramModuleResult:
    module_name: str
    soae_index: float = 0.0
    soae_present: bool = False
    snr_value: float = 0.0
    growth_alpha: float = 0.0
    health_status: str = ""


@dataclass
class FlakegramResult:
    modules: list[FlakegramModuleResult] = field(default_factory=list)
    overall_alpha: float = 0.0
    overall_health: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.modules and not self.overall_alpha:
            self.overall_alpha = sum(m.growth_alpha for m in self.modules) / len(self.modules)
            self._classify_health()

    def _classify_health(self) -> None:
        a = self.overall_alpha
        if a < 0.5:
            self.overall_health = "insensitive"
        elif a > 1.5:
            self.overall_health = "fragile"
        else:
            self.overall_health = "healthy"


@dataclass
class ConductionStage:
    name: str
    stage_type: str
    latency_ms: float
    assertion_count: int
    code_covered_pct: float


@dataclass
class ConductionResult:
    stages: list[ConductionStage] = field(default_factory=list)
    interstage_latencies: list[float] = field(default_factory=list)
    fsp_values: dict[str, float] = field(default_factory=dict)
    vi_ratio: float = 0.0
    bottleneck_stage: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class IsolationSweepPoint:
    isolation_level: int
    pass_rate: float
    assertion_count: int
    code_covered_pct: float


@dataclass
class IsolationModuleResult:
    module_a: str
    module_b: str
    crosstalk: float = 0.0
    attenuation: float = 0.0
    plateau_range: tuple[int, int] = (0, 0)
    is_overmocked: bool = False
    is_undermasked: bool = False
    is_dilemma: bool = False
    sweep_points: list[IsolationSweepPoint] = field(default_factory=list)


@dataclass
class IsolationResult:
    module_results: list[IsolationModuleResult] = field(default_factory=list)
    dilemmas: list[str] = field(default_factory=list)
    overmocked_modules: list[str] = field(default_factory=list)
    undermasked_modules: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class FullDiagnostic:
    project_root: str = ""
    testigram: Optional[TestigramResult] = None
    srt: Optional[SRTResult] = None
    companogram: Optional[CompanogramResult] = None
    flakegram: Optional[FlakegramResult] = None
    conduction: Optional[ConductionResult] = None
    isolation: Optional[IsolationResult] = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


# ==================== lehr models ====================


class GlassType(enum.Enum):
    FUSED_SILICA = "fused_silica"
    BOROSILICATE = "borosilicate"
    SODA_LIME = "soda_lime"
    LEAD_CRYSTAL = "lead_crystal"
    TEMPERED_SODA_LIME = "tempered_soda_lime"

    @property
    def label(self) -> str:
        labels = {
            GlassType.FUSED_SILICA: "Fused Silica",
            GlassType.BOROSILICATE: "Borosilicate",
            GlassType.SODA_LIME: "Soda-Lime",
            GlassType.LEAD_CRYSTAL: "Lead Crystal",
            GlassType.TEMPERED_SODA_LIME: "Tempered Soda-Lime",
        }
        return labels[self]

    @property
    def description(self) -> str:
        descs = {
            GlassType.FUSED_SILICA: "Pure unit test, no I/O, deterministic",
            GlassType.BOROSILICATE: "Unit test with mocks, deterministic with proper setup",
            GlassType.SODA_LIME: "Integration test with controlled dependencies",
            GlassType.LEAD_CRYSTAL: "Integration test with external services, timing-dependent",
            GlassType.TEMPERED_SODA_LIME: "Hardened flaky test — looks stable, shatters catastrophically",
        }
        return descs[self]


class BrittlenessClass(enum.Enum):
    ANNEALED = "annealed"
    TEMPERED = "tempered"
    CRACKED = "cracked"


@dataclass
class EnvironmentCondition:
    os: str = "linux"
    python_version: str = "3.11"
    parallelism: int = 1
    load_level: float = 0.0

    def to_tuple(self) -> tuple:
        return (self.os, self.python_version, self.parallelism, self.load_level)


@dataclass
class TestResultLehr:
    test_name: str = ""
    condition: EnvironmentCondition = field(default_factory=EnvironmentCondition)
    passed: bool = True
    duration_ms: float = 0.0
    retries_used: int = 0
    timeout_used: bool = False


@dataclass
class StressReport:
    test_name: str = ""
    total_stress: float = 0.0
    directional_stress: Dict[str, float] = field(default_factory=dict)
    fringe_order: int = 0
    pass_rates: Dict[str, float] = field(default_factory=dict)

    @property
    def is_stressed(self) -> bool:
        return self.total_stress > 0.1


@dataclass
class CTEProfile:
    test_name: str = ""
    cte_by_dimension: Dict[str, float] = field(default_factory=dict)
    composite_cte: float = 0.0

    @property
    def glass_analogy(self) -> str:
        if self.composite_cte < 0.1:
            return "borosilicate (low expansion)"
        elif self.composite_cte < 0.3:
            return "soda-lime (moderate expansion)"
        else:
            return "lead crystal (high expansion)"


@dataclass
class ShockResistance:
    test_name: str = ""
    resistance_score: float = 0.0
    max_environment_change: float = 0.0
    shock_pass_rate: float = 0.0

    @property
    def is_shock_resistant(self) -> bool:
        return self.resistance_score > 0.5


@dataclass
class AnnealingPhase:
    phase_name: str = ""
    description: str = ""
    duration_steps: int = 0
    environment_changes: List[str] = field(default_factory=list)
    target_pass_rate: float = 0.95


@dataclass
class AnnealingSchedule:
    test_name: str = ""
    phases: List[AnnealingPhase] = field(default_factory=list)
    estimated_total_steps: int = 0
    complexity_factor: float = 1.0


@dataclass
class TemperResult:
    test_name: str = ""
    pass_rate_with_hardening: float = 0.0
    pass_rate_without_hardening: float = 0.0
    brittleness_index: float = 0.0
    brittleness_class: BrittlenessClass = BrittlenessClass.ANNEALED

    @property
    def is_tempered(self) -> bool:
        return self.brittleness_class == BrittlenessClass.TEMPERED


@dataclass
class GlassClassification:
    test_name: str = ""
    glass_type: GlassType = GlassType.BOROSILICATE
    cte: float = 0.0
    shock_resistance: float = 0.0
    brittleness: float = 0.0
    confidence: float = 0.0

    @property
    def recommendation(self) -> str:
        recs = {
            GlassType.FUSED_SILICA: "Safe for any CI environment",
            GlassType.BOROSILICATE: "Safe with version pinning",
            GlassType.SODA_LIME: "Needs controlled environments",
            GlassType.LEAD_CRYSTAL: "Needs isolation and monitoring",
            GlassType.TEMPERED_SODA_LIME: "Needs re-annealing, not more hardening",
        }
        return recs[self.glass_type]


@dataclass
class SuiteReport:
    suite_name: str = ""
    tests: List[TestResultLehr] = field(default_factory=list)
    stress_reports: Dict[str, StressReport] = field(default_factory=dict)
    cte_profiles: Dict[str, CTEProfile] = field(default_factory=dict)
    shock_resistances: Dict[str, ShockResistance] = field(default_factory=dict)
    annealing_schedules: Dict[str, AnnealingSchedule] = field(default_factory=dict)
    temper_results: Dict[str, TemperResult] = field(default_factory=dict)
    glass_classifications: Dict[str, GlassClassification] = field(default_factory=dict)

    @property
    def glass_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for gc in self.glass_classifications.values():
            key = gc.glass_type.label
            dist[key] = dist.get(key, 0) + 1
        return dist

    @property
    def suite_health(self) -> float:
        if not self.glass_classifications:
            return 0.0
        scores = {
            GlassType.FUSED_SILICA: 1.0,
            GlassType.BOROSILICATE: 0.8,
            GlassType.SODA_LIME: 0.5,
            GlassType.LEAD_CRYSTAL: 0.2,
            GlassType.TEMPERED_SODA_LIME: 0.1,
        }
        total = sum(scores.get(gc.glass_type, 0.0) for gc in self.glass_classifications.values())
        return total / len(self.glass_classifications)

    @property
    def tempered_count(self) -> int:
        return sum(1 for tr in self.temper_results.values() if tr.is_tempered)


# ==================== marksman models ====================


class TestOutcomeMarksman(str, enum.Enum):
    __test__ = False
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class MaturityClass(str, enum.Enum):
    FRAGILE = "fragile"
    UNSTABLE = "unstable"
    MATURING = "maturing"
    STABLE = "stable"
    ROBUST = "robust"


class TMOAClass(str, enum.Enum):
    ELITE = "elite"
    COMPETITION = "competition"
    SERVICEABLE = "serviceable"
    SUB_MOA = "sub-moa"


class BiasDirection(str, enum.Enum):
    FP_HEAVY = "fp_heavy"
    FN_HEAVY = "fn_heavy"
    BALANCED = "balanced"


class EllipseShape(str, enum.Enum):
    ROUND = "round"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    TILTED = "tilted"


@dataclass
class TestExecution:
    __test__ = False
    test_name: str
    outcome: TestOutcomeMarksman
    timestamp: datetime
    suite: str = ""
    is_false_positive: bool = False
    is_false_negative: bool = False
    run_id: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.outcome, str):
            self.outcome = TestOutcomeMarksman(self.outcome)
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class GroupingResult:
    test_name: str
    sigma_fp: float = 0.0
    sigma_fn: float = 0.0
    sigma_t: float = 0.0
    cep_t: float = 0.0
    mean_radius: float = 0.0
    n_runs: int = 0

    def __post_init__(self) -> None:
        self.sigma_t = math.sqrt(self.sigma_fp**2 + self.sigma_fn**2)
        self.cep_t = 1.1774 * self.sigma_t
        self.mean_radius = math.sqrt(math.pi / 2) * self.sigma_t


@dataclass
class DispersionResult:
    test_name: str
    sigma_fp: float = 0.0
    sigma_fn: float = 0.0
    covariance: float = 0.0
    eigenvalue_1: float = 0.0
    eigenvalue_2: float = 0.0
    eigenvector_1: tuple[float, float] = (1.0, 0.0)
    eigenvector_2: tuple[float, float] = (0.0, 1.0)
    tilt_angle_deg: float = 0.0
    shape: EllipseShape = EllipseShape.ROUND
    aspect_ratio: float = 1.0

    def __post_init__(self) -> None:
        if self.sigma_fp == 0.0 and self.sigma_fn == 0.0:
            self.eigenvalue_1 = 0.0
            self.eigenvalue_2 = 0.0
            self.eigenvector_1 = (1.0, 0.0)
            self.eigenvector_2 = (0.0, 1.0)
            self.tilt_angle_deg = 0.0
            self.shape = EllipseShape.ROUND
            self.aspect_ratio = 1.0
            return

        var_fp = self.sigma_fp**2
        var_fn = self.sigma_fn**2
        cov = self.covariance

        trace = var_fp + var_fn
        det = var_fp * var_fn - cov**2
        discriminant = max(trace**2 - 4 * det, 0.0)
        sqrt_disc = math.sqrt(discriminant)

        self.eigenvalue_1 = (trace + sqrt_disc) / 2
        self.eigenvalue_2 = max((trace - sqrt_disc) / 2, 0.0)

        if abs(cov) > 1e-12:
            ev1_x = self.eigenvalue_1 - var_fn
            ev1_y = cov
            norm = math.sqrt(ev1_x**2 + ev1_y**2)
            if norm > 0:
                self.eigenvector_1 = (ev1_x / norm, ev1_y / norm)
                self.eigenvector_2 = (-ev1_y / norm, ev1_x / norm)
        else:
            if var_fp >= var_fn:
                self.eigenvector_1 = (1.0, 0.0)
                self.eigenvector_2 = (0.0, 1.0)
            else:
                self.eigenvector_1 = (0.0, 1.0)
                self.eigenvector_2 = (1.0, 0.0)

        self.tilt_angle_deg = math.degrees(math.atan2(self.eigenvector_1[1], self.eigenvector_1[0]))

        if self.eigenvalue_2 > 1e-12:
            self.aspect_ratio = self.eigenvalue_1 / self.eigenvalue_2
        else:
            self.aspect_ratio = float("inf")

        abs_cov = abs(self.covariance)
        max_var = max(var_fp, var_fn, 1e-12)
        covariance_ratio = abs_cov / max_var

        if covariance_ratio > 0.3:
            self.shape = EllipseShape.TILTED
        elif self.aspect_ratio > 2.0:
            if self.sigma_fp > self.sigma_fn:
                self.shape = EllipseShape.HORIZONTAL
            else:
                self.shape = EllipseShape.VERTICAL
        else:
            self.shape = EllipseShape.ROUND


@dataclass
class TMOAResult:
    project: str
    sigma_t: float = 0.0
    n_dependencies: int = 1
    tmoa_deg: float = 0.0
    classification: TMOAClass = TMOAClass.SERVICEABLE

    def __post_init__(self) -> None:
        if self.n_dependencies < 1:
            self.n_dependencies = 1
        self.tmoa_deg = math.degrees(math.atan(self.sigma_t / math.sqrt(self.n_dependencies)))
        if self.tmoa_deg < 0.5:
            self.classification = TMOAClass.ELITE
        elif self.tmoa_deg < 1.5:
            self.classification = TMOAClass.COMPETITION
        elif self.tmoa_deg < 3.0:
            self.classification = TMOAClass.SERVICEABLE
        else:
            self.classification = TMOAClass.SUB_MOA


@dataclass
class BCResult:
    k: float = 0.5
    sigma_consistency: float = 0.0
    scales: list[float] = field(default_factory=list)
    predicted_sigmas: list[float] = field(default_factory=list)
    bc_classification: str = "medium"

    def __post_init__(self) -> None:
        if not self.scales:
            self.scales = [1, 5, 10, 20]
        self.predicted_sigmas = [s**self.k * self.sigma_consistency for s in self.scales]
        if self.k <= 0.35:
            self.bc_classification = "high"
        elif self.k <= 0.65:
            self.bc_classification = "medium"
        else:
            self.bc_classification = "low"


@dataclass
class WeibullResult:
    suite: str
    beta: float = 1.0
    eta: float = 1.0
    maturity: MaturityClass = MaturityClass.UNSTABLE
    n_failures: int = 0

    def __post_init__(self) -> None:
        if self.beta < 0.8:
            self.maturity = MaturityClass.FRAGILE
        elif self.beta < 1.2:
            self.maturity = MaturityClass.UNSTABLE
        elif self.beta < 2.0:
            self.maturity = MaturityClass.MATURING
        elif self.beta < 3.0:
            self.maturity = MaturityClass.STABLE
        else:
            self.maturity = MaturityClass.ROBUST


@dataclass
class CalibrationClick:
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    direction: BiasDirection = BiasDirection.BALANCED
    clicks: int = 0
    description: str = ""
    expected_fp_change: float = 0.0
    expected_fn_change: float = 0.0
    actual_fp_change: float | None = None
    actual_fn_change: float | None = None
    verified: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class CalibrationResult:
    suite: str
    current_fp_rate: float = 0.0
    current_fn_rate: float = 0.0
    bias_direction: BiasDirection = BiasDirection.BALANCED
    target_cep: float = 0.05
    required_fp_correction: float = 0.0
    required_fn_correction: float = 0.0
    clicks: list[CalibrationClick] = field(default_factory=list)
    calibration_accuracy: float | None = None

    def __post_init__(self) -> None:
        if self.current_fp_rate > self.current_fn_rate * 1.5:
            self.bias_direction = BiasDirection.FP_HEAVY
        elif self.current_fn_rate > self.current_fp_rate * 1.5:
            self.bias_direction = BiasDirection.FN_HEAVY
        else:
            self.bias_direction = BiasDirection.BALANCED
        self.required_fp_correction = self.current_fp_rate
        self.required_fn_correction = self.current_fn_rate


# ==================== levain models ====================


class TestOutcomeLevain(enum.Enum):
    __test__ = False
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    XFAIL = "xfail"
    ERROR = "error"


class HoochType(enum.Enum):
    DEAD = "dead"
    STALE = "stale"
    DORMANT = "dormant"


class RiseClassification(enum.Enum):
    HEALTHY = "healthy"
    FLAT = "flat"
    CHAOTIC = "chaotic"
    SEASONAL = "seasonal"


class ThermalTolerance(enum.Enum):
    THERMOPHILIC = "thermophilic"
    MESOPHILIC = "mesophilic"
    PSYCHROPHILIC = "psychrophilic"


@dataclasses.dataclass
class TestResultLevain:
    __test__ = False
    test_id: str
    name: str
    module: str
    outcome: TestOutcomeLevain
    duration: float
    timestamp: datetime
    message: str = ""
    filepath: str = ""
    lineno: int = 0

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "module": self.module,
            "outcome": self.outcome.value,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "filepath": self.filepath,
            "lineno": self.lineno,
        }


@dataclasses.dataclass
class HoochResult:
    test_id: str
    name: str
    module: str
    hooch_type: HoochType
    confidence: float
    reason: str
    last_failed_days_ago: Optional[int] = None
    assertion_quality: Optional[float] = None
    skip_duration_days: Optional[float] = None

    def to_dict(self) -> dict:
        d = {
            "test_id": self.test_id,
            "name": self.name,
            "module": self.module,
            "hooch_type": self.hooch_type.value,
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
        }
        if self.last_failed_days_ago is not None:
            d["last_failed_days_ago"] = self.last_failed_days_ago
        if self.assertion_quality is not None:
            d["assertion_quality"] = round(self.assertion_quality, 3)
        if self.skip_duration_days is not None:
            d["skip_duration_days"] = round(self.skip_duration_days, 1)
        return d


@dataclasses.dataclass
class HoochReport:
    module_hooch_index: dict[str, float]
    total_tests: int
    hooch_tests: list[HoochResult]
    overall_hooch_index: float

    def to_dict(self) -> dict:
        return {
            "module_hooch_index": {k: round(v, 1) for k, v in self.module_hooch_index.items()},
            "total_tests": self.total_tests,
            "hooch_count": len(self.hooch_tests),
            "overall_hooch_index": round(self.overall_hooch_index, 1),
            "hooch_tests": [h.to_dict() for h in self.hooch_tests],
        }


@dataclasses.dataclass
class RiseResult:
    rise_score: float
    classification: RiseClassification
    failure_rate: float
    pattern_description: str
    peak_timing: Optional[str] = None
    failure_positions: Optional[list[int]] = None

    def to_dict(self) -> dict:
        return {
            "rise_score": round(self.rise_score, 1),
            "classification": self.classification.value,
            "failure_rate": round(self.failure_rate, 4),
            "pattern_description": self.pattern_description,
            "peak_timing": self.peak_timing,
            "failure_positions": self.failure_positions,
        }


@dataclasses.dataclass
class ContaminationNode:
    test_id: str
    name: str
    module: str
    is_flaky: bool
    r0: float
    infection_sources: list[str]
    infected_targets: list[str]

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "module": self.module,
            "is_flaky": self.is_flaky,
            "r0": round(self.r0, 3),
            "infection_sources": self.infection_sources,
            "infected_targets": self.infected_targets,
        }


@dataclasses.dataclass
class ContaminationReport:
    patient_zero: Optional[str]
    nodes: list[ContaminationNode]
    quarantine_plan: list[str]
    inoculation_suggestions: list[str]
    overall_r0: float

    def to_dict(self) -> dict:
        return {
            "patient_zero": self.patient_zero,
            "nodes": [n.to_dict() for n in self.nodes],
            "quarantine_plan": self.quarantine_plan,
            "inoculation_suggestions": self.inoculation_suggestions,
            "overall_r0": round(self.overall_r0, 3),
        }


@dataclasses.dataclass
class FeedingResult:
    module: str
    last_fed_days_ago: float
    code_changes_since_feed: int
    feeding_adherence: float
    status: str
    recommended_interval_days: float

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "last_fed_days_ago": round(self.last_fed_days_ago, 1),
            "code_changes_since_feed": self.code_changes_since_feed,
            "feeding_adherence": round(self.feeding_adherence, 3),
            "status": self.status,
            "recommended_interval_days": round(self.recommended_interval_days, 1),
        }


@dataclasses.dataclass
class FeedingReport:
    modules: list[FeedingResult]
    overall_adherence: float
    starving_modules: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        return {
            "modules": [m.to_dict() for m in self.modules],
            "overall_adherence": round(self.overall_adherence, 3),
            "starving_modules": self.starving_modules,
            "warnings": self.warnings,
        }


@dataclasses.dataclass
class BuildResult:
    selected_tests: list[str]
    estimated_confidence: float
    proofing_time_seconds: float
    change_scope: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "selected_tests": self.selected_tests,
            "estimated_confidence": round(self.estimated_confidence, 3),
            "proofing_time_seconds": round(self.proofing_time_seconds, 1),
            "change_scope": self.change_scope,
            "test_count": len(self.selected_tests),
        }


@dataclasses.dataclass
class ThermalProfile:
    test_id: str
    name: str
    tolerance: ThermalTolerance
    environment_correlations: dict[str, float]
    sensitivity_factors: list[str]

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "tolerance": self.tolerance.value,
            "environment_correlations": {
                k: round(v, 3) for k, v in self.environment_correlations.items()
            },
            "sensitivity_factors": self.sensitivity_factors,
        }


@dataclasses.dataclass
class ThermalReport:
    profiles: list[ThermalProfile]
    climate_control_suggestions: list[str]
    environment_summary: dict[str, str]

    def to_dict(self) -> dict:
        return {
            "profiles": [p.to_dict() for p in self.profiles],
            "climate_control_suggestions": self.climate_control_suggestions,
            "environment_summary": self.environment_summary,
        }


@dataclasses.dataclass
class HealthReport:
    hooch: HoochReport
    rise: RiseResult
    contamination: ContaminationReport
    feeding: FeedingReport
    overall_health: float
    diagnosis: str

    def to_dict(self) -> dict:
        return {
            "hooch": self.hooch.to_dict(),
            "rise": self.rise.to_dict(),
            "contamination": self.contamination.to_dict(),
            "feeding": self.feeding.to_dict(),
            "overall_health": round(self.overall_health, 1),
            "diagnosis": self.diagnosis,
        }
