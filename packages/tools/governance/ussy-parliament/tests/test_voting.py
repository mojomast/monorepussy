import pytest
from ussy_parliament.models import Agent, Motion, MotionStatus, Vote, VoteMethod
from ussy_parliament.storage import SQLiteStore
from ussy_parliament.voting import VotingEngine, tally_votes


class TestTallyVotes:
    def test_majority_pass(self):
        votes = [Vote(agent_id="a1", aye=True, weight=1.0), Vote(agent_id="a2", aye=True, weight=1.0), Vote(agent_id="a3", aye=False, weight=0.5)]
        result = tally_votes(votes, VoteMethod.MAJORITY)
        assert result.passes is True
        assert result.tally > 0.5

    def test_majority_fail(self):
        votes = [Vote(agent_id="a1", aye=True, weight=0.4), Vote(agent_id="a2", aye=False, weight=1.0)]
        result = tally_votes(votes, VoteMethod.MAJORITY)
        assert result.passes is False

    def test_supermajority_pass(self):
        votes = [Vote(agent_id="a1", aye=True, weight=1.0), Vote(agent_id="a2", aye=True, weight=1.0), Vote(agent_id="a3", aye=False, weight=0.1)]
        result = tally_votes(votes, VoteMethod.SUPERMAJORITY)
        assert result.passes is True

    def test_supermajority_fail(self):
        votes = [Vote(agent_id="a1", aye=True, weight=1.0), Vote(agent_id="a2", aye=False, weight=1.0)]
        result = tally_votes(votes, VoteMethod.SUPERMAJORITY)
        assert result.passes is False

    def test_consensus_pass(self):
        votes = [Vote(agent_id="a1", aye=True, weight=1.0), Vote(agent_id="a2", aye=True, weight=1.0), Vote(agent_id="a3", aye=False, weight=0.1)]
        result = tally_votes(votes, VoteMethod.CONSENSUS)
        assert result.passes is True

    def test_consensus_fail_veto(self):
        votes = [Vote(agent_id="a1", aye=True, weight=1.0), Vote(agent_id="a2", aye=False, weight=1.0)]
        result = tally_votes(votes, VoteMethod.CONSENSUS)
        assert result.passes is False

    def test_empty_votes(self):
        result = tally_votes([], VoteMethod.MAJORITY)
        assert result.passes is False
        assert result.total_weight == 0.0

    def test_unanimous(self):
        votes = [Vote(agent_id="a1", aye=True, weight=1.0), Vote(agent_id="a2", aye=True, weight=1.0)]
        result = tally_votes(votes, VoteMethod.MAJORITY)
        assert result.passes is True
        assert result.tally == 1.0


class TestVotingEngine:
    def test_open_voting(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = VotingEngine(store)
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy", status=MotionStatus.FLOOR))
        motion = engine.open_voting("MP-1")
        assert motion.status == MotionStatus.VOTING

    def test_cast_vote(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = VotingEngine(store)
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy", status=MotionStatus.VOTING))
        store.save_agent(Agent(agent_id="a1", agent_type="test", base_weight=1.0))
        vote = engine.cast_vote("MP-1", "a1", True)
        assert vote.aye is True
        assert vote.weight == 1.0

    def test_double_voting_blocked(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = VotingEngine(store)
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy", status=MotionStatus.VOTING))
        store.save_agent(Agent(agent_id="a1", agent_type="test", base_weight=1.0))
        engine.cast_vote("MP-1", "a1", True)
        with pytest.raises(ValueError, match="already voted"):
            engine.cast_vote("MP-1", "a1", False)

    def test_close_voting_pass(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = VotingEngine(store)
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy", status=MotionStatus.VOTING, vote_method=VoteMethod.MAJORITY))
        store.save_agent(Agent(agent_id="a1", agent_type="test", base_weight=1.0))
        store.save_agent(Agent(agent_id="a2", agent_type="test", base_weight=1.0))
        engine.cast_vote("MP-1", "a1", True)
        engine.cast_vote("MP-1", "a2", True)
        result = engine.close_voting("MP-1")
        assert result.passes is True
        motion = store.get_motion("MP-1")
        assert motion.status == MotionStatus.PASSED

    def test_close_voting_fail(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = VotingEngine(store)
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy", status=MotionStatus.VOTING, vote_method=VoteMethod.MAJORITY))
        store.save_agent(Agent(agent_id="a1", agent_type="test", base_weight=1.0))
        store.save_agent(Agent(agent_id="a2", agent_type="test", base_weight=1.0))
        engine.cast_vote("MP-1", "a1", False)
        engine.cast_vote("MP-1", "a2", False)
        result = engine.close_voting("MP-1")
        assert result.passes is False
        motion = store.get_motion("MP-1")
        assert motion.status == MotionStatus.FAILED

    def test_get_result(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        engine = VotingEngine(store)
        store.save_motion(Motion(motion_id="MP-1", agent_id="bot", action="deploy", status=MotionStatus.VOTING, vote_method=VoteMethod.MAJORITY))
        store.save_agent(Agent(agent_id="a1", agent_type="test", base_weight=1.0))
        engine.cast_vote("MP-1", "a1", True)
        result = engine.get_result("MP-1")
        assert result.tally == 1.0
