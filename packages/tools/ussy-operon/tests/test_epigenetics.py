"""Tests for operon.epigenetics module."""

from datetime import datetime, timedelta, timezone

import pytest

from ussy_operon.epigenetics import EpigeneticStateTracker
from ussy_operon.models import Codebase, Gene, MarkType, Operon


class TestEpigeneticStateTracker:
    def test_tracker_creation(self):
        tracker = EpigeneticStateTracker()
        assert tracker.marks == []

    def test_is_archived_true(self):
        tracker = EpigeneticStateTracker()
        operon = Operon(operon_id="op_0", genes=[])
        history = [{"operon_id": "op_0", "action": "archive", "timestamp": (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()}]
        assert tracker._is_archived(operon, history) is True

    def test_is_archived_deprecated(self):
        tracker = EpigeneticStateTracker()
        operon = Operon(operon_id="op_0", genes=[Gene(name="old", path="old.py", is_deprecated=True)])
        assert tracker._is_archived(operon, []) is True

    def test_is_archived_false(self):
        tracker = EpigeneticStateTracker()
        operon = Operon(operon_id="op_0", genes=[Gene(name="new", path="new.py", is_deprecated=False)])
        assert tracker._is_archived(operon, []) is False

    def test_get_last_reviewed(self):
        tracker = EpigeneticStateTracker()
        operon = Operon(operon_id="op_0", genes=[])
        now = datetime.now(timezone.utc)
        history = [
            {"operon_id": "op_0", "action": "review", "timestamp": now.isoformat()},
        ]
        last = tracker._get_last_reviewed(operon, history)
        assert last is not None
        assert (last - now).total_seconds() < 1

    def test_get_last_reviewed_none(self):
        tracker = EpigeneticStateTracker()
        operon = Operon(operon_id="op_0", genes=[])
        last = tracker._get_last_reviewed(operon, [])
        assert last is None

    def test_days_since_recent(self):
        tracker = EpigeneticStateTracker()
        dt = datetime.now(timezone.utc) - timedelta(days=5)
        assert tracker._days_since(dt) == 5

    def test_days_since_very_recent(self):
        tracker = EpigeneticStateTracker()
        dt = datetime.now(timezone.utc) - timedelta(hours=1)
        assert tracker._days_since(dt) == 0

    def test_calculate_acetylation_level_no_review(self):
        tracker = EpigeneticStateTracker()
        operon = Operon(operon_id="op_0", genes=[])
        level = tracker._calculate_acetylation_level(operon, [])
        assert level == 0.0

    def test_calculate_acetylation_level_recent(self):
        tracker = EpigeneticStateTracker()
        operon = Operon(operon_id="op_0", genes=[])
        now = datetime.now(timezone.utc)
        history = [{"operon_id": "op_0", "action": "review", "timestamp": now.isoformat()}]
        level = tracker._calculate_acetylation_level(operon, history)
        assert level > 0.9

    def test_calculate_acetylation_level_old(self):
        tracker = EpigeneticStateTracker()
        operon = Operon(operon_id="op_0", genes=[])
        old = datetime.now(timezone.utc) - timedelta(days=35)
        history = [{"operon_id": "op_0", "action": "review", "timestamp": old.isoformat()}]
        level = tracker._calculate_acetylation_level(operon, history)
        assert level == 0.0

    def test_has_structure_changed_true(self):
        tracker = EpigeneticStateTracker()
        operon = Operon(operon_id="op_0", genes=[])
        recent = datetime.now(timezone.utc) - timedelta(days=5)
        history = [{"operon_id": "op_0", "action": "restructure", "timestamp": recent.isoformat()}]
        assert tracker._has_structure_changed(operon, history) is True

    def test_has_structure_changed_false(self):
        tracker = EpigeneticStateTracker()
        operon = Operon(operon_id="op_0", genes=[])
        old = datetime.now(timezone.utc) - timedelta(days=60)
        history = [{"operon_id": "op_0", "action": "restructure", "timestamp": old.isoformat()}]
        assert tracker._has_structure_changed(operon, history) is False

    def test_predict_epigenetic_inheritance_methylation(self):
        tracker = EpigeneticStateTracker()
        mark = tracker.add_manual_mark("op_0", MarkType.METHYLATION)
        inheritance = tracker._predict_epigenetic_inheritance([mark], [])
        assert "stable_silencing" in inheritance["op_0"]

    def test_predict_epigenetic_inheritance_acetylation(self):
        tracker = EpigeneticStateTracker()
        mark = tracker.add_manual_mark("op_0", MarkType.ACETYLATION)
        inheritance = tracker._predict_epigenetic_inheritance([mark], [])
        assert "active_transcription" in inheritance["op_0"]

    def test_predict_epigenetic_inheritance_with_risk(self):
        tracker = EpigeneticStateTracker()
        mark = tracker.add_manual_mark("op_0", MarkType.ACETYLATION)
        mark.deacetylase_risk = True
        inheritance = tracker._predict_epigenetic_inheritance([mark], [])
        assert "risk_of_silencing" in inheritance["op_0"]

    def test_suggest_interventions_methylation(self):
        tracker = EpigeneticStateTracker()
        mark = tracker.add_manual_mark("op_0", MarkType.METHYLATION)
        suggestions = tracker._suggest_interventions([mark])
        assert len(suggestions) == 1
        assert suggestions[0]["intervention"] == "review_archived_docs"

    def test_suggest_interventions_acetylation_risk(self):
        tracker = EpigeneticStateTracker()
        mark = tracker.add_manual_mark("op_0", MarkType.ACETYLATION)
        mark.deacetylase_risk = True
        suggestions = tracker._suggest_interventions([mark])
        assert any(s["intervention"] == "refresh_review" for s in suggestions)

    def test_track_epigenetic_state_empty(self):
        tracker = EpigeneticStateTracker()
        codebase = Codebase(root_path=".", operons=[], genes=[])
        result = tracker.track_epigenetic_state([], codebase)
        assert result["total_operons"] == 0
        assert result["current_marks"] == []

    def test_track_epigenetic_state_with_methylation(self):
        tracker = EpigeneticStateTracker()
        operon = Operon(operon_id="op_0", genes=[Gene(name="old", path="old.py", is_deprecated=True)])
        codebase = Codebase(root_path=".", operons=[operon])
        result = tracker.track_epigenetic_state([], codebase)
        assert len(result["current_marks"]) == 1
        assert result["current_marks"][0]["mark_type"] == "methylation"

    def test_track_epigenetic_state_with_acetylation(self):
        tracker = EpigeneticStateTracker()
        operon = Operon(operon_id="op_0", genes=[])
        codebase = Codebase(root_path=".", operons=[operon])
        now = datetime.now(timezone.utc)
        history = [{"operon_id": "op_0", "action": "review", "timestamp": now.isoformat()}]
        result = tracker.track_epigenetic_state(history, codebase)
        assert any(m["mark_type"] == "acetylation" for m in result["current_marks"])

    def test_add_manual_mark(self):
        tracker = EpigeneticStateTracker()
        mark = tracker.add_manual_mark("op_0", MarkType.CHROMATIN_REMODELING, effect="test")
        assert mark.mark_type == MarkType.CHROMATIN_REMODELING
        assert mark.operon_id == "op_0"
        assert len(tracker.marks) == 1

    def test_get_marks_for_operon(self):
        tracker = EpigeneticStateTracker()
        tracker.add_manual_mark("op_0", MarkType.ACETYLATION)
        tracker.add_manual_mark("op_1", MarkType.METHYLATION)
        marks = tracker.get_marks_for_operon("op_0")
        assert len(marks) == 1
        assert marks[0].operon_id == "op_0"

    def test_clear_marks_for_operon(self):
        tracker = EpigeneticStateTracker()
        tracker.add_manual_mark("op_0", MarkType.ACETYLATION)
        tracker.add_manual_mark("op_1", MarkType.METHYLATION)
        cleared = tracker.clear_marks_for_operon("op_0")
        assert cleared == 1
        assert len(tracker.marks) == 1
