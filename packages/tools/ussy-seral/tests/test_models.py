"""Tests for data models."""

from datetime import datetime, timezone

import pytest

from ussy_seral.models import (
    DisturbanceEvent,
    GovernancePrescription,
    GovernanceRule,
    ModuleMetrics,
    Stage,
    StageTransition,
    TimelineEntry,
    TrajectoryProjection,
)


class TestStage:
    """Tests for Stage enum."""

    def test_stage_values(self):
        assert Stage.PIONEER.value == "pioneer"
        assert Stage.SERAL_EARLY.value == "seral_early"
        assert Stage.SERAL_MID.value == "seral_mid"
        assert Stage.SERAL_LATE.value == "seral_late"
        assert Stage.CLIMAX.value == "climax"
        assert Stage.DISTURBED.value == "disturbed"

    def test_stage_emoji(self):
        assert Stage.PIONEER.emoji == "🌱"
        assert Stage.CLIMAX.emoji == "🌳"
        assert Stage.DISTURBED.emoji == "🔥"
        assert Stage.SERAL_MID.emoji == "🌿🌿"

    def test_stage_display_name(self):
        assert Stage.PIONEER.display_name == "PIONEER"
        assert Stage.SERAL_MID.display_name == "SERAL (mid)"
        assert Stage.CLIMAX.display_name == "CLIMAX"
        assert Stage.DISTURBED.display_name == "DISTURBED"

    def test_stage_seral_tier(self):
        assert Stage.PIONEER.seral_tier == 0
        assert Stage.SERAL_EARLY.seral_tier == 1
        assert Stage.SERAL_MID.seral_tier == 2
        assert Stage.SERAL_LATE.seral_tier == 3
        assert Stage.CLIMAX.seral_tier == 4
        assert Stage.DISTURBED.seral_tier == -1

    def test_from_string_pioneer(self):
        assert Stage.from_string("pioneer") == Stage.PIONEER

    def test_from_string_climax(self):
        assert Stage.from_string("climax") == Stage.CLIMAX

    def test_from_string_seral_mid_variants(self):
        assert Stage.from_string("seral_mid") == Stage.SERAL_MID
        assert Stage.from_string("seral-mid") == Stage.SERAL_MID
        assert Stage.from_string("seral mid") == Stage.SERAL_MID

    def test_from_string_seral_defaults_to_mid(self):
        assert Stage.from_string("seral") == Stage.SERAL_MID

    def test_from_string_case_insensitive(self):
        assert Stage.from_string("PIONEER") == Stage.PIONEER
        assert Stage.from_string("Climax") == Stage.CLIMAX

    def test_from_string_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown stage"):
            Stage.from_string("nonexistent")

    def test_from_string_whitespace_trimmed(self):
        assert Stage.from_string("  pioneer  ") == Stage.PIONEER


class TestModuleMetrics:
    """Tests for ModuleMetrics."""

    def test_compute_stage_pioneer(self):
        m = ModuleMetrics(
            path="src/new",
            age_days=10,
            commit_count=3,
            contributor_count=1,
            churn_rate=200.0,
            test_coverage=0.0,
            dependent_count=0,
        )
        stage = m.compute_stage()
        assert stage == Stage.PIONEER

    def test_compute_stage_climax(self):
        m = ModuleMetrics(
            path="src/auth",
            age_days=800,
            commit_count=400,
            contributor_count=12,
            churn_rate=2.0,
            test_coverage=0.95,
            dependent_count=25,
        )
        stage = m.compute_stage()
        assert stage == Stage.CLIMAX

    def test_compute_stage_seral_mid(self):
        m = ModuleMetrics(
            path="src/payments",
            age_days=200,
            commit_count=80,
            contributor_count=4,
            churn_rate=40.0,
            test_coverage=0.6,
            dependent_count=3,
        )
        stage = m.compute_stage()
        assert stage in (Stage.SERAL_EARLY, Stage.SERAL_MID, Stage.SERAL_LATE)

    def test_compute_stage_disturbed_by_deletion(self):
        m = ModuleMetrics(
            path="src/legacy",
            age_days=1000,
            deletion_ratio=0.5,
            commit_count=100,
            contributor_count=5,
            churn_rate=10.0,
            test_coverage=0.8,
            dependent_count=10,
        )
        stage = m.compute_stage()
        assert stage == Stage.DISTURBED

    def test_compute_stage_disturbed_by_contributor_spike(self):
        m = ModuleMetrics(
            path="src/team",
            age_days=500,
            contributor_spike=3.0,
            commit_count=50,
            contributor_count=9,
            churn_rate=20.0,
            test_coverage=0.5,
            dependent_count=5,
        )
        stage = m.compute_stage()
        assert stage == Stage.DISTURBED

    def test_compute_stage_disturbed_by_churn_spike(self):
        m = ModuleMetrics(
            path="src/hot",
            age_days=300,
            churn_spike=4.0,
            commit_count=30,
            contributor_count=3,
            churn_rate=30.0,
            test_coverage=0.4,
            dependent_count=2,
        )
        stage = m.compute_stage()
        assert stage == Stage.DISTURBED

    def test_compute_stage_seral_early(self):
        m = ModuleMetrics(
            path="src/growing",
            age_days=60,
            commit_count=15,
            contributor_count=2,
            churn_rate=80.0,
            test_coverage=0.1,
            dependent_count=1,
        )
        stage = m.compute_stage()
        assert stage in (Stage.PIONEER, Stage.SERAL_EARLY)

    def test_default_values(self):
        m = ModuleMetrics(path="test")
        assert m.age_days == 0.0
        assert m.commit_count == 0
        assert m.contributor_count == 0
        assert m.churn_rate == 0.0
        assert m.test_coverage == 0.0
        assert m.stage is None

    def test_stage_set_after_compute(self):
        m = ModuleMetrics(path="test")
        assert m.stage is None
        m.compute_stage()
        assert m.stage is not None


