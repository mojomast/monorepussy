"""Tests for snapshot diffing."""

import os
from datetime import datetime, timezone

import pytest

from ussy_snapshot.diff import diff_snapshots, format_diff, _diff_terminals, _diff_editor, _diff_environment
from ussy_snapshot.models import (
    Snapshot,
    SnapshotMetadata,
    TerminalState,
    EditorState,
    OpenFile,
    CursorPosition,
    ProcessRecord,
    EnvironmentState,
    MentalContext,
)
from ussy_snapshot.storage import save_snapshot


@pytest.fixture
def storage_dir(tmp_path):
    """Create a temporary storage directory."""
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    old_env = os.environ.get("SNAPSHOT_DIR")
    os.environ["SNAPSHOT_DIR"] = str(snap_dir)
    yield snap_dir
    if old_env is not None:
        os.environ["SNAPSHOT_DIR"] = old_env
    else:
        os.environ.pop("SNAPSHOT_DIR", None)


class TestDiffSnapshots:
    def test_diff_nonexistent_first(self, storage_dir):
        result = diff_snapshots("nonexistent1", "nonexistent2")
        assert "error" in result

    def test_diff_nonexistent_second(self, storage_dir):
        save_snapshot(Snapshot(name="snap1", metadata=SnapshotMetadata(name="snap1")))
        result = diff_snapshots("snap1", "nonexistent2")
        assert "error" in result

    def test_diff_identical_snapshots(self, storage_dir):
        snap = Snapshot(name="same1", metadata=SnapshotMetadata(name="same1"))
        save_snapshot(snap)
        snap2 = Snapshot(name="same2", metadata=SnapshotMetadata(name="same2"))
        save_snapshot(snap2)
        result = diff_snapshots("same1", "same2")
        assert "error" not in result
        assert "terminals" in result
        assert "editor" in result

    def test_diff_added_terminal(self, storage_dir):
        snap1 = Snapshot(name="no-term", metadata=SnapshotMetadata(name="no-term"))
        save_snapshot(snap1)
        snap2 = Snapshot(
            name="with-term",
            metadata=SnapshotMetadata(name="with-term"),
            terminals=[TerminalState(session_id="t1")],
        )
        save_snapshot(snap2)
        result = diff_snapshots("no-term", "with-term")
        assert "t1" in result["terminals"]["added"]

    def test_diff_removed_file(self, storage_dir):
        snap1 = Snapshot(
            name="with-file",
            metadata=SnapshotMetadata(name="with-file"),
            editor=EditorState(open_files=[OpenFile(path="main.py")]),
        )
        save_snapshot(snap1)
        snap2 = Snapshot(name="no-file", metadata=SnapshotMetadata(name="no-file"))
        save_snapshot(snap2)
        result = diff_snapshots("with-file", "no-file")
        assert "main.py" in result["editor"]["removed"]

    def test_diff_changed_env(self, storage_dir):
        snap1 = Snapshot(
            name="env1",
            metadata=SnapshotMetadata(name="env1"),
            environment=EnvironmentState(variables={"A": "1", "B": "2"}),
        )
        save_snapshot(snap1)
        snap2 = Snapshot(
            name="env2",
            metadata=SnapshotMetadata(name="env2"),
            environment=EnvironmentState(variables={"A": "1", "B": "3", "C": "4"}),
        )
        save_snapshot(snap2)
        result = diff_snapshots("env1", "env2")
        assert "C" in result["environment"]["added"]
        assert "B" in result["environment"]["changed"]


class TestDiffTerminals:
    def test_added_terminals(self):
        s1 = Snapshot(name="a")
        s2 = Snapshot(name="b", terminals=[TerminalState(session_id="new")])
        result = _diff_terminals(s1, s2)
        assert "new" in result["added"]

    def test_removed_terminals(self):
        s1 = Snapshot(name="a", terminals=[TerminalState(session_id="old")])
        s2 = Snapshot(name="b")
        result = _diff_terminals(s1, s2)
        assert "old" in result["removed"]

    def test_changed_directory(self):
        s1 = Snapshot(name="a", terminals=[TerminalState(session_id="t1", working_directory="/old")])
        s2 = Snapshot(name="b", terminals=[TerminalState(session_id="t1", working_directory="/new")])
        result = _diff_terminals(s1, s2)
        assert len(result["changed"]) == 1
        assert result["changed"][0]["session_id"] == "t1"


class TestDiffEditor:
    def test_added_files(self):
        s1 = Snapshot(name="a")
        s2 = Snapshot(name="b", editor=EditorState(open_files=[OpenFile(path="new.py")]))
        result = _diff_editor(s1, s2)
        assert "new.py" in result["added"]

    def test_cursor_change(self):
        s1 = Snapshot(name="a", editor=EditorState(open_files=[OpenFile(path="f.py", cursor=CursorPosition(line=1))]))
        s2 = Snapshot(name="b", editor=EditorState(open_files=[OpenFile(path="f.py", cursor=CursorPosition(line=42))]))
        result = _diff_editor(s1, s2)
        assert len(result["changed"]) == 1


class TestDiffEnvironment:
    def test_added_vars(self):
        s1 = Snapshot(name="a", environment=EnvironmentState(variables={"A": "1"}))
        s2 = Snapshot(name="b", environment=EnvironmentState(variables={"A": "1", "B": "2"}))
        result = _diff_environment(s1, s2)
        assert "B" in result["added"]

    def test_changed_vars(self):
        s1 = Snapshot(name="a", environment=EnvironmentState(variables={"X": "old"}))
        s2 = Snapshot(name="b", environment=EnvironmentState(variables={"X": "new"}))
        result = _diff_environment(s1, s2)
        assert "X" in result["changed"]
        assert result["changed"]["X"]["from"] == "old"
        assert result["changed"]["X"]["to"] == "new"


class TestFormatDiff:
    def test_format_error(self):
        result = format_diff({"error": "Not found"})
        assert "Error" in result

    def test_format_no_diff(self):
        result = format_diff({
            "name1": "a",
            "name2": "b",
            "terminals": {},
            "editor": {},
            "processes": {},
            "environment": {},
            "mental_context": {},
        })
        assert "No differences" in result

    def test_format_with_changes(self):
        result = format_diff({
            "name1": "a",
            "name2": "b",
            "terminals": {"added": ["t1"], "removed": [], "changed": []},
            "editor": {"added": ["main.py"], "removed": ["old.py"], "changed": []},
            "processes": {"added": ["python app.py"], "removed": []},
            "environment": {"added": {"NEW_VAR": "val"}, "removed": {}, "changed": {}},
            "mental_context": {"note": {"from": "old", "to": "new"}},
        })
        assert "t1" in result
        assert "main.py" in result
        assert "python app.py" in result
