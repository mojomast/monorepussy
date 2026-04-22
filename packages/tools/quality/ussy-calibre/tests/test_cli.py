"""Tests for the CLI module."""

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from ussy_calibre.cli_measure import build_parser, main
from ussy_calibre.db import CalibreDB
from ussy_calibre.models import (
    DriftObservation,
    TestResult,
    TestRun,
    TraceabilityLink,
)


@pytest.fixture
def seeded_db(tmp_path):
    """Create and seed a temporary database."""
    db_path = str(tmp_path / "test.db")
    db = CalibreDB(db_path)

    # Insert some test runs
    runs = []
    for i in range(10):
        for env in ["ci", "staging"]:
            result = TestResult.PASS if i % 3 != 0 else TestResult.FAIL
            runs.append(
                TestRun(
                    test_name="test_example",
                    module="tests/mod",
                    suite="example_suite",
                    build_id=f"build-{i}",
                    environment=env,
                    result=result,
                    timestamp=datetime.now(timezone.utc) - timedelta(days=10 - i),
                    duration=1.0,
                )
            )
    db.insert_test_runs(runs)

    # Insert drift observations
    drift_obs = []
    base = datetime.now(timezone.utc) - timedelta(days=15)
    for day in range(15):
        drift_obs.append(
            DriftObservation(
                test_name="example_suite",
                timestamp=base + timedelta(days=day),
                observed_value=0.95 - 0.003 * day,
            )
        )
    db.insert_drift_observations(drift_obs)

    # Insert traceability links
    links = [
        TraceabilityLink(
            test_name="test_example",
            level="specification",
            reference="REQ-1",
            uncertainty=0.05,
            last_verified=datetime.now(timezone.utc),
            review_interval_days=90,
        ),
    ]
    db.insert_traceability_links(links)
    db.close()

    return db_path


class TestBuildParser:
    def test_parser_creation(self):
        parser = build_parser()
        assert parser is not None

    def test_version(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])


class TestCLIBudget:
    def test_budget_command(self, seeded_db, capsys):
        main(["--db", seeded_db, "budget", "tests/mod"])
        captured = capsys.readouterr()
        assert "Uncertainty Budget" in captured.out

    def test_budget_no_data(self, tmp_path, capsys):
        db_path = str(tmp_path / "empty.db")
        main(["--db", db_path, "budget", "nonexistent"])
        captured = capsys.readouterr()
        assert "No test runs found" in captured.out


class TestCLIRR:
    def test_rr_command(self, seeded_db, capsys):
        main(["--db", seeded_db, "rr", "example_suite"])
        captured = capsys.readouterr()
        assert "Gauge R&R Study" in captured.out


class TestCLICapability:
    def test_capability_command(self, seeded_db, capsys):
        main(["--db", seeded_db, "capability", "example_suite", "--usl", "1.0", "--lsl", "0.8"])
        captured = capsys.readouterr()
        assert "Capability Analysis" in captured.out


class TestCLIClassify:
    def test_classify_command(self, seeded_db, capsys):
        main(["--db", seeded_db, "classify", "test_example"])
        captured = capsys.readouterr()
        assert "Uncertainty Classification" in captured.out


class TestCLIDrift:
    def test_drift_command(self, seeded_db, capsys):
        main(["--db", seeded_db, "drift", "example_suite"])
        captured = capsys.readouterr()
        assert "Drift Analysis" in captured.out


class TestCLITrace:
    def test_trace_command(self, seeded_db, capsys):
        main(["--db", seeded_db, "trace", "test_example"])
        captured = capsys.readouterr()
        assert "Traceability Audit" in captured.out


class TestCLIReport:
    def test_report_command(self, seeded_db, capsys):
        main(["--db", seeded_db, "report", "example_suite"])
        captured = capsys.readouterr()
        assert "METROLOGICAL CHARACTERIZATION REPORT" in captured.out


class TestCLISeed:
    def test_seed_command(self, tmp_path, capsys):
        db_path = str(tmp_path / "seeded.db")
        main(["--db", db_path, "seed"])
        captured = capsys.readouterr()
        assert "Seeded database" in captured.out


class TestCLIImport:
    def test_import_command(self, tmp_path, capsys):
        # Create a JSON file
        data = {
            "build_id": "b1",
            "environment": "ci",
            "tests": [
                {"nodeid": "tests/test.py::test_a", "outcome": "passed", "duration": 1.0},
            ],
        }
        json_file = tmp_path / "results.json"
        json_file.write_text(json.dumps(data))

        db_path = str(tmp_path / "import.db")
        main(["--db", db_path, "import", str(json_file)])
        captured = capsys.readouterr()
        assert "Imported 1" in captured.out


class TestCLIHelp:
    def test_no_command(self, capsys):
        main([])
        captured = capsys.readouterr()
        assert "calibre" in captured.out.lower() or "usage" in captured.out.lower()
