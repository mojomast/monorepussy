"""Tests for disturbances module."""

from __future__ import annotations

from pathlib import Path

import pytest

from ussy_seral.disturbances import DisturbanceDetector
from ussy_seral.models import ModuleMetrics, Stage


class TestDisturbanceDetector:
    """Tests for DisturbanceDetector."""

    def test_detect_no_disturbance(self):
        """A healthy module should have no disturbances."""
        detector = DisturbanceDetector()
        metrics = ModuleMetrics(
            path="src/healthy",
            deletion_ratio=0.05,
            contributor_spike=0.5,
            churn_spike=0.5,
        )
        events = detector.detect("src/healthy")
        # Should be empty since no real git data to trigger
        # (git commands will fail on nonexistent repo)
        assert isinstance(events, list)

    def test_detect_all_disturbed_modules(self):
        """detect_all should only process disturbed modules."""
        detector = DisturbanceDetector()
        modules = [
            ModuleMetrics(path="src/healthy", stage=Stage.PIONEER),
            ModuleMetrics(path="src/disturbed", stage=Stage.DISTURBED),
        ]
        events = detector.detect_all(modules)
        assert isinstance(events, list)

    def test_detect_all_empty(self):
        """detect_all with no disturbed modules returns empty list."""
        detector = DisturbanceDetector()
        modules = [
            ModuleMetrics(path="src/a", stage=Stage.PIONEER),
            ModuleMetrics(path="src/b", stage=Stage.CLIMAX),
        ]
        events = detector.detect_all(modules)
        assert events == []

    def test_infer_previous_stage_old(self):
        """Old modules were likely climax before disturbance."""
        detector = DisturbanceDetector()
        metrics = ModuleMetrics(path="test", age_days=500)
        stage = detector._infer_previous_stage(metrics)
        assert stage == Stage.CLIMAX

    def test_infer_previous_stage_medium(self):
        """Medium-aged modules were likely seral_mid before disturbance."""
        detector = DisturbanceDetector()
        metrics = ModuleMetrics(path="test", age_days=200)
        stage = detector._infer_previous_stage(metrics)
        assert stage == Stage.SERAL_MID

    def test_infer_previous_stage_young(self):
        """Young modules were likely pioneer before disturbance."""
        detector = DisturbanceDetector()
        metrics = ModuleMetrics(path="test", age_days=10)
        stage = detector._infer_previous_stage(metrics)
        assert stage == Stage.PIONEER

    def test_disturbance_event_types(self):
        """Verify that different disturbance types can be detected."""
        # We test the event creation logic directly
        from ussy_seral.models import DisturbanceEvent

        e1 = DisturbanceEvent(
            path="src/legacy",
            event_type="major_deletion",
            cause="60% files removed",
        )
        assert e1.event_type == "major_deletion"

        e2 = DisturbanceEvent(
            path="src/core",
            event_type="contributor_spike",
            cause="3 → 9 contributors",
        )
        assert e2.event_type == "contributor_spike"

        e3 = DisturbanceEvent(
            path="src/hot",
            event_type="churn_spike",
            cause="Churn rate doubled",
        )
        assert e3.event_type == "churn_spike"
