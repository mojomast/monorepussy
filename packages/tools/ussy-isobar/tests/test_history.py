"""Tests for isobar.history module."""

import pytest
from datetime import datetime, timezone, timedelta

from ussy_isobar.fields import AtmosphericField, AtmosphericProfile
from ussy_isobar.scanner import ScanResult, FileHistory, FileCommit
from ussy_isobar.history import (
    compute_historical_fields, compare_sprints, format_history,
)


def _make_scan_with_commits():
    """Create a scan result with commits over time."""
    now = datetime.now(timezone.utc)
    result = ScanResult(root="/tmp")

    commits_a = [
        FileCommit(commit_hash="a1", author="x",
                   timestamp=now - timedelta(days=45), message="old commit",
                   files_changed=["test.py"]),
        FileCommit(commit_hash="a2", author="x",
                   timestamp=now - timedelta(days=20), message="recent commit",
                   files_changed=["test.py"]),
        FileCommit(commit_hash="a3", author="x",
                   timestamp=now - timedelta(days=5), message="fix bug",
                   files_changed=["test.py"]),
    ]
    result.file_histories["test.py"] = FileHistory(filepath="test.py", commits=commits_a)
    result.import_graph = {}
    result.co_changes = {}

    return result


class TestComputeHistoricalFields:
    def test_basic_history(self):
        scan = _make_scan_with_commits()
        history = compute_historical_fields(scan, period_days=30, interval_days=7)
        assert len(history) > 0

    def test_history_entries_have_timestamps(self):
        scan = _make_scan_with_commits()
        history = compute_historical_fields(scan, period_days=14, interval_days=7)
        for timestamp, field in history:
            assert isinstance(timestamp, datetime)
            assert isinstance(field, AtmosphericField)


class TestCompareSprints:
    def test_same_field(self):
        field_a = AtmosphericField()
        field_a.profiles["test.py"] = AtmosphericProfile(
            filepath="test.py", temperature=50.0, pressure=20.0, humidity=60.0,
        )
        field_b = AtmosphericField()
        field_b.profiles["test.py"] = AtmosphericProfile(
            filepath="test.py", temperature=70.0, pressure=25.0, humidity=70.0,
        )
        report = compare_sprints(field_a, field_b, "Sprint 1", "Sprint 2")
        assert "WEATHER COMPARISON" in report
        assert "Sprint 1" in report
        assert "Sprint 2" in report

    def test_no_common_files(self):
        field_a = AtmosphericField()
        field_a.profiles["a.py"] = AtmosphericProfile(filepath="a.py", temperature=50.0)
        field_b = AtmosphericField()
        field_b.profiles["b.py"] = AtmosphericProfile(filepath="b.py", temperature=50.0)
        report = compare_sprints(field_a, field_b)
        assert "No common files" in report


class TestFormatHistory:
    def test_empty_history(self):
        report = format_history([])
        assert "No historical data" in report

    def test_with_data(self):
        now = datetime.now(timezone.utc)
        field = AtmosphericField()
        field.profiles["test.py"] = AtmosphericProfile(
            filepath="test.py", temperature=45.0,
        )
        history = [(now, field)]
        report = format_history(history)
        assert "HISTORICAL WEATHER" in report
