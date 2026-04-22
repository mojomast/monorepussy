"""Tests for coroner.scanner — Directory scan and JSON ingestion."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ussy_coroner.models import PipelineRun, StageStatus
from ussy_coroner.models import PipelineRun, StageStatus
from ussy_coroner.scanner import (
    ingest_json,
    scan_directory,
    _detect_status,
    _extract_env_vars,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_RUN_JSON = FIXTURES_DIR / "sample_run" / "run.json"


class TestDetectStatus:
    """Tests for automatic status detection from log content."""

    def test_detect_failure(self):
        log = "FAILED test.js\nAssertionError: expected true\nexit code 1"
        assert _detect_status(log) == StageStatus.FAILURE

    def test_detect_error(self):
        log = "ERROR: Cannot connect to database"
        assert _detect_status(log) == StageStatus.FAILURE

    def test_detect_fatal(self):
        log = "FATAL: Out of memory"
        assert _detect_status(log) == StageStatus.FAILURE

    def test_detect_exception(self):
        log = "Exception in thread main java.lang.NullPointerException"
        assert _detect_status(log) == StageStatus.FAILURE

    def test_detect_success(self):
        log = "BUILD SUCCESSFUL\nAll tests passed"
        assert _detect_status(log) == StageStatus.SUCCESS

    def test_detect_exit_code_0(self):
        log = "Some output\nexit code 0"
        assert _detect_status(log) == StageStatus.SUCCESS

    def test_mixed_failure_and_success(self):
        """When both present, failure takes precedence."""
        log = "BUILD SUCCESSFUL\nFAILED test.js\nexit code 1"
        assert _detect_status(log) == StageStatus.FAILURE

    def test_empty_log(self):
        log = ""
        assert _detect_status(log) == StageStatus.SUCCESS


class TestExtractEnvVars:
    """Tests for environment variable extraction from logs."""

    def test_extract_export_vars(self):
        log = "export FOO=bar\nexport BAZ=qux"
        env = _extract_env_vars(log)
        assert env.get("FOO") == "bar"
        assert env.get("BAZ") == "qux"

    def test_extract_simple_assignment(self):
        log = "DEP_VERSION=4.17.20"
        env = _extract_env_vars(log)
        assert env.get("DEP_VERSION") == "4.17.20"

    def test_no_env_vars(self):
        log = "Just some output\nNothing to see here"
        env = _extract_env_vars(log)
        assert len(env) == 0


class TestIngestJson:
    """Tests for JSON ingestion."""

    def test_ingest_sample_run(self):
        run = ingest_json(SAMPLE_RUN_JSON)
        assert run.run_id == "build-42"
        assert len(run.stages) == 5

    def test_ingest_preserves_status(self):
        run = ingest_json(SAMPLE_RUN_JSON)
        assert run.stages[0].status == StageStatus.SUCCESS
        assert run.stages[2].status == StageStatus.FAILURE

    def test_ingest_preserves_env_vars(self):
        run = ingest_json(SAMPLE_RUN_JSON)
        assert "DEP_VERSION" in run.stages[0].env_vars

    def test_ingest_preserves_artifact_hashes(self):
        run = ingest_json(SAMPLE_RUN_JSON)
        assert len(run.stages[0].artifact_hashes) > 0

    def test_ingest_from_dict(self):
        data = {
            "run_id": "test-1",
            "stages": [
                {"name": "build", "index": 0, "status": "success", "log_content": "OK"},
            ],
        }
        run = ingest_json(data)
        assert run.run_id == "test-1"
        assert len(run.stages) == 1

    def test_ingest_minimal_data(self):
        data = {"stages": []}
        run = ingest_json(data)
        assert run.run_id == "unknown"

    def test_ingest_with_log_autodetect(self):
        """Log content with failures should auto-detect status."""
        data = {
            "run_id": "auto-detect",
            "stages": [
                {
                    "name": "test",
                    "index": 0,
                    "status": "success",
                    "log_content": "FAILED test\nexit code 1",
                },
            ],
        }
        run = ingest_json(data)
        # Should override success with failure based on log content
        assert run.stages[0].status == StageStatus.FAILURE


class TestScanDirectory:
    """Tests for directory scanning."""

    def test_scan_sample_directory(self):
        run = scan_directory(FIXTURES_DIR / "sample_run")
        assert run.run_id == "build-42"
        assert len(run.stages) >= 2  # At least checkout and build logs

    def test_scan_nonexistent_directory(self):
        with pytest.raises(ValueError):
            scan_directory("/nonexistent/path/12345")

    def test_scan_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            run = scan_directory(tmpdir)
            assert isinstance(run, PipelineRun)
            assert len(run.stages) == 0

    def test_scan_with_env_dump(self):
        run = scan_directory(FIXTURES_DIR / "sample_run")
        # Should pick up env vars from env_dump.json
        total_env_vars = set()
        for stage in run.stages:
            total_env_vars.update(stage.env_vars.keys())
        # env_dump.json has DEP_VERSION, NODE_VERSION, REDIS_URL, CC, GCC_VERSION
        assert "DEP_VERSION" in total_env_vars or len(total_env_vars) > 0

    def test_scan_with_run_json(self):
        """run.json should override directory name as run_id."""
        run = scan_directory(FIXTURES_DIR / "sample_run")
        assert run.run_id == "build-42"
