"""Tests for coroner.models."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from ussy_coroner.models import (
    TRACE_PERSISTENCE,
    CustodyChain,
    CustodyComparison,
    CustodyEntry,
    ErrorStain,
    Investigation,
    LuminolFinding,
    LuminolReport,
    LuminolResult,
    PipelineRun,
    SpatterReconstruction,
    Stage,
    StageStatus,
    StriationMatch,
    TraceEvidence,
    TraceTransferResult,
    TraceType,
    VelocityClass,
)


class TestTraceType:
    """Tests for TraceType enum."""

    def test_seven_trace_types(self):
        assert len(TraceType) == 7

    def test_trace_type_values(self):
        expected = ["fibers", "dna", "fingerprints", "soil", "tool_marks", "glass_fragments", "paint_layers"]
        actual = [t.value for t in TraceType]
        assert sorted(actual) == sorted(expected)

    def test_trace_persistence_keys_match(self):
        for tt in TraceType:
            assert tt in TRACE_PERSISTENCE

    def test_persistence_decay_values_reasonable(self):
        for tt, lam in TRACE_PERSISTENCE.items():
            assert 0.0 < lam < 1.0, f"Decay constant for {tt} out of range: {lam}"


class TestStageStatus:
    """Tests for StageStatus enum."""

    def test_stage_statuses(self):
        assert StageStatus.SUCCESS.value == "success"
        assert StageStatus.FAILURE.value == "failure"
        assert StageStatus.SKIPPED.value == "skipped"
        assert StageStatus.RUNNING.value == "running"


class TestStage:
    """Tests for Stage dataclass."""

    def test_stage_creation(self):
        stage = Stage(name="build", index=1)
        assert stage.name == "build"
        assert stage.index == 1
        assert stage.status == StageStatus.SUCCESS
        assert stage.env_vars == {}
        assert stage.artifacts == []
        assert stage.artifact_hashes == {}

    def test_stage_with_failure(self):
        stage = Stage(name="test", index=2, status=StageStatus.FAILURE)
        assert stage.status == StageStatus.FAILURE


class TestPipelineRun:
    """Tests for PipelineRun dataclass."""

    def test_pipeline_run_creation(self):
        run = PipelineRun(run_id="build-42")
        assert run.run_id == "build-42"
        assert run.stages == []

    def test_failed_stages(self, simple_failing_run):
        failures = simple_failing_run.failed_stages
        assert len(failures) == 1
        assert failures[0].name == "test"

    def test_first_failure(self, simple_failing_run):
        first = simple_failing_run.first_failure
        assert first is not None
        assert first.name == "test"

    def test_no_failures(self, passing_run):
        assert passing_run.failed_stages == []
        assert passing_run.first_failure is None

    def test_timestamp_uses_utc(self):
        run = PipelineRun(run_id="ts-test")
        assert run.timestamp.tzinfo is not None


class TestTraceEvidence:
    """Tests for TraceEvidence dataclass."""

    def test_trace_evidence_creation(self):
        te = TraceEvidence(
            source_stage="checkout",
            target_stage="build",
            trace_type=TraceType.FIBERS,
            strength=0.8,
            source_index=0,
            target_index=1,
        )
        assert te.suspicion_score > 0
        assert te.suspicion_score <= 1.0

    def test_suspicion_score_decay(self):
        """Traces further apart should have lower suspicion scores."""
        te_near = TraceEvidence(
            source_stage="checkout",
            target_stage="build",
            trace_type=TraceType.FIBERS,
            strength=1.0,
            source_index=0,
            target_index=1,
        )
        te_far = TraceEvidence(
            source_stage="checkout",
            target_stage="deploy",
            trace_type=TraceType.FIBERS,
            strength=1.0,
            source_index=0,
            target_index=4,
        )
        assert te_near.suspicion_score > te_far.suspicion_score

    def test_high_persistence_type(self):
        """High persistence trace types should have less decay."""
        te_hp = TraceEvidence(
            source_stage="a",
            target_stage="b",
            trace_type=TraceType.FINGERPRINTS,
            strength=1.0,
            source_index=0,
            target_index=3,
        )
        te_lp = TraceEvidence(
            source_stage="a",
            target_stage="b",
            trace_type=TraceType.SOIL,
            strength=1.0,
            source_index=0,
            target_index=3,
        )
        assert te_hp.suspicion_score > te_lp.suspicion_score


class TestErrorStain:
    """Tests for ErrorStain dataclass."""

    def test_error_stain_creation(self):
        stain = ErrorStain(
            stage_name="test",
            stage_index=2,
            breadth=3,
            depth=2,
        )
        assert stain.impact_angle > 0

    def test_impact_angle_calculation(self):
        """alpha = arcsin(breadth/depth) when breadth < depth."""
        stain = ErrorStain(
            stage_name="test",
            stage_index=2,
            breadth=2,
            depth=3,
        )
        expected = math.degrees(math.asin(2 / 3))
        assert abs(stain.impact_angle - expected) < 0.01

    def test_zero_depth(self):
        stain = ErrorStain(stage_name="test", stage_index=2, breadth=2, depth=0)
        assert stain.impact_angle == 0.0

    def test_breadth_exceeds_depth(self):
        """When breadth > depth, arcsin capped at 1.0."""
        stain = ErrorStain(stage_name="test", stage_index=2, breadth=5, depth=1)
        # arcsin(min(5/1, 1.0)) = arcsin(1.0) = 90°
        assert abs(stain.impact_angle - 90.0) < 0.01


class TestStriationMatch:
    """Tests for StriationMatch dataclass."""

    def test_high_correlation_sets_same_root_cause(self):
        match = StriationMatch(
            build_id_1="build-42",
            build_id_2="build-38",
            correlation=0.93,
        )
        assert match.same_root_cause is True

    def test_low_correlation_no_same_root_cause(self):
        match = StriationMatch(
            build_id_1="build-42",
            build_id_2="build-30",
            correlation=0.45,
        )
        assert match.same_root_cause is False

    def test_threshold_correlation(self):
        match = StriationMatch(
            build_id_1="a",
            build_id_2="b",
            correlation=0.81,
        )
        assert match.same_root_cause is True


class TestCustodyEntry:
    """Tests for CustodyEntry dataclass."""

    def test_compute_hash(self):
        entry = CustodyEntry(
            stage_name="build",
            stage_index=1,
            handler="build_handler",
            action="compile",
        )
        h = entry.compute_hash("0" * 64)
        assert len(h) == 64  # SHA-256 hex digest
        assert h != "0" * 64

    def test_hash_chain_determinism(self):
        """Same inputs should produce same hash."""
        _t = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        e1 = CustodyEntry(stage_name="build", stage_index=1, handler="h", action="a", timestamp=_t)
        e2 = CustodyEntry(stage_name="build", stage_index=1, handler="h", action="a", timestamp=_t)
        h1 = e1.compute_hash("prev_hash")
        h2 = e2.compute_hash("prev_hash")
        assert h1 == h2

    def test_hash_chain_changes_with_different_input(self):
        e1 = CustodyEntry(stage_name="build", stage_index=1, handler="h1", action="a")
        e2 = CustodyEntry(stage_name="build", stage_index=1, handler="h2", action="a")
        h1 = e1.compute_hash("prev")
        h2 = e2.compute_hash("prev")
        assert h1 != h2


class TestInvestigation:
    """Tests for Investigation dataclass."""

    def test_investigation_creation(self):
        inv = Investigation(run_id="build-42")
        assert inv.run_id == "build-42"
        assert inv.confidence == 0.0
        assert inv.timestamp.tzinfo is not None
