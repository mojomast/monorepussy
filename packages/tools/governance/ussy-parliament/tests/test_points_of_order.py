import pytest
from ussy_parliament.models import (
    Agent,
    Appeal,
    Motion,
    MotionStatus,
    PointOfOrder,
    RulingOutcome,
    Session,
    ViolationType,
    Vote,
)
from ussy_parliament.points_of_order import PointsOfOrderEngine
from ussy_parliament.quorum import QuorumEngine
from ussy_parliament.storage import SQLiteStore


class TestPointsOfOrderEngine:
    def test_raise_point_of_order(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        quorum = QuorumEngine(store)
        engine = PointsOfOrderEngine(store, quorum)
        poo = engine.raise_point_of_order("MP-1", ViolationType.QUORUM_DEFICIT, "bot")
        assert poo.violation_type == ViolationType.QUORUM_DEFICIT
        assert poo.sustained is None

    def test_rule_quorum_deficit_sustained(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        quorum = QuorumEngine(store)
        engine = PointsOfOrderEngine(store, quorum)
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy"))
        poo = engine.raise_point_of_order("MP-1", ViolationType.QUORUM_DEFICIT, "bot")
        ruled = engine.rule(poo.poo_id)
        assert ruled.sustained is True
        assert ruled.remedy == "suspend_target"
        motion = store.get_motion("MP-1")
        assert motion.status == MotionStatus.SUSPENDED

    def test_rule_quorum_deficit_overturned(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        quorum = QuorumEngine(store)
        engine = PointsOfOrderEngine(store, quorum)
        store.save_agent(Agent(agent_id="a1", agent_type="t1", active=True))
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy"))
        quorum.call_to_order("MP-1", "S1", {"a1"})
        poo = engine.raise_point_of_order("MP-1", ViolationType.QUORUM_DEFICIT, "bot")
        ruled = engine.rule(poo.poo_id)
        # With 1 active agent and tier 1 motion, quorum_required = ceil(0.38 * 1) = 1, so quorum IS met
        assert ruled.sustained is False

    def test_rule_missing_second(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        quorum = QuorumEngine(store)
        engine = PointsOfOrderEngine(store, quorum)
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy", required_seconds=2, seconders=set()))
        poo = engine.raise_point_of_order("MP-1", ViolationType.MISSING_SECOND, "bot")
        ruled = engine.rule(poo.poo_id)
        assert ruled.sustained is True
        assert ruled.remedy == "return_to_docket"

    def test_rule_double_voting(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        quorum = QuorumEngine(store)
        engine = PointsOfOrderEngine(store, quorum)
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy"))
        store.save_vote(Vote(agent_id="a1", aye=True), "MP-1")
        store.save_vote(Vote(agent_id="a1", aye=False), "MP-1")
        poo = engine.raise_point_of_order("MP-1", ViolationType.DOUBLE_VOTING, "bot")
        ruled = engine.rule(poo.poo_id)
        assert ruled.sustained is True
        assert ruled.remedy == "invalidate_duplicate_votes"

    def test_appeal_insufficient_appealers(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        quorum = QuorumEngine(store)
        engine = PointsOfOrderEngine(store, quorum)
        poo = engine.raise_point_of_order("MP-1", ViolationType.QUORUM_DEFICIT, "bot")
        with pytest.raises(ValueError, match="At least 2 appealers"):
            engine.file_appeal(poo.poo_id, ["a1"])

    def test_appeal_overturn(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        quorum = QuorumEngine(store)
        engine = PointsOfOrderEngine(store, quorum)
        store.save_agent(Agent(agent_id="a1", agent_type="t1", active=True))
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy"))
        quorum.call_to_order("MP-1", "S1", {"a1"})
        poo = engine.raise_point_of_order("MP-1", ViolationType.QUORUM_DEFICIT, "bot")
        engine.rule(poo.poo_id)  # should be not sustained since quorum is met
        appeal = engine.file_appeal(poo.poo_id, ["a1", "a2"])
        votes = [Vote(agent_id="a1", aye=True, weight=1.0), Vote(agent_id="a2", aye=True, weight=1.0)]
        outcome = engine.vote_appeal(appeal.appeal_id, votes)
        assert outcome.outcome == RulingOutcome.OVERTURNED

    def test_appeal_sustain(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        quorum = QuorumEngine(store)
        engine = PointsOfOrderEngine(store, quorum)
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy"))
        poo = engine.raise_point_of_order("MP-1", ViolationType.QUORUM_DEFICIT, "bot")
        engine.rule(poo.poo_id)
        appeal = engine.file_appeal(poo.poo_id, ["a1", "a2"])
        votes = [Vote(agent_id="a1", aye=False, weight=1.0), Vote(agent_id="a2", aye=False, weight=1.0)]
        outcome = engine.vote_appeal(appeal.appeal_id, votes)
        assert outcome.outcome == RulingOutcome.SUSTAINED

    def test_appeal_reinstates_motion(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        quorum = QuorumEngine(store)
        engine = PointsOfOrderEngine(store, quorum)
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy", status=MotionStatus.SUSPENDED))
        poo = engine.raise_point_of_order("MP-1", ViolationType.QUORUM_DEFICIT, "bot")
        engine.rule(poo.poo_id)
        appeal = engine.file_appeal(poo.poo_id, ["a1", "a2"])
        votes = [Vote(agent_id="a1", aye=True, weight=1.0), Vote(agent_id="a2", aye=True, weight=1.0)]
        engine.vote_appeal(appeal.appeal_id, votes)
        motion = store.get_motion("MP-1")
        assert motion.status == MotionStatus.FLOOR
