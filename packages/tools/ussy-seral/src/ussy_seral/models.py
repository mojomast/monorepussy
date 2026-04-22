"""Data models for Seral."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


class Stage(enum.Enum):
    """Ecological successional stages for code modules."""

    PIONEER = "pioneer"
    SERAL_EARLY = "seral_early"
    SERAL_MID = "seral_mid"
    SERAL_LATE = "seral_late"
    CLIMAX = "climax"
    DISTURBED = "disturbed"

    @property
    def emoji(self) -> str:
        _map = {
            Stage.PIONEER: "🌱",
            Stage.SERAL_EARLY: "🌿",
            Stage.SERAL_MID: "🌿🌿",
            Stage.SERAL_LATE: "🌳",
            Stage.CLIMAX: "🌳",
            Stage.DISTURBED: "🔥",
        }
        return _map.get(self, "❓")

    @property
    def display_name(self) -> str:
        _map = {
            Stage.PIONEER: "PIONEER",
            Stage.SERAL_EARLY: "SERAL (early)",
            Stage.SERAL_MID: "SERAL (mid)",
            Stage.SERAL_LATE: "SERAL (late)",
            Stage.CLIMAX: "CLIMAX",
            Stage.DISTURBED: "DISTURBED",
        }
        return _map.get(self, self.value)

    @property
    def seral_tier(self) -> int:
        """Return a numeric tier for comparison (higher = more mature)."""
        _tiers = {
            Stage.PIONEER: 0,
            Stage.SERAL_EARLY: 1,
            Stage.SERAL_MID: 2,
            Stage.SERAL_LATE: 3,
            Stage.CLIMAX: 4,
            Stage.DISTURBED: -1,
        }
        return _tiers.get(self, 0)

    @classmethod
    def from_string(cls, s: str) -> "Stage":
        """Parse a stage from a string (case-insensitive, flexible)."""
        mapping = {
            "pioneer": cls.PIONEER,
            "seral_early": cls.SERAL_EARLY,
            "seral-early": cls.SERAL_EARLY,
            "seral early": cls.SERAL_EARLY,
            "seral_mid": cls.SERAL_MID,
            "seral-mid": cls.SERAL_MID,
            "seral mid": cls.SERAL_MID,
            "seral_late": cls.SERAL_LATE,
            "seral-late": cls.SERAL_LATE,
            "seral late": cls.SERAL_LATE,
            "seral": cls.SERAL_MID,  # default seral -> mid
            "climax": cls.CLIMAX,
            "disturbed": cls.DISTURBED,
        }
        key = s.strip().lower()
        if key not in mapping:
            raise ValueError(f"Unknown stage: {s!r}. Valid: {list(mapping.keys())}")
        return mapping[key]


@dataclass
class ModuleMetrics:
    """Git-derived metrics for a single module."""

    path: str
    age_days: float = 0.0
    commit_count: int = 0
    contributor_count: int = 0
    churn_rate: float = 0.0  # lines changed per week
    test_coverage: float = 0.0  # 0.0–1.0
    dependent_count: int = 0
    file_count: int = 0
    file_type_diversity: int = 0
    deletion_ratio: float = 0.0  # fraction of files deleted recently
    contributor_spike: float = 0.0  # z-score of recent contributor change
    churn_spike: float = 0.0  # z-score of recent churn change
    breaking_change_count: int = 0  # breaking changes in last 60 days
    stage: Optional[Stage] = None

    def compute_stage(self) -> Stage:
        """Compute the successional stage from metrics using weighted scoring."""
        # Check for disturbance first
        if self.deletion_ratio > 0.4 or self.contributor_spike > 2.5 or self.churn_spike > 3.0:
            self.stage = Stage.DISTURBED
            return self.stage

        # Weighted scoring: age, churn, contributors, coverage, dependents
        score = 0.0

        # Age contribution (0-25 points)
        if self.age_days < 30:
            score += 0
        elif self.age_days < 90:
            score += 5
        elif self.age_days < 180:
            score += 10
        elif self.age_days < 365:
            score += 15
        elif self.age_days < 730:
            score += 20
        else:
            score += 25

        # Churn rate contribution (0-20 points, inverted — low churn = mature)
        if self.churn_rate > 100:
            score += 0
        elif self.churn_rate > 50:
            score += 3
        elif self.churn_rate > 20:
            score += 7
        elif self.churn_rate > 5:
            score += 12
        elif self.churn_rate > 1:
            score += 17
        else:
            score += 20

        # Test coverage contribution (0-20 points)
        score += min(self.test_coverage * 20, 20)

        # Contributor count (0-20 points)
        if self.contributor_count <= 1:
            score += 0
        elif self.contributor_count <= 3:
            score += 5
        elif self.contributor_count <= 5:
            score += 10
        elif self.contributor_count <= 10:
            score += 15
        else:
            score += 20

        # Dependent count (0-15 points)
        if self.dependent_count == 0:
            score += 0
        elif self.dependent_count <= 3:
            score += 3
        elif self.dependent_count <= 10:
            score += 7
        elif self.dependent_count <= 20:
            score += 11
        else:
            score += 15

        # Classify based on total score (0-100)
        if score < 15:
            self.stage = Stage.PIONEER
        elif score < 30:
            self.stage = Stage.SERAL_EARLY
        elif score < 50:
            self.stage = Stage.SERAL_MID
        elif score < 70:
            self.stage = Stage.SERAL_LATE
        else:
            self.stage = Stage.CLIMAX

        return self.stage


@dataclass
class StageTransition:
    """A recorded transition between stages."""

    path: str
    from_stage: Stage
    to_stage: Stage
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: Optional[ModuleMetrics] = None
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "from_stage": self.from_stage.value,
            "to_stage": self.to_stage.value,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
        }


@dataclass
class GovernanceRule:
    """A single governance rule."""

    category: str  # mandatory, recommended, forbidden
    description: str
    stage: Stage = Stage.PIONEER

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "description": self.description,
            "stage": self.stage.value,
        }


@dataclass
class GovernancePrescription:
    """Full governance prescription for a stage."""

    stage: Stage
    path: str = ""
    mandatory: list[GovernanceRule] = field(default_factory=list)
    recommended: list[GovernanceRule] = field(default_factory=list)
    forbidden: list[GovernanceRule] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.value,
            "path": self.path,
            "mandatory": [r.to_dict() for r in self.mandatory],
            "recommended": [r.to_dict() for r in self.recommended],
            "forbidden": [r.to_dict() for r in self.forbidden],
        }


@dataclass
class DisturbanceEvent:
    """A detected disturbance event."""

    path: str
    event_type: str  # major_deletion, contributor_spike, churn_spike, dependency_reshaping
    date: str = ""
    previous_stage: Optional[Stage] = None
    current_stage: Stage = Stage.DISTURBED
    cause: str = ""
    governance_shift: str = ""

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "event_type": self.event_type,
            "date": self.date,
            "previous_stage": self.previous_stage.value if self.previous_stage else None,
            "current_stage": self.current_stage.value,
            "cause": self.cause,
            "governance_shift": self.governance_shift,
        }


@dataclass
class TimelineEntry:
    """A point on the succession timeline."""

    stage: Stage
    date: str = ""
    metrics: Optional[ModuleMetrics] = None


@dataclass
class TrajectoryProjection:
    """Projected future stage transition."""

    target_stage: Stage
    estimated_time: str = ""
    blockers: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
