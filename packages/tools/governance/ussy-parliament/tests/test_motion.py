import pytest
from parliament.models import MotionStatus, VoteMethod
from parliament.motion import (
    MotionEngine,
    compute_criticality_tier,
    compute_impact_score,
    compute_required_seconds,
)
from parliament.storage import SQLiteStore


class TestComputeImpactScore:
    def test_empty_scope(self):
        assert compute_impact_score(set()) == 0.0

    def test_single_item(self):
        assert compute_impact_score({"a"}, {"a": 2.0}) == 2.0

    def test_multiple_items(self):
        assert compute_impact_score({"a", "b"}, {"a": 2.0, "b": 3.0}) == 5.0

    def test_default_criticality(self):
        assert compute_impact_score({"a"}) == 1.0


class TestComputeRequiredSeconds:
    def test_zero_impact(self):
        assert compute_required_seconds(0) == 1

    def test_low_impact(self):
        assert compute_required_seconds(1) == 1

    def test_medium_impact(self):
        # ln(100+1) ~ 4.6 -> ceil = 5
        assert compute_required_seconds(100) == 5

    def test_high_impact(self):
        assert compute_required_seconds(10000) == 7  # capped at 7

    def test_policy_cap(self):
        assert compute_required_seconds(1e9, policy_cap=3) == 3


class TestComputeCriticalityTier:
    def test_zero(self):
        assert compute_criticality_tier(0) == 1

    def test_low(self):
        assert compute_criticality_tier(5) == 1

    def test_mid(self):
        assert compute_criticality_tier(100) == 2  # log10(100)=2, ceil=2

    def test_high(self):
        assert compute_criticality_tier(100000) == 5


class TestMotionEngine:
    def test_create_motion(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = MotionEngine(store)
        m = engine.create_motion("bot", "deploy")
        assert m.agent_id == "bot"
        assert m.action == "deploy"
        assert m.status == MotionStatus.DOCKET
        assert m.required_seconds >= 1

    def test_second_motion(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = MotionEngine(store)
        m = engine.create_motion("bot", "deploy", scope={"prod"}, criticality_map={"prod": 1.0})
        # With impact_score=1.0, required_seconds should be 1
        assert m.required_seconds == 1
        m2 = engine.second_motion(m.motion_id, "bot2")
        assert m2.status == MotionStatus.FLOOR

    def test_withdraw_second_returns_to_docket(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = MotionEngine(store)
        # impact=2.0 gives required_seconds=2 (ceil(ln(3)) = 2)
        m = engine.create_motion("bot", "deploy", scope={"prod"}, criticality_map={"prod": 2.0})
        engine.second_motion(m.motion_id, "bot2")
        m2 = engine.second_motion(m.motion_id, "bot3")
        assert m2.status == MotionStatus.FLOOR
        m3 = engine.withdraw_second(m.motion_id, "bot2")
        assert m3.status == MotionStatus.DOCKET

    def test_second_motion_not_found(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = MotionEngine(store)
        with pytest.raises(ValueError):
            engine.second_motion("MP-NONEXISTENT", "bot")

    def test_graduate_if_ready(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = MotionEngine(store)
        m = engine.create_motion("bot", "deploy")
        engine.second_motion(m.motion_id, "bot2")
        m2 = engine.graduate_if_ready(m.motion_id)
        assert m2.status == MotionStatus.FLOOR

    def test_list_motions(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = MotionEngine(store)
        m1 = engine.create_motion("bot", "deploy")
        m2 = engine.create_motion("bot", "scale")
        assert len(engine.list_motions()) == 2
