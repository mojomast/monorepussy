"""Shared test fixtures for Coroner tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pytest

from coroner.models import (
    CustodyChain,
    CustodyEntry,
    ErrorStain,
    LuminolFinding,
    LuminolReport,
    LuminolResult,
    PipelineRun,
    SpatterReconstruction,
    Stage,
    StageStatus,
    TraceEvidence,
    TraceTransferResult,
    TraceType,
    VelocityClass,
)
from coroner.scanner import ingest_json

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_RUN_JSON = FIXTURES_DIR / "sample_run" / "run.json"
BUILD_38_JSON = FIXTURES_DIR / "build_38.json"


@pytest.fixture
def sample_run() -> PipelineRun:
    """Load the sample pipeline run from fixtures."""
    return ingest_json(SAMPLE_RUN_JSON)


@pytest.fixture
def build_38_run() -> PipelineRun:
    """Load the build-38 comparison run from fixtures."""
    return ingest_json(BUILD_38_JSON)


@pytest.fixture
def simple_failing_run() -> PipelineRun:
    """Create a simple failing pipeline run programmatically."""
    run = PipelineRun(run_id="test-run-1")
    _t0 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    run.stages = [
        Stage(
            name="checkout",
            index=0,
            status=StageStatus.SUCCESS,
            start_time=_t0,
            env_vars={"DEP_VERSION": "1.0.0", "NODE_VERSION": "18"},
            artifact_hashes={"src/": "hash1", "package.json": "hash2"},
        ),
        Stage(
            name="build",
            index=1,
            status=StageStatus.SUCCESS,
            start_time=datetime(2025, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
            log_content="BUILD SUCCESSFUL\nexport CC=gcc\nexport GCC_VERSION=12.2",
            env_vars={"DEP_VERSION": "1.0.0", "CC": "gcc", "GCC_VERSION": "12.2"},
            artifact_hashes={"dist/bundle.js": "hash3"},
        ),
        Stage(
            name="test",
            index=2,
            status=StageStatus.FAILURE,
            start_time=datetime(2025, 1, 1, 0, 2, 0, tzinfo=timezone.utc),
            log_content="FAILED auth-module/test.js\nAssertionError: expected 200 but got 401\nat auth-module/test.js:42\nexit code 1",
            env_vars={"DEP_VERSION": "1.0.0", "NODE_VERSION": "18", "CC": "clang", "GCC_VERSION": "13.1"},
        ),
    ]
    return run


@pytest.fixture
def passing_run() -> PipelineRun:
    """Create a passing pipeline run."""
    run = PipelineRun(run_id="passing-run")
    _t0 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    run.stages = [
        Stage(
            name="checkout",
            index=0,
            status=StageStatus.SUCCESS,
            start_time=_t0,
            env_vars={"DEP_VERSION": "1.0.0"},
            artifact_hashes={"src/": "hash1"},
        ),
        Stage(
            name="build",
            index=1,
            status=StageStatus.SUCCESS,
            start_time=datetime(2025, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
            log_content="BUILD SUCCESSFUL",
            env_vars={"DEP_VERSION": "1.0.0"},
            artifact_hashes={"dist/": "hash2"},
        ),
        Stage(
            name="test",
            index=2,
            status=StageStatus.SUCCESS,
            start_time=datetime(2025, 1, 1, 0, 2, 0, tzinfo=timezone.utc),
            log_content="All tests passed\nexit code 0",
            env_vars={"DEP_VERSION": "1.0.0"},
        ),
    ]
    return run


@pytest.fixture
def multi_failure_run() -> PipelineRun:
    """Create a pipeline run with multiple consecutive failures."""
    run = PipelineRun(run_id="multi-fail")
    run.stages = [
        Stage(
            name="checkout",
            index=0,
            status=StageStatus.SUCCESS,
            env_vars={"DEP_VERSION": "2.0.0", "PLATFORM": "linux"},
            artifact_hashes={"src/": "h1"},
        ),
        Stage(
            name="build",
            index=1,
            status=StageStatus.SUCCESS,
            log_content="Building...",
            env_vars={"DEP_VERSION": "2.0.0", "CC": "gcc", "GCC_VERSION": "12.2", "PLATFORM": "linux"},
            artifact_hashes={"build.o": "h2"},
        ),
        Stage(
            name="test",
            index=2,
            status=StageStatus.FAILURE,
            log_content="FAILED module-a/unit.test.js\n  AssertionError: expected true\n  at module-a/unit.test.js:10\nFAILED module-b/integration.test.js\n  TypeError: undefined is not a function\n  at module-b/integration.test.js:25\nexit code 1",
            env_vars={"DEP_VERSION": "2.0.0", "PLATFORM": "linux"},
        ),
        Stage(
            name="integration",
            index=3,
            status=StageStatus.FAILURE,
            log_content="FAILED integration/api.test.js\n  Error: Connection refused\n  at integration/api.test.js:15\nexit code 1",
            env_vars={"DEP_VERSION": "2.0.0", "PLATFORM": "darwin"},
        ),
        Stage(
            name="deploy",
            index=4,
            status=StageStatus.FAILURE,
            log_content="FATAL: deployment failed\n  Error: health check timeout\nexit code 1",
            env_vars={"DEP_VERSION": "2.0.0", "REDIS_URL": "redis://prod:6379", "NODE_OPTIONS": "--max-old-space-size=8192"},
        ),
    ]
    return run


@pytest.fixture
def env_diverge_run() -> PipelineRun:
    """Create a pipeline run with environment variable divergence between stages."""
    run = PipelineRun(run_id="env-diverge")
    run.stages = [
        Stage(
            name="setup",
            index=0,
            status=StageStatus.SUCCESS,
            env_vars={"PATH": "/usr/bin", "HOME": "/root", "CUSTOM_VAR": "v1"},
            artifact_hashes={},
        ),
        Stage(
            name="build",
            index=1,
            status=StageStatus.SUCCESS,
            env_vars={"PATH": "/usr/bin", "HOME": "/root", "CUSTOM_VAR": "v2", "SECRET_KEY": "abc123"},
            artifact_hashes={"output.bin": "hash_a"},
        ),
        Stage(
            name="test",
            index=2,
            status=StageStatus.FAILURE,
            log_content="FAILED test.js\nexit code 1",
            env_vars={"PATH": "/usr/bin", "HOME": "/root", "CUSTOM_VAR": "v2", "SECRET_KEY": "abc123", "CACHE_DIR": "/tmp/cache"},
        ),
    ]
    return run


@pytest.fixture
def artifact_mutation_run() -> PipelineRun:
    """Create a pipeline run where downstream stages modify upstream artifacts."""
    run = PipelineRun(run_id="artifact-mutation")
    run.stages = [
        Stage(
            name="checkout",
            index=0,
            status=StageStatus.SUCCESS,
            artifact_hashes={"compiled.o": "hash_original"},
        ),
        Stage(
            name="build",
            index=1,
            status=StageStatus.SUCCESS,
            artifact_hashes={"compiled.o": "hash_modified", "bundle.js": "hash_bundle"},
        ),
        Stage(
            name="test",
            index=2,
            status=StageStatus.FAILURE,
            log_content="FAILED test.js\nexit code 1",
            artifact_hashes={"compiled.o": "hash_modified"},
        ),
    ]
    return run
