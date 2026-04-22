"""Data models for Fatigue."""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Optional


class CrackType(Enum):
    """Types of cracks detectable in code."""
    TODO_FIXME_HACK = "TODO/FIXME/HACK"
    HIGH_COMPLEXITY = "High complexity"
    MISSING_ERROR_HANDLING = "Missing error handling"
    CIRCULAR_DEPENDENCY = "Circular dependency"
    GOD_CLASS = "God class"


class TrendDirection(Enum):
    """Trend direction for crack severity."""
    DECLINING = "declining"
    STABLE = "stable"
    GROWING = "growing"
    GROWING_FAST = "growing fast"


class ModuleStatus(Enum):
    """Status of a module based on its stress intensity."""
    STABLE = "STABLE"
    GROWING = "GROWING"
    CRITICAL = "CRITICAL"
    CATASTROPHIC = "CATASTROPHIC"


@dataclasses.dataclass
class Crack:
    """A detected crack (flaw) in code."""
    crack_type: CrackType
    file_path: str
    line_number: int
    severity: float  # 0-10 scale
    description: str
    details: str = ""


@dataclasses.dataclass
class ModuleMetrics:
    """Metrics for a single module/file."""
    file_path: str
    coupling: float = 0.0         # fan-in + fan-out weighted by depth
    churn_rate: float = 0.0       # commits per week
    complexity: float = 0.0       # cyclomatic complexity normalized by LOC
    test_coverage: float = 0.0    # ratio 0-1
    lines_of_code: int = 0
    cyclomatic_complexity: int = 0
    num_methods: int = 0
    fan_in: int = 0
    fan_out: int = 0
    nesting_depth: int = 0


@dataclasses.dataclass
class StressIntensity:
    """Stress intensity calculation result for a module."""
    file_path: str
    K: float                      # stress intensity factor
    delta_K: float = 0.0          # change in K between measurements
    coupling_component: float = 0.0
    churn_component: float = 0.0
    complexity_component: float = 0.0
    coverage_component: float = 0.0


@dataclasses.dataclass
class MaterialConstants:
    """Paris' Law material constants for a codebase or module."""
    C: float = 0.015    # crack growth coefficient
    m: float = 2.5      # stress exponent
    K_Ic: float = 28.0  # fracture toughness
    K_e: float = 8.2    # endurance limit
    r_squared: float = 0.0  # model fit quality


@dataclasses.dataclass
class DecayPrediction:
    """Prediction result for a module's decay trajectory."""
    file_path: str
    current_debt: float
    current_K: float
    growth_rate: float          # da/dN
    cycles_per_week: float
    status: ModuleStatus
    time_to_critical_cycles: Optional[float] = None
    time_to_critical_weeks: Optional[float] = None
    time_to_critical_sprints: Optional[float] = None
    trajectory: list[tuple[int, float]] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class WhatIfScenario:
    """Result of a what-if intervention analysis."""
    file_path: str
    intervention: str
    intervention_sprint: int
    without_debt_at_horizon: float
    with_debt_at_horizon: float
    debt_prevented: float
    without_K_at_horizon: float
    with_K_at_horizon: float
    without_status: ModuleStatus
    with_status: ModuleStatus
    roi_description: str = ""


@dataclasses.dataclass
class CrackArrestStrategy:
    """A recommended intervention to arrest crack growth."""
    name: str
    description: str
    K_reduction: float
    impact: str  # "HIGH", "MED", "LOW"


@dataclasses.dataclass
class ScanResult:
    """Result of a full scan operation."""
    cracks: list[Crack]
    modules: dict[str, ModuleMetrics]
    stress_intensities: dict[str, StressIntensity]
    critical_cracks: list[tuple[Crack, StressIntensity]]
