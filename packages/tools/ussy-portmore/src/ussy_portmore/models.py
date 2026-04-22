"""Core data models for Portmore license classification."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ── Enumerations ──────────────────────────────────────────────────────────────

class LicenseFamily(Enum):
    PERMISSIVE = "01"
    WEAK_COPYLEFT = "02"
    STRONG_COPYLEFT = "03"
    PROPRIETARY = "04"
    PUBLIC_DOMAIN = "05"


class DependencyZone(Enum):
    BONDED = "bonded"       # dev/build-only
    DOMESTIC = "domestic"   # runtime


class WithdrawalType(Enum):
    EXPORT = "export"       # removed from production
    DOMESTIC = "domestic"   # included in runtime


class OriginStatus(Enum):
    WHOLLY_OBTAINED = "wholly_obtained"
    SUBSTANTIALLY_TRANSFORMED = "substantially_transformed"
    NON_ORIGINATING = "non_originating"


class CompatibilityStatus(Enum):
    COMPATIBLE = "compatible"
    CONDITIONAL = "conditional"
    INCOMPATIBLE = "incompatible"


class ValuationMethod(Enum):
    TRANSACTION = 1
    IDENTICAL = 2
    SIMILAR = 3
    DEDUCTIVE = 4
    COMPUTED = 5
    FALLBACK = 6


class InjuryIndicator(Enum):
    LOST_LICENSING_OPTIONS = "lost_licensing_options"
    FORCED_CODE_DISCLOSURE = "forced_code_disclosure"
    COMPETITIVE_DISADVANTAGE = "competitive_disadvantage"


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class HSCode:
    """Harmonized System code for license classification."""
    chapter: str       # 2-digit family
    heading: str       # 4-digit type
    subheading: str    # 6-digit variant
    description: str
    family: LicenseFamily

    @property
    def code(self) -> str:
        return f"{self.chapter}.{self.heading[2:]}.{self.subheading[4:]}"

    def __str__(self) -> str:
        return f"HS {self.code} — {self.description}"


@dataclass
class LicenseObligation:
    """A single obligation imposed by a license."""
    name: str
    cost: float = 0.0
    description: str = ""

    __test__ = False


@dataclass
class ClassifiedLicense:
    """Result of GIR classification."""
    spdx_id: str
    hs_code: HSCode
    gir_applied: str
    reasoning: str
    confidence: float = 1.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class GIRResult:
    """Result of applying one General Interpretative Rule."""
    rule: str
    description: str
    applied: bool
    outcome: str = ""


@dataclass
class MultiLicenseResolution:
    """Full resolution of a multi-license work via GIRs."""
    licenses_found: list[str]
    gir_results: list[GIRResult]
    governing_license: str
    governing_hs_code: str = ""
    reasoning_chain: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class OriginDetermination:
    """Per-module origin status determination."""
    module: str
    status: OriginStatus
    wholly_obtained: bool
    ct_classification_changed: bool
    value_added_ratio: float
    de_minimis_ratio: float
    accumulation_applied: bool
    absorption_applied: bool
    threshold: float = 0.40
    deminimis_threshold: float = 0.05
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class CompatibilityRule:
    """A single compatibility exception rule (PTA analog)."""
    from_license: str
    to_license: str
    status: CompatibilityStatus
    condition: str = ""
    quota_limit: int = 0
    zone_from: str = ""
    zone_to: str = ""

    __test__ = False


@dataclass
class CompatibilityResult:
    """Result of compatibility analysis."""
    from_license: str
    to_license: str
    status: CompatibilityStatus
    conditions: list[str]
    quota_remaining: int = 0
    anti_circumvention_flag: bool = False
    rules_applied: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class ValuationResult:
    """Result of compliance value assessment."""
    method: ValuationMethod
    value: float
    currency: str = "USD"
    obligations: list[LicenseObligation] = field(default_factory=list)
    article8_adjustments: float = 0.0
    related_party_adjustment: float = 0.0
    reasoning: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class ValuationHierarchy:
    """Full 6-method sequential valuation."""
    results: list[ValuationResult] = field(default_factory=list)
    final_value: float = 0.0
    final_method: ValuationMethod = ValuationMethod.TRANSACTION
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class ContagionAssessment:
    """Copyleft contagion / anti-dumping assessment."""
    license_id: str
    dumping_margin: float
    copyleft_ratio: float
    within_duty_order: bool
    injury_indicators: list[InjuryIndicator]
    causal_link_established: bool
    lesser_duty_remedy: str
    scope_ruling: str = ""
    threshold: float = 0.60
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class QuarantineEntry:
    """Single dependency in quarantine registry."""
    dependency: str
    zone: DependencyZone
    legal_status: str
    obligations: list[str]
    withdrawal_type: WithdrawalType | None = None
    manipulation_warning: bool = False
    constructive_warehouse: bool = False
    in_bond_movement: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class QuarantineReport:
    """Full quarantine report for a project."""
    entries: list[QuarantineEntry] = field(default_factory=list)
    boundary_violations: list[str] = field(default_factory=list)
    manipulation_warnings: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class ProjectInfo:
    """Basic project information extracted from project directory."""
    name: str
    path: str
    licenses: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    dev_dependencies: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