class TestStageTransition:
    """Tests for StageTransition."""

    def test_to_dict(self):
        t = StageTransition(
            path="src/mod",
            from_stage=Stage.PIONEER,
            to_stage=Stage.SERAL_MID,
            reason="Growing module",
        )
        d = t.to_dict()
        assert d["path"] == "src/mod"
        assert d["from_stage"] == "pioneer"
        assert d["to_stage"] == "seral_mid"
        assert d["reason"] == "Growing module"
        assert "timestamp" in d

    def test_default_timestamp_is_utc(self):
        t = StageTransition(
            path="test",
            from_stage=Stage.PIONEER,
            to_stage=Stage.CLIMAX,
        )
        assert t.timestamp.tzinfo is not None


class TestGovernanceRule:
    """Tests for GovernanceRule."""

    def test_to_dict(self):
        r = GovernanceRule(category="mandatory", description="Review required", stage=Stage.PIONEER)
        d = r.to_dict()
        assert d["category"] == "mandatory"
        assert d["description"] == "Review required"
        assert d["stage"] == "pioneer"


class TestGovernancePrescription:
    """Tests for GovernancePrescription."""

    def test_to_dict(self):
        p = GovernancePrescription(
            stage=Stage.PIONEER,
            path="src/mod",
            mandatory=[
                GovernanceRule(category="mandatory", description="Review", stage=Stage.PIONEER)
            ],
        )
        d = p.to_dict()
        assert d["stage"] == "pioneer"
        assert d["path"] == "src/mod"
        assert len(d["mandatory"]) == 1

    def test_default_empty_lists(self):
        p = GovernancePrescription(stage=Stage.CLIMAX)
        assert p.mandatory == []
        assert p.recommended == []
        assert p.forbidden == []


class TestDisturbanceEvent:
    """Tests for DisturbanceEvent."""

    def test_to_dict(self):
        e = DisturbanceEvent(
            path="src/legacy",
            event_type="major_deletion",
            previous_stage=Stage.CLIMAX,
            current_stage=Stage.DISTURBED,
            cause="Migration to REST",
        )
        d = e.to_dict()
        assert d["path"] == "src/legacy"
        assert d["event_type"] == "major_deletion"
        assert d["previous_stage"] == "climax"
        assert d["current_stage"] == "disturbed"
        assert d["cause"] == "Migration to REST"

    def test_to_dict_no_previous_stage(self):
        e = DisturbanceEvent(
            path="test",
            event_type="churn_spike",
        )
        d = e.to_dict()
        assert d["previous_stage"] is None


class TestTrajectoryProjection:
    """Tests for TrajectoryProjection."""

    def test_default_values(self):
        t = TrajectoryProjection(target_stage=Stage.CLIMAX)
        assert t.estimated_time == ""
        assert t.blockers == []
        assert t.recommended_actions == []

    def test_with_data(self):
        t = TrajectoryProjection(
            target_stage=Stage.CLIMAX,
            estimated_time="~4-6 months",
            blockers=["Low coverage"],
            recommended_actions=["Add tests"],
        )
        assert t.estimated_time == "~4-6 months"
        assert len(t.blockers) == 1
        assert len(t.recommended_actions) == 1
