"""Tests for core snapshot operations."""

import os
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from ussy_snapshot.core import (
    save,
    load,
    new,
    peek,
    tag,
    untag,
    format_snapshot_list,
    _format_age,
)
from ussy_snapshot.models import Snapshot, SnapshotMetadata, MentalContext
from ussy_snapshot.storage import save_snapshot, load_snapshot, snapshot_exists


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


class TestSave:
    def test_save_creates_snapshot(self, storage_dir):
        snap = save("test-save", note="test note")
        assert snap.name == "test-save"
        assert snapshot_exists("test-save")

    def test_save_with_note(self, storage_dir):
        snap = save("note-test", note="Was about to wire up callback")
        loaded = load_snapshot("note-test")
        assert loaded.mental_context.note == "Was about to wire up callback"

    def test_save_captures_terminals(self, storage_dir):
        snap = save("terminal-test")
        assert len(snap.terminals) >= 1  # At least current terminal

    def test_save_captures_environment(self, storage_dir):
        snap = save("env-test")
        assert len(snap.environment.variables) > 0

    def test_save_captures_metadata(self, storage_dir):
        snap = save("meta-test")
        assert snap.metadata.name == "meta-test"
        assert snap.metadata.created_at != ""

    def test_save_overwrite(self, storage_dir):
        save("overwrite-test", note="first")
        save("overwrite-test", note="second")
        loaded = load_snapshot("overwrite-test")
        assert loaded.mental_context.note == "second"


class TestLoad:
    def test_load_existing(self, storage_dir):
        save("load-test", note="test note")
        snap = load("load-test", dry_run=True)
        assert snap is not None
        assert snap.name == "load-test"

    def test_load_nonexistent(self, storage_dir):
        snap = load("no-such-snap", dry_run=True)
        assert snap is None


class TestNew:
    def test_new_creates_minimal_snapshot(self, storage_dir):
        snap = new("clean-test")
        assert snap.name == "clean-test"
        assert snapshot_exists("clean-test")

    def test_new_has_clean_context(self, storage_dir):
        snap = new("clean-ctx")
        assert snap.mental_context.note == "Clean environment"


class TestPeek:
    def test_peek_existing(self, storage_dir):
        save("peek-test", note="peek this")
        result = peek("peek-test")
        assert result is not None
        assert result["name"] == "peek-test"
        assert result["note"] == "peek this"

    def test_peek_nonexistent(self, storage_dir):
        result = peek("no-such-snap")
        assert result is None

    def test_peek_includes_terminals(self, storage_dir):
        save("peek-term")
        result = peek("peek-term")
        assert "terminals" in result

    def test_peek_includes_env_count(self, storage_dir):
        save("peek-env")
        result = peek("peek-env")
        assert "env_var_count" in result
        assert result["env_var_count"] > 0


class TestTag:
    def test_tag_adds_tag(self, storage_dir):
        save("tag-test")
        result = tag("tag-test", "milestone-v1")
        assert result is True
        loaded = load_snapshot("tag-test")
        assert "milestone-v1" in loaded.metadata.tags

    def test_tag_no_duplicate(self, storage_dir):
        save("dup-tag")
        tag("dup-tag", "same-tag")
        tag("dup-tag", "same-tag")
        loaded = load_snapshot("dup-tag")
        assert loaded.metadata.tags.count("same-tag") == 1

    def test_tag_nonexistent(self, storage_dir):
        result = tag("no-such-snap", "tag")
        assert result is False


class TestUntag:
    def test_untag_removes_tag(self, storage_dir):
        save("untag-test")
        tag("untag-test", "remove-me")
        result = untag("untag-test", "remove-me")
        assert result is True
        loaded = load_snapshot("untag-test")
        assert "remove-me" not in loaded.metadata.tags

    def test_untag_nonexistent(self, storage_dir):
        result = untag("no-such-snap", "tag")
        assert result is False


class TestFormatSnapshotList:
    def test_empty_list(self):
        result = format_snapshot_list([])
        assert "No snapshots" in result

    def test_with_snapshots(self):
        snaps = [
            SnapshotMetadata(name="test-snap", terminal_count=2, file_count=5, process_count=1),
        ]
        result = format_snapshot_list(snaps)
        assert "test-snap" in result

    def test_verbose(self):
        snaps = [
            SnapshotMetadata(name="verbose-snap", created_at=datetime.now(timezone.utc).isoformat()),
        ]
        result = format_snapshot_list(snaps, verbose=True)
        assert "Created:" in result

    def test_with_tags(self):
        snaps = [
            SnapshotMetadata(name="tagged", tags=["milestone", "release"]),
        ]
        result = format_snapshot_list(snaps)
        assert "milestone" in result
        assert "release" in result

    def test_with_note_preview(self):
        snaps = [
            SnapshotMetadata(name="noted", note_preview="Was about to type..."),
        ]
        result = format_snapshot_list(snaps)
        assert "Was about to type" in result


class TestFormatAge:
    def test_just_now(self):
        now = datetime.now(timezone.utc).isoformat()
        assert _format_age(now) == "just now"

    def test_minutes_ago(self):
        age = (datetime.now(timezone.utc) - __import__("datetime").timedelta(minutes=5)).isoformat()
        assert "m ago" in _format_age(age)

    def test_hours_ago(self):
        age = (datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=3)).isoformat()
        assert "h ago" in _format_age(age)

    def test_days_ago(self):
        age = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=5)).isoformat()
        assert "d ago" in _format_age(age)

    def test_months_ago(self):
        age = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=60)).isoformat()
        assert "mo ago" in _format_age(age)

    def test_years_ago(self):
        age = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=400)).isoformat()
        assert "y ago" in _format_age(age)

    def test_invalid_timestamp(self):
        result = _format_age("not-a-date")
        assert result == "not-a-date"
