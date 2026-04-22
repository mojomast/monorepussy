"""Tests for snapshot storage."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ussy_snapshot.models import Snapshot, SnapshotMetadata, TerminalState, MentalContext, OpenFile, EditorState
from ussy_snapshot.storage import (
    save_snapshot,
    load_snapshot,
    load_metadata,
    list_snapshots,
    delete_snapshot,
    snapshot_exists,
    get_snapshot_size,
)


@pytest.fixture
def storage_dir(tmp_path):
    """Create a temporary storage directory and set SNAPSHOT_DIR."""
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    old_env = os.environ.get("SNAPSHOT_DIR")
    os.environ["SNAPSHOT_DIR"] = str(snap_dir)
    yield snap_dir
    if old_env is not None:
        os.environ["SNAPSHOT_DIR"] = old_env
    else:
        os.environ.pop("SNAPSHOT_DIR", None)


@pytest.fixture
def sample_snapshot():
    """Create a sample snapshot for testing."""
    return Snapshot(
        name="test-snap",
        metadata=SnapshotMetadata(name="test-snap"),
        terminals=[TerminalState(session_id="t1", working_directory="/tmp")],
        mental_context=MentalContext(note="test note"),
    )


class TestSaveSnapshot:
    def test_save_creates_directory(self, storage_dir, sample_snapshot):
        path = save_snapshot(sample_snapshot)
        assert path.exists()
        assert path.is_dir()

    def test_save_creates_snapshot_json(self, storage_dir, sample_snapshot):
        save_snapshot(sample_snapshot)
        snap_file = storage_dir / "test-snap" / "snapshot.json"
        assert snap_file.exists()
        data = json.loads(snap_file.read_text())
        assert data["name"] == "test-snap"

    def test_save_creates_metadata_json(self, storage_dir, sample_snapshot):
        save_snapshot(sample_snapshot)
        meta_file = storage_dir / "test-snap" / "metadata.json"
        assert meta_file.exists()
        data = json.loads(meta_file.read_text())
        assert data["name"] == "test-snap"

    def test_save_updates_counts(self, storage_dir):
        snap = Snapshot(
            name="counted-snap",
            terminals=[TerminalState(session_id="t1"), TerminalState(session_id="t2")],
            editor=EditorState(open_files=[OpenFile(path="a.py"), OpenFile(path="b.py"), OpenFile(path="c.py")]),
        )
        save_snapshot(snap)
        loaded = load_snapshot("counted-snap")
        assert loaded.metadata.terminal_count == 2
        assert loaded.metadata.file_count == 3


class TestLoadSnapshot:
    def test_load_existing(self, storage_dir, sample_snapshot):
        save_snapshot(sample_snapshot)
        loaded = load_snapshot("test-snap")
        assert loaded is not None
        assert loaded.name == "test-snap"

    def test_load_nonexistent(self, storage_dir):
        loaded = load_snapshot("no-such-snap")
        assert loaded is None

    def test_load_preserves_data(self, storage_dir):
        snap = Snapshot(
            name="preserve-test",
            terminals=[TerminalState(session_id="t1", working_directory="/home")],
            mental_context=MentalContext(note="important note"),
        )
        save_snapshot(snap)
        loaded = load_snapshot("preserve-test")
        assert loaded.terminals[0].working_directory == "/home"
        assert loaded.mental_context.note == "important note"


class TestLoadMetadata:
    def test_load_metadata(self, storage_dir, sample_snapshot):
        save_snapshot(sample_snapshot)
        meta = load_metadata("test-snap")
        assert meta is not None
        assert meta.name == "test-snap"

    def test_load_metadata_nonexistent(self, storage_dir):
        meta = load_metadata("no-such-snap")
        assert meta is None


class TestListSnapshots:
    def test_list_empty(self, storage_dir):
        snapshots = list_snapshots()
        assert snapshots == []

    def test_list_multiple(self, storage_dir):
        for name in ["alpha", "beta", "gamma"]:
            save_snapshot(Snapshot(name=name, metadata=SnapshotMetadata(name=name)))
        snapshots = list_snapshots()
        assert len(snapshots) == 3

    def test_list_sort_by_name(self, storage_dir):
        for name in ["gamma", "alpha", "beta"]:
            save_snapshot(Snapshot(name=name, metadata=SnapshotMetadata(name=name)))
        snapshots = list_snapshots(sort="name")
        names = [s.name for s in snapshots]
        assert names == ["alpha", "beta", "gamma"]

    def test_list_sort_by_age(self, storage_dir):
        for name in ["first", "second", "third"]:
            save_snapshot(Snapshot(name=name, metadata=SnapshotMetadata(name=name)))
        snapshots = list_snapshots(sort="age")
        # Newest first
        assert snapshots[0].name == "third"

    def test_list_sort_by_size(self, storage_dir):
        # Create snapshots of different sizes
        save_snapshot(Snapshot(name="small", metadata=SnapshotMetadata(name="small")))
        big = Snapshot(
            name="big",
            metadata=SnapshotMetadata(name="big"),
            mental_context=MentalContext(note="x" * 500),
        )
        save_snapshot(big)
        snapshots = list_snapshots(sort="size")
        # Biggest first
        assert snapshots[0].name == "big"


class TestDeleteSnapshot:
    def test_delete_existing(self, storage_dir, sample_snapshot):
        save_snapshot(sample_snapshot)
        assert snapshot_exists("test-snap")
        result = delete_snapshot("test-snap")
        assert result is True
        assert not snapshot_exists("test-snap")

    def test_delete_nonexistent(self, storage_dir):
        result = delete_snapshot("no-such-snap")
        assert result is False


class TestSnapshotExists:
    def test_exists(self, storage_dir, sample_snapshot):
        save_snapshot(sample_snapshot)
        assert snapshot_exists("test-snap") is True

    def test_not_exists(self, storage_dir):
        assert snapshot_exists("no-such-snap") is False


class TestGetSnapshotSize:
    def test_size_existing(self, storage_dir, sample_snapshot):
        save_snapshot(sample_snapshot)
        size = get_snapshot_size("test-snap")
        assert size > 0

    def test_size_nonexistent(self, storage_dir):
        size = get_snapshot_size("no-such-snap")
        assert size == 0
