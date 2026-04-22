"""Tests for the database module."""

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from ussy_calibre.db import CalibreDB
from ussy_calibre.models import (
    DriftObservation,
    RRObservation,
    TestResult,
    TestRun,
    TraceabilityLink,
)


class TestCalibreDB:
    __test__ = False


class TestDBInit:
    def test_creates_database(self, tmp_db_path):
        db = CalibreDB(tmp_db_path)
        _ = db.conn  # trigger init
        assert Path(tmp_db_path).exists()
        db.close()

    def test_close_and_reopen(self, tmp_db_path):
        db = CalibreDB(tmp_db_path)
        db.close()
        db2 = CalibreDB(tmp_db_path)
        _ = db2.conn
        db2.close()


class TestTestRuns:
    def test_insert_and_retrieve(self, tmp_db_path):
        db = CalibreDB(tmp_db_path)
        run = TestRun(
            test_name="test_1", module="mod1", suite="suite1",
            build_id="b1", environment="ci", result=TestResult.PASS,
            timestamp=datetime.now(timezone.utc), duration=1.5,
        )
        row_id = db.insert_test_run(run)
        assert row_id > 0

        results = db.get_test_runs(suite="suite1")
        assert len(results) == 1
        assert results[0].test_name == "test_1"
        assert results[0].result == TestResult.PASS
        db.close()

    def test_insert_multiple(self, tmp_db_path):
        db = CalibreDB(tmp_db_path)
        runs = [
            TestRun(
                test_name=f"test_{i}", module="mod", suite="s",
                build_id="b1", environment="ci", result=TestResult.PASS,
            )
            for i in range(5)
        ]
        db.insert_test_runs(runs)
        results = db.get_test_runs(suite="s")
        assert len(results) == 5
        db.close()

    def test_filter_by_test_name(self, tmp_db_path):
        db = CalibreDB(tmp_db_path)
        db.insert_test_run(
            TestRun(
                test_name="test_a", module="m", suite="s",
                build_id="b1", environment="ci", result=TestResult.PASS,
            )
        )
        db.insert_test_run(
            TestRun(
                test_name="test_b", module="m", suite="s",
                build_id="b1", environment="ci", result=TestResult.FAIL,
            )
        )
        results = db.get_test_runs(test_name="test_a")
        assert len(results) == 1
        assert results[0].test_name == "test_a"
        db.close()

    def test_get_unique_builds(self, tmp_db_path):
        db = CalibreDB(tmp_db_path)
        for build in ["b1", "b2", "b3"]:
            db.insert_test_run(
                TestRun(
                    test_name="t", module="m", suite="s",
                    build_id=build, environment="ci", result=TestResult.PASS,
                )
            )
        builds = db.get_unique_builds(suite="s")
        assert len(builds) == 3
        db.close()

    def test_get_unique_environments(self, tmp_db_path):
        db = CalibreDB(tmp_db_path)
        for env in ["ci", "staging", "local"]:
            db.insert_test_run(
                TestRun(
                    test_name="t", module="m", suite="s",
                    build_id="b1", environment=env, result=TestResult.PASS,
                )
            )
        envs = db.get_unique_environments(suite="s")
        assert len(envs) == 3
        db.close()


class TestRRObservations:
    def test_insert_and_retrieve(self, tmp_db_path):
        db = CalibreDB(tmp_db_path)
        obs = RRObservation(
            build_id="b1", environment="ci", test_name="t1",
            replicate=1, value=0.95,
        )
        db.insert_rr_observation(obs)
        results = db.get_rr_observations(test_name="t1")
        assert len(results) == 1
        assert results[0].value == 0.95
        db.close()


class TestDriftObservations:
    def test_insert_and_retrieve(self, tmp_db_path):
        db = CalibreDB(tmp_db_path)
        obs = DriftObservation(
            test_name="t1",
            timestamp=datetime.now(timezone.utc),
            observed_value=0.9,
        )
        db.insert_drift_observation(obs)
        results = db.get_drift_observations(test_name="t1")
        assert len(results) == 1
        assert results[0].observed_value == 0.9
        db.close()


class TestTraceabilityLinks:
    def test_insert_and_retrieve(self, tmp_db_path):
        db = CalibreDB(tmp_db_path)
        link = TraceabilityLink(
            test_name="t1",
            level="specification",
            reference="REQ-001",
            uncertainty=0.05,
            last_verified=datetime.now(timezone.utc),
        )
        db.insert_traceability_link(link)
        results = db.get_traceability_links(test_name="t1")
        assert len(results) == 1
        assert results[0].reference == "REQ-001"
        db.close()


class TestJsonImport:
    def test_import_pytest_json(self, tmp_db_path, tmp_path):
        db = CalibreDB(tmp_db_path)
        data = {
            "build_id": "b1",
            "environment": "ci",
            "tests": [
                {"nodeid": "tests/test_foo.py::test_bar", "outcome": "passed", "duration": 1.2},
                {"nodeid": "tests/test_baz.py::test_qux", "outcome": "failed", "duration": 0.3},
            ],
        }
        json_file = tmp_path / "results.json"
        json_file.write_text(json.dumps(data))

        count = db.import_json_results(str(json_file))
        assert count == 2

        runs = db.get_test_runs(build_id="b1")
        assert len(runs) == 2
        db.close()
