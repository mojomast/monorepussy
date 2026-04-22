import pytest
from parliament.models import MotionStatus, ViolationType, VoteMethod, Vote


class TestParliamentSession:
    def test_init_chamber(self, tmp_chamber):
        from parliament.session import ParliamentSession
        s = ParliamentSession(tmp_chamber)
        s.init_chamber()
        assert (tmp_chamber).exists()

    def test_register_agent(self, session):
        agent = session.register_agent("a1", "test", base_weight=1.5)
        assert agent.agent_id == "a1"
        assert agent.weight == 1.5
        loaded = session.store.get_agent("a1")
        assert loaded is not None
        assert loaded.agent_type == "test"

    def test_create_motion(self, session):
        motion = session.create_motion("bot", "deploy", scope={"prod"})
        assert motion.status == MotionStatus.DOCKET
        loaded = session.store.get_motion(motion.motion_id)
        assert loaded is not None

    def test_second_and_graduate(self, populated_session):
        motion = populated_session.create_motion("deploy-bot", "scale:10x", scope={"prod"})
        populated_session.second_motion(motion.motion_id, "canary-bot")
        loaded = populated_session.store.get_motion(motion.motion_id)
        assert loaded.status == MotionStatus.FLOOR

    def test_propose_amendment(self, populated_session):
        original = populated_session.create_motion("deploy-bot", "scale:10x", scope={"prod"})
        original.status = MotionStatus.FLOOR
        populated_session.store.save_motion(original)
        amendment = populated_session.propose_amendment(original.motion_id, "canary-bot", "scale:8x", scope={"prod"})
        assert amendment.parent_id == original.motion_id

    def test_full_vote_majority(self, populated_session):
        motion = populated_session.create_motion("deploy-bot", "scale:10x", scope={"prod"})
        populated_session.second_motion(motion.motion_id, "canary-bot")
        populated_session.open_voting(motion.motion_id, VoteMethod.MAJORITY)
        populated_session.cast_vote(motion.motion_id, "deploy-bot", True)
        populated_session.cast_vote(motion.motion_id, "canary-bot", True)
        result = populated_session.close_voting(motion.motion_id)
        assert result.passes is True
        loaded = populated_session.store.get_motion(motion.motion_id)
        assert loaded.status == MotionStatus.PASSED

    def test_full_vote_supermajority_fail(self, populated_session):
        motion = populated_session.create_motion("deploy-bot", "scale:10x", scope={"prod"})
        populated_session.second_motion(motion.motion_id, "canary-bot")
        populated_session.open_voting(motion.motion_id, VoteMethod.SUPERMAJORITY)
        populated_session.cast_vote(motion.motion_id, "deploy-bot", True)
        populated_session.cast_vote(motion.motion_id, "canary-bot", False)
        result = populated_session.close_voting(motion.motion_id)
        assert result.passes is False

    def test_call_to_order_and_quorum(self, populated_session):
        motion = populated_session.create_motion("deploy-bot", "scale:10x", scope={"prod"})
        agents = {"deploy-bot", "canary-bot", "security-scanner", "cost-monitor", "rollback-bot", "test-runner", "compliance-audit", "on-call-human"}
        sess = populated_session.call_to_order(motion.motion_id, agents_present=agents)
        assert sess.quorum_verified is True

    def test_point_of_order_suspends(self, populated_session):
        motion = populated_session.create_motion("deploy-bot", "scale:10x", scope={"prod"})
        populated_session.second_motion(motion.motion_id, "canary-bot")
        poo = populated_session.raise_point_of_order(motion.motion_id, ViolationType.QUORUM_DEFICIT, "rollback-bot")
        populated_session.rule_on_point(poo.poo_id)
        loaded = populated_session.store.get_motion(motion.motion_id)
        assert loaded.status == MotionStatus.SUSPENDED

    def test_appeal_reinstates(self, populated_session):
        motion = populated_session.create_motion("deploy-bot", "scale:10x", scope={"prod"})
        populated_session.second_motion(motion.motion_id, "canary-bot")
        poo = populated_session.raise_point_of_order(motion.motion_id, ViolationType.QUORUM_DEFICIT, "rollback-bot")
        populated_session.rule_on_point(poo.poo_id)
        appeal = populated_session.file_appeal(poo.poo_id, ["deploy-bot", "canary-bot"])
        votes = [Vote(agent_id="deploy-bot", aye=True, weight=1.0), Vote(agent_id="canary-bot", aye=True, weight=1.0)]
        populated_session.vote_appeal(appeal.appeal_id, votes)
        loaded = populated_session.store.get_motion(motion.motion_id)
        assert loaded.status == MotionStatus.FLOOR

    def test_journal_entries_created(self, populated_session):
        motion = populated_session.create_motion("deploy-bot", "scale:10x", scope={"prod"})
        entries = populated_session.journal_engine.view_session(motion.motion_id)
        assert len(entries) >= 1
        assert entries[0].entry_type.value == "motion_introduced"

    def test_generate_minutes(self, populated_session):
        motion = populated_session.create_motion("deploy-bot", "scale:10x", scope={"prod"})
        minutes = populated_session.generate_minutes(motion.motion_id)
        assert "Minutes for Session" in minutes

    def test_amendment_second_graduates(self, populated_session):
        original = populated_session.create_motion("deploy-bot", "scale:10x", scope={"prod"})
        original.status = MotionStatus.FLOOR
        populated_session.store.save_motion(original)
        amendment = populated_session.propose_amendment(original.motion_id, "canary-bot", "scale:8x", scope={"prod"})
        populated_session.second_amendment(amendment.motion_id, "security-scanner")
        loaded = populated_session.store.get_motion(amendment.motion_id)
        assert loaded.status == MotionStatus.FLOOR

    def test_consensus_voting(self, populated_session):
        motion = populated_session.create_motion("deploy-bot", "scale:10x", scope={"prod"})
        populated_session.second_motion(motion.motion_id, "canary-bot")
        populated_session.open_voting(motion.motion_id, VoteMethod.CONSENSUS)
        for agent_id in ["deploy-bot", "canary-bot", "security-scanner", "cost-monitor", "rollback-bot"]:
            populated_session.cast_vote(motion.motion_id, agent_id, True)
        # Use an agent with low weight for NAY so veto threshold (0.5) is not triggered
        agent = populated_session.store.get_agent("test-runner")
        agent.base_weight = 0.1
        populated_session.store.save_agent(agent)
        populated_session.cast_vote(motion.motion_id, "test-runner", False)
        result = populated_session.close_voting(motion.motion_id)
        assert result.passes is True
