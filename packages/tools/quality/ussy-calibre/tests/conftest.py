"""Test fixtures and shared utilities for Calibre tests."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List

import pytest

from calibre.models import (
    CapabilitySpec,
    DriftObservation,
    RRObservation,
    TestResult,
    TestRun,
    TraceabilityLink,
    UncertaintySource,
    UncertaintyType,
)


@pytest.fixture
def tmp_db_path(tmp_path):
    """Provide a temporary database path."""
    return str(tmp_path / "test_calibre.db")


@pytest.fixture
def sample_test_runs() -> List[TestRun]:
    """Create a sample set of test runs."""
    runs = []
    base_time = datetime.now(timezone.utc) - timedelta(days=7)

    tests = [
        ("test_login", "auth", "auth"),
        ("test_logout", "auth", "auth"),
        ("test_get_users", "api", "api"),
        ("test_create_user", "api", "api"),
    ]
    builds = ["build-1", "build-2", "build-3", "build-4", "build-5"]
    envs = ["ci-linux", "ci-macos", "staging"]

    for test_name, module, suite in tests:
        for i, build in enumerate(builds):
            for j, env in enumerate(envs):
                # Make some tests flaky in specific envs
                if test_name == "test_login" and env == "staging":
                    result = TestResult.FAIL
                elif test_name == "test_logout" and i % 3 == 0:
                    result = TestResult.FAIL
                else:
                    result = TestResult.PASS

                runs.append(
                    TestRun(
                        test_name=test_name,
                        module=module,
                        suite=suite,
                        build_id=build,
                        environment=env,
                        result=result,
                        timestamp=base_time + timedelta(days=i, hours=j),
                        duration=0.5,
                    )
                )

    return runs


@pytest.fixture
def sample_rr_observations() -> List[RRObservation]:
    """Create sample R&R observations with meaningful variance."""
    observations = []
    builds = ["build-1", "build-2", "build-3", "build-4", "build-5"]
    envs = ["ci-linux", "ci-macos", "staging"]

    # Build 1 and 2 are "good" (higher values), 3-5 are "bad" (lower)
    for i, build in enumerate(builds):
        for env in envs:
            for rep in range(3):
                base = 0.9 if i < 2 else 0.6
                # Add noise
                import random
                random.seed(i * 100 + hash(env) + rep)
                value = base + random.uniform(-0.1, 0.1)
                value = max(0.0, min(1.0, value))

                observations.append(
                    RRObservation(
                        build_id=build,
                        environment=env,
                        test_name="test_example",
                        replicate=rep + 1,
                        value=value,
                    )
                )

    return observations


@pytest.fixture
def sample_drift_observations() -> List[DriftObservation]:
    """Create sample drift observations with linear drift."""
    observations = []
    base_time = datetime.now(timezone.utc) - timedelta(days=30)

    for day in range(30):
        ts = base_time + timedelta(days=day)
        # Simulate slow drift: value decreases over time
        value = 0.95 - 0.003 * day
        observations.append(
            DriftObservation(
                test_name="test_drifty",
                timestamp=ts,
                observed_value=value,
            )
        )

    return observations


@pytest.fixture
def sample_traceability_links() -> List[TraceabilityLink]:
    """Create sample traceability chain."""
    now = datetime.now(timezone.utc)
    return [
        TraceabilityLink(
            test_name="test_login",
            level="stakeholder_need",
            reference="REQ-001",
            uncertainty=0.05,
            last_verified=now - timedelta(days=10),
            review_interval_days=90,
        ),
        TraceabilityLink(
            test_name="test_login",
            level="specification",
            reference="SPEC-01",
            uncertainty=0.03,
            last_verified=now - timedelta(days=10),
            review_interval_days=90,
        ),
        TraceabilityLink(
            test_name="test_login",
            level="acceptance_criteria",
            reference="AC-01",
            uncertainty=0.02,
            last_verified=now - timedelta(days=200),
            review_interval_days=180,
        ),
        TraceabilityLink(
            test_name="test_login",
            level="test_plan",
            reference="TP-01",
            uncertainty=0.01,
            last_verified=now - timedelta(days=5),
            review_interval_days=90,
        ),
        TraceabilityLink(
            test_name="test_login",
            level="assertion",
            reference="assert status==200",
            uncertainty=0.01,
            last_verified=now - timedelta(days=5),
            review_interval_days=90,
        ),
    ]


@pytest.fixture
def sample_uncertainty_sources() -> List[UncertaintySource]:
    """Create sample uncertainty sources."""
    return [
        UncertaintySource(
            name="flakiness",
            uncertainty_value=0.05,
            sensitivity_coefficient=1.0,
        ),
        UncertaintySource(
            name="environment_variance",
            uncertainty_value=0.03,
            sensitivity_coefficient=0.8,
            correlation_with="flakiness",
            correlation_coefficient=0.3,
        ),
        UncertaintySource(
            name="timing_sensitivity",
            uncertainty_value=0.02,
            sensitivity_coefficient=0.5,
        ),
        UncertaintySource(
            name="data_staleness",
            uncertainty_value=0.01,
            sensitivity_coefficient=0.3,
        ),
    ]
