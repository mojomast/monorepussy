"""Tests for coroner.db — SQLite storage."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from coroner.db import ForensicDB
from coroner.models import (
    CustodyChain,
    CustodyEntry,
    ErrorStain,
    LuminolFinding,
    LuminolReport,
    LuminolResult,
    PipelineRun,
    Stage,
    StageStatus,
    StriationMatch,
    TraceEvidence,
    TraceTransferResult,
    TraceType,
)


class TestForensicDB:
    """Tests for ForensicDB."""

    def test_create_in_memory(self):
        db = ForensicDB(":memory:")
        db.close()

    def test_create_on_disk(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        db = ForensicDB(path)
        db.close()
        assert Path(path).exists()

    def test_save_and_load_run(self, simple_failing_run):
        db = ForensicDB(":memory:")
        db.save_run(simple_failing_run)
        loaded = db.load_run(simple_failing_run.run_id)
        assert loaded is not None
        assert loaded.run_id == "test-run-1"
        assert len(loaded.stages) == 3
        assert loaded.stages[0].name == "checkout"
        assert loaded.stages[2].status == StageStatus.FAILURE
        db.close()

    def test_load_nonexistent_run(self):
        db = ForensicDB(":memory:")
        loaded = db.load_run("nonexistent")
        assert loaded is None
        db.close()

    def test_list_runs(self, simple_failing_run, passing_run):
        db = ForensicDB(":memory:")
        db.save_run(simple_failing_run)
        db.save_run(passing_run)
        runs = db.list_runs()
        assert len(runs) == 2
        db.close()

    def test_save_and_load_traces(self):
        db = ForensicDB(":memory:")
        result = TraceTransferResult(
            forward_traces=[
                TraceEvidence(
                    source_stage="checkout",
                    target_stage="build",
                    trace_type=TraceType.FIBERS,
                    strength=0.8,
                    source_index=0,
                    target_index=1,
                ),
            ],
            reverse_traces=[
                TraceEvidence(
                    source_stage="build",
                    target_stage="checkout",
                    trace_type=TraceType.GLASS_FRAGMENTS,
                    strength=0.6,
                    source_index=1,
                    target_index=0,
                ),
            ],
        )
        db.save_traces("run-1", result)
        loaded = db.load_traces("run-1")
        assert len(loaded.forward_traces) == 1
        assert len(loaded.reverse_traces) == 1
        assert loaded.forward_traces[0].trace_type == TraceType.FIBERS
        db.close()

    def test_save_and_load_stains(self):
        db = ForensicDB(":memory:")
        stains = [
            ErrorStain(stage_name="test", stage_index=2, breadth=3, depth=2, component="auth"),
            ErrorStain(stage_name="deploy", stage_index=4, breadth=1, depth=1, component="deploy"),
        ]
        db.save_stains("run-1", stains)
        loaded = db.load_stains("run-1")
        assert len(loaded) == 2
        assert loaded[0].stage_name == "test"
        db.close()

    def test_save_and_load_striations(self):
        db = ForensicDB(":memory:")
        match = StriationMatch(
            build_id_1="build-42",
            build_id_2="build-38",
            correlation=0.93,
        )
        db.save_striation("build-42", match)
        loaded = db.load_striations("build-42")
        assert len(loaded) == 1
        assert loaded[0].correlation == 0.93
        assert loaded[0].same_root_cause is True
        db.close()

    def test_save_and_load_luminol(self):
        db = ForensicDB(":memory:")
        report = LuminolReport(
            findings=[
                LuminolFinding(
                    category="cache",
                    path=".cache/node_modules",
                    expected_hash="a4f2b3c4",
                    actual_hash="7c91d2e3",
                    result=LuminolResult.PRESUMPTIVE_POSITIVE,
                    description="Hash mismatch",
                ),
                LuminolFinding(
                    category="ninhydrin",
                    env_vars=["REDIS_URL", "NODE_OPTIONS"],
                    source_stage="test",
                    target_stage="deploy",
                    result=LuminolResult.CONFIRMED,
                    description="Undeclared env vars",
                ),
            ],
            confirmed=True,
        )
        db.save_luminol("run-1", report)
        loaded = db.load_luminol("run-1")
        assert len(loaded.findings) == 2
        assert loaded.findings[0].category == "cache"
        assert loaded.findings[1].env_vars == ["REDIS_URL", "NODE_OPTIONS"]
        db.close()

    def test_save_and_load_custody(self):
        db = ForensicDB(":memory:")
        from datetime import datetime, timezone
        chain = CustodyChain(
            run_id="run-1",
            entries=[
                CustodyEntry(
                    stage_name="checkout",
                    stage_index=0,
                    handler="checkout",
                    timestamp=datetime.now(timezone.utc),
                    action="status=success",
                    hash_value="abc123",
                ),
                CustodyEntry(
                    stage_name="build",
                    stage_index=1,
                    handler="build",
                    timestamp=datetime.now(timezone.utc),
                    action="status=success",
                    hash_value="def456",
                ),
            ],
        )
        db.save_custody(chain)
        loaded = db.load_custody("run-1")
        assert len(loaded.entries) == 2
        assert loaded.entries[0].hash_value == "abc123"
        db.close()

    def test_overwrite_run(self, simple_failing_run):
        db = ForensicDB(":memory:")
        db.save_run(simple_failing_run)
        # Save again with same ID — should overwrite
        db.save_run(simple_failing_run)
        runs = db.list_runs()
        assert len(runs) == 1
        db.close()
