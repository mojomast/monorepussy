import pytest
from ussy_parliament.amendment import (
    AmendmentEngine,
    GERMANENESS_THRESHOLD,
    MAX_AMENDMENT_DEPTH,
    germaneness,
    is_amendment_admissible,
)
from ussy_parliament.models import MotionStatus
from ussy_parliament.motion import MotionEngine
from ussy_parliament.storage import SQLiteStore


class TestGermaneness:
    def test_identical_scopes(self):
        assert germaneness({"a", "b"}, {"a", "b"}) == 1.0

    def test_partial_overlap(self):
        assert germaneness({"a", "b"}, {"b", "c"}) == 1 / 3

    def test_no_overlap(self):
        assert germaneness({"a"}, {"b"}) == 0.0

    def test_empty_both(self):
        assert germaneness(set(), set()) == 1.0

    def test_empty_one(self):
        assert germaneness(set(), {"a"}) == 0.0


class TestIsAmendmentAdmissible:
    def test_passes(self):
        assert is_amendment_admissible({"a", "b"}, {"a", "b", "c"}, depth=1)

    def test_fails_germaneness(self):
        assert not is_amendment_admissible({"a"}, {"b"}, depth=1)

    def test_fails_depth(self):
        assert not is_amendment_admissible({"a", "b"}, {"a", "b"}, depth=4)


class TestAmendmentEngine:
    def test_propose_amendment(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        motion_engine = MotionEngine(store)
        amendment_engine = AmendmentEngine(motion_engine)
        original = motion_engine.create_motion("bot", "scale:10x", scope={"prod"})
        original.status = MotionStatus.FLOOR
        store.save_motion(original)
        amendment = amendment_engine.propose_amendment(
            original.motion_id, "bot2", "scale:8x", scope={"prod"}
        )
        assert amendment.parent_id == original.motion_id
        assert amendment.depth == 1

    def test_propose_amendment_not_germane(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        motion_engine = MotionEngine(store)
        amendment_engine = AmendmentEngine(motion_engine)
        original = motion_engine.create_motion("bot", "scale:10x", scope={"prod"})
        original.status = MotionStatus.FLOOR
        store.save_motion(original)
        with pytest.raises(ValueError, match="not germane"):
            amendment_engine.propose_amendment(
                original.motion_id, "bot2", "scale:8x", scope={"unrelated"}
            )

    def test_propose_amendment_exceeds_depth(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        motion_engine = MotionEngine(store)
        amendment_engine = AmendmentEngine(motion_engine)
        original = motion_engine.create_motion("bot", "scale:10x", scope={"prod"})
        original.status = MotionStatus.FLOOR
        original.depth = MAX_AMENDMENT_DEPTH
        store.save_motion(original)
        with pytest.raises(ValueError, match="depth"):
            amendment_engine.propose_amendment(
                original.motion_id, "bot2", "scale:8x", scope={"prod"}
            )

    def test_get_amendment_tree(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        motion_engine = MotionEngine(store)
        amendment_engine = AmendmentEngine(motion_engine)
        original = motion_engine.create_motion("bot", "scale:10x", scope={"prod"})
        original.status = MotionStatus.FLOOR
        store.save_motion(original)
        amendment = amendment_engine.propose_amendment(
            original.motion_id, "bot2", "scale:8x", scope={"prod"}
        )
        tree = amendment_engine.get_amendment_tree(original.motion_id)
        assert tree["motion_id"] == original.motion_id
        assert len(tree["children"]) == 1
        assert tree["children"][0]["motion_id"] == amendment.motion_id

    def test_second_amendment(self, tmp_chamber):
        store = SQLiteStore(tmp_chamber / "test.db")
        motion_engine = MotionEngine(store)
        amendment_engine = AmendmentEngine(motion_engine)
        original = motion_engine.create_motion("bot", "scale:10x", scope={"prod"})
        original.status = MotionStatus.FLOOR
        store.save_motion(original)
        amendment = amendment_engine.propose_amendment(
            original.motion_id, "bot2", "scale:8x", scope={"prod"}
        )
        amended = amendment_engine.second_amendment(amendment.motion_id, "bot3")
        assert "bot3" in amended.seconders
