"""Tests for mushin.journal module."""

from datetime import datetime, timezone, timedelta

import pytest

from ussy_mushin.journal import Journal, JournalEntry


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


class TestJournalEntry:
    def test_creation(self):
        entry = JournalEntry(expression="x = 1", output="1")
        assert entry.expression == "x = 1"
        assert entry.output == "1"
        assert entry.result_type == "success"
        assert entry.timestamp  # auto-generated

    def test_custom_result_type(self):
        entry = JournalEntry(expression="1/0", output="ZeroDivisionError", result_type="error")
        assert entry.result_type == "error"

    def test_auto_timestamp(self):
        entry = JournalEntry(expression="test")
        assert entry.timestamp  # not empty
        # Should be parseable
        dt = datetime.fromisoformat(entry.timestamp)
        assert dt.tzinfo is not None

    def test_explicit_timestamp(self):
        entry = JournalEntry(expression="test", timestamp="2025-01-01T00:00:00+00:00")
        assert entry.timestamp == "2025-01-01T00:00:00+00:00"

    def test_to_dict_roundtrip(self):
        entry = JournalEntry(expression="print('hi')", output="hi", result_type="success", context={"file": "a.py"})
        d = entry.to_dict()
        restored = JournalEntry.from_dict(d)
        assert restored.expression == entry.expression
        assert restored.output == entry.output
        assert restored.result_type == entry.result_type
        assert restored.context == {"file": "a.py"}

    def test_from_dict_defaults(self):
        d = {"expression": "x"}
        entry = JournalEntry.from_dict(d)
        assert entry.output == ""
        assert entry.result_type == "success"
        assert entry.context == {}


class TestJournal:
    def test_create_journal(self, project_dir):
        j = Journal(project_dir, "ws-001")
        assert len(j) == 0

    def test_record_entry(self, project_dir):
        j = Journal(project_dir, "ws-002")
        entry = j.record("import os", "imported os")
        assert len(j) == 1
        assert entry.expression == "import os"
        assert entry.output == "imported os"

    def test_record_multiple(self, project_dir):
        j = Journal(project_dir, "ws-003")
        j.record("a = 1")
        j.record("b = 2")
        j.record("c = a + b")
        assert len(j) == 3

    def test_persistence(self, project_dir):
        j1 = Journal(project_dir, "ws-004")
        j1.record("x = 42", "42")
        # Create a new journal instance — should load from disk
        j2 = Journal(project_dir, "ws-004")
        assert len(j2) == 1
        assert j2[0].expression == "x = 42"

    def test_last(self, project_dir):
        j = Journal(project_dir, "ws-005")
        assert j.last() is None
        j.record("first")
        j.record("second")
        assert j.last().expression == "second"

    def test_search(self, project_dir):
        j = Journal(project_dir, "ws-006")
        j.record("import pandas", "ok")
        j.record("df = pd.DataFrame()", "DataFrame")
        j.record("import numpy", "ok")
        results = j.search("pandas")
        assert len(results) == 1
        assert results[0].expression == "import pandas"

    def test_search_case_insensitive(self, project_dir):
        j = Journal(project_dir, "ws-007")
        j.record("Print('Hi')", "Hi")
        results = j.search("print")
        assert len(results) == 1

    def test_filter_by_type(self, project_dir):
        j = Journal(project_dir, "ws-008")
        j.record("x = 1", result_type="success")
        j.record("1/0", output="error", result_type="error")
        j.record("info msg", result_type="info")
        errors = j.filter_by_type("error")
        assert len(errors) == 1
        assert errors[0].expression == "1/0"

    def test_filter_by_time_range(self, project_dir):
        j = Journal(project_dir, "ws-009")
        j.record("early", context={"fake": True})
        j.record("late")
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)
        results = j.filter_by_time_range(start, end)
        assert len(results) == 2

    def test_iteration(self, project_dir):
        j = Journal(project_dir, "ws-010")
        j.record("a")
        j.record("b")
        entries = list(j)
        assert len(entries) == 2

    def test_getitem(self, project_dir):
        j = Journal(project_dir, "ws-011")
        j.record("first", "1")
        j.record("second", "2")
        assert j[0].expression == "first"
        assert j[1].expression == "second"

    def test_replay_no_executor(self, project_dir):
        j = Journal(project_dir, "ws-012")
        j.record("x = 1", "1")
        j.record("y = 2", "2")
        results = j.replay()
        assert len(results) == 2
        assert results[0] == ("x = 1", "1")

    def test_replay_with_executor(self, project_dir):
        j = Journal(project_dir, "ws-013")
        j.record("2 + 2")

        def executor(expr):
            return (str(eval(expr)), "success")

        results = j.replay(executor)
        assert results[0] == ("2 + 2", "4")

    def test_replay_executor_error(self, project_dir):
        j = Journal(project_dir, "ws-014")
        j.record("invalid syntax !!!")

        def executor(expr):
            raise SyntaxError("bad")

        results = j.replay(executor)
        assert "REPLAY ERROR" in results[0][1]

    def test_export_text(self, project_dir):
        j = Journal(project_dir, "ws-015")
        j.record("print('hello')", "hello")
        text = j.export_text()
        assert "print('hello')" in text
        assert "hello" in text

    def test_context_preserved(self, project_dir):
        j = Journal(project_dir, "ws-016")
        j.record("x = 1", context={"file": "main.py", "line": 42})
        entry = j[0]
        assert entry.context["file"] == "main.py"
        assert entry.context["line"] == 42

    def test_empty_output(self, project_dir):
        j = Journal(project_dir, "ws-017")
        j.record("pass", output="")
        assert j[0].output == ""
