import pytest
from datetime import datetime, timezone

from ussy_parliament.models import (
    Agent,
    Appeal,
    EntryType,
    JournalEntry,
    Motion,
    MotionStatus,
    PointOfOrder,
    Session,
    ViolationType,
    Vote,
    VoteMethod,
)


class TestAgent:
    def test_agent_default_weight(self):
        a = Agent(agent_id="a1", agent_type="test")
        assert a.weight == 1.0

    def test_agent_weight_decay(self):
        a = Agent(agent_id="a1", agent_type="test", error_count_30d=1)
        assert a.weight == 0.95

    def test_agent_weight_multiple_errors(self):
        a = Agent(agent_id="a1", agent_type="test", error_count_30d=2)
        assert a.weight == 0.9025


class TestMotion:
    def test_motion_defaults(self):
        m = Motion(motion_id="MP-1", agent_id="bot", action="deploy")
        assert m.status == MotionStatus.DOCKET
        assert m.scope == set()
        assert m.seconders == set()

    def test_motion_post_init_preserves_values(self):
        m = Motion(
            motion_id="MP-1",
            agent_id="bot",
            action="deploy",
            scope={"a", "b"},
            seconders={"x"},
        )
        assert m.scope == {"a", "b"}
        assert m.seconders == {"x"}


class TestVote:
    def test_vote_creation(self):
        v = Vote(agent_id="a1", aye=True, weight=0.9)
        assert v.aye is True
        assert v.weight == 0.9


class TestSession:
    def test_session_defaults(self):
        s = Session(session_id="S1", motion_id="MP-1")
        assert s.quorum_verified is False
        assert s.agents_present == set()


class TestPointOfOrder:
    def test_poo_creation(self):
        p = PointOfOrder(
            poo_id="POO-1",
            motion_id="MP-1",
            violation_type=ViolationType.QUORUM_DEFICIT,
            claimant="bot",
        )
        assert p.sustained is None


class TestJournalEntry:
    def test_journal_entry_hash(self):
        e = JournalEntry(
            entry_id="J1",
            timestamp=datetime(2026, 4, 22, 5, 14, tzinfo=timezone.utc),
            entry_type=EntryType.MOTION_INTRODUCED,
            data=b"test",
            previous_hash=b"",
        )
        h1 = e.hash
        h2 = e.hash
        assert h1 == h2
        assert isinstance(h1, bytes)

    def test_journal_entry_hash_changes_with_data(self):
        e1 = JournalEntry(
            entry_id="J1",
            timestamp=datetime(2026, 4, 22, 5, 14, tzinfo=timezone.utc),
            entry_type=EntryType.MOTION_INTRODUCED,
            data=b"test1",
            previous_hash=b"",
        )
        e2 = JournalEntry(
            entry_id="J1",
            timestamp=datetime(2026, 4, 22, 5, 14, tzinfo=timezone.utc),
            entry_type=EntryType.MOTION_INTRODUCED,
            data=b"test2",
            previous_hash=b"",
        )
        assert e1.hash != e2.hash

    def test_journal_entry_to_dict(self):
        e = JournalEntry(
            entry_id="J1",
            timestamp=datetime(2026, 4, 22, 5, 14, tzinfo=timezone.utc),
            entry_type=EntryType.MOTION_INTRODUCED,
            data=b"test",
            previous_hash=b"\x00",
        )
        d = e.to_dict()
        assert d["entry_id"] == "J1"
        assert d["entry_type"] == "motion_introduced"


class TestAppeal:
    def test_appeal_defaults(self):
        a = Appeal(appeal_id="A1", poo_id="POO-1", motion_id="MP-1")
        assert a.outcome is None
        assert a.appealers == []
