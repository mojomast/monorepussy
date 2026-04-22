import pytest
from parliament.models import Agent, Motion, MotionStatus, Session
from parliament.motion import compute_criticality_tier
from parliament.quorum import QuorumEngine, quorum_required
from parliament.storage import SQLiteStore


class TestQuorumRequired:
    def test_low_tier(self):
        m = Motion(motion_id="MP-1", agent_id="bot", action="deploy", criticality_tier=1)
        assert quorum_required(m, 10) == 4  # ceil(0.3 + 0.4*0.2 = 0.38 * 10) = 4

    def test_high_tier(self):
        m = Motion(motion_id="MP-1", agent_id="bot", action="deploy", criticality_tier=5)
        assert quorum_required(m, 10) == 7  # ceil(0.3 + 0.4*1.0 = 0.7 * 10) = 7

    def test_zero_total(self):
        m = Motion(motion_id="MP-1", agent_id="bot", action="deploy", criticality_tier=1)
        assert quorum_required(m, 0) == 0


class TestQuorumEngine:
    def test_call_to_order_achieved(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = QuorumEngine(store)
        store.save_agent(Agent(agent_id="a1", agent_type="t1", active=True))
        store.save_agent(Agent(agent_id="a2", agent_type="t2", active=True))
        store.save_agent(Agent(agent_id="a3", agent_type="t3", active=True))
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy", criticality_tier=1))
        session = engine.call_to_order("MP-1", "S1", {"a1", "a2", "a3"})
        assert session.quorum_verified is True

    def test_call_to_order_deficient(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = QuorumEngine(store)
        store.save_agent(Agent(agent_id="a1", agent_type="t1", active=True))
        store.save_agent(Agent(agent_id="a2", agent_type="t2", active=True))
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy", criticality_tier=5))
        session = engine.call_to_order("MP-1", "S1", {"a1"})
        assert session.quorum_verified is False

    def test_join_session_achieves_quorum(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = QuorumEngine(store)
        for i in range(10):
            store.save_agent(Agent(agent_id=f"a{i}", agent_type=f"t{i}", active=True))
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy", criticality_tier=1))
        # quorum_required = ceil(0.38 * 10) = 4
        session = engine.call_to_order("MP-1", "S1", {"a0"})
        assert session.quorum_verified is False
        engine.join_session("S1", "a1")
        engine.join_session("S1", "a2")
        session4 = engine.join_session("S1", "a3")
        assert session4.quorum_verified is True

    def test_leave_session_drops_quorum(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = QuorumEngine(store)
        for i in range(10):
            store.save_agent(Agent(agent_id=f"a{i}", agent_type=f"t{i}", active=True))
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy", criticality_tier=1))
        session = engine.call_to_order("MP-1", "S1", {"a0", "a1", "a2", "a3"})
        assert session.quorum_verified is True
        session2 = engine.leave_session("S1", "a1")
        session3 = engine.leave_session("S1", "a2")
        session4 = engine.leave_session("S1", "a3")
        assert session4.quorum_verified is False

    def test_check_quorum(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = QuorumEngine(store)
        store.save_agent(Agent(agent_id="a1", agent_type="t1", active=True))
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy", criticality_tier=1))
        engine.call_to_order("MP-1", "S1", {"a1"})
        assert engine.check_quorum("S1") is True

    def test_session_not_found(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = QuorumEngine(store)
        with pytest.raises(ValueError):
            engine.join_session("S-NONE", "a1")
