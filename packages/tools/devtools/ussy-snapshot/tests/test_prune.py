"""Tests for snapshot pruning."""

import os
from datetime import datetime, timezone, timedelta

import pytest

from snapshot.prune import (
    parse_duration,
    prune_snapshots,
    get_storage_usage,
    _human_size,
)
from snapshot.models import Snapshot, SnapshotMetadata
from snapshot.storage import save_snapshot


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


class TestParseDuration:
    def test_days(self):
        delta = parse_duration("7d")
        assert delta == timedelta(days=7)

    def test_hours(self):
        delta = parse_duration("2h")
        assert delta == timedelta(hours=2)

    def test_minutes(self):
        delta = parse_duration("30m")
        assert delta == timedelta(minutes=30)

    def test_weeks(self):
        delta = parse_duration("1w")
        assert delta == timedelta(weeks=1)

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            parse_duration("invalid")

    def test_invalid_unit(self):
        with pytest.raises(ValueError):
            parse_duration("5x")

    def test_zero(self):
        delta = parse_duration("0d")
        assert delta == timedelta(days=0)


class TestPruneSnapshots:
    def test_prune_empty(self, storage_dir):
        deleted = prune_snapshots(older_than="7d")
        assert deleted == []

    def test_prune_by_age(self, storage_dir):
        # Create an "old" snapshot
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        save_snapshot(Snapshot(
            name="old-snap",
            metadata=SnapshotMetadata(name="old-snap", created_at=old_time),
        ))
        # Create a "new" snapshot
        save_snapshot(Snapshot(
            name="new-snap",
            metadata=SnapshotMetadata(name="new-snap"),
        ))
        deleted = prune_snapshots(older_than="7d")
        assert "old-snap" in deleted
        assert "new-snap" not in deleted

    def test_prune_keep_last(self, storage_dir):
        for i in range(5):
            old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
            save_snapshot(Snapshot(
                name=f"snap-{i}",
                metadata=SnapshotMetadata(name=f"snap-{i}", created_at=old_time),
            ))
        deleted = prune_snapshots(older_than="7d", keep_last=2)
        # Should keep 2 most recent
        assert len(deleted) == 3

    def test_prune_dry_run(self, storage_dir):
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        save_snapshot(Snapshot(
            name="old-snap",
            metadata=SnapshotMetadata(name="old-snap", created_at=old_time),
        ))
        deleted = prune_snapshots(older_than="7d", dry_run=True)
        assert "old-snap" in deleted
        # Should still exist
        from snapshot.storage import snapshot_exists
        assert snapshot_exists("old-snap")

    def test_prune_with_tags(self, storage_dir):
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        save_snapshot(Snapshot(
            name="tagged-snap",
            metadata=SnapshotMetadata(name="tagged-snap", created_at=old_time, tags=["milestone"]),
        ))
        save_snapshot(Snapshot(
            name="untagged-snap",
            metadata=SnapshotMetadata(name="untagged-snap", created_at=old_time),
        ))
        deleted = prune_snapshots(older_than="7d", exclude_tags=["milestone"])
        assert "tagged-snap" not in deleted
        assert "untagged-snap" in deleted

    def test_prune_nothing_old_enough(self, storage_dir):
        save_snapshot(Snapshot(
            name="recent-snap",
            metadata=SnapshotMetadata(name="recent-snap"),
        ))
        deleted = prune_snapshots(older_than="7d")
        assert deleted == []


class TestGetStorageUsage:
    def test_empty_storage(self, storage_dir):
        usage = get_storage_usage()
        assert usage["count"] == 0
        assert usage["total_size_bytes"] == 0

    def test_with_snapshots(self, storage_dir):
        save_snapshot(Snapshot(name="snap1", metadata=SnapshotMetadata(name="snap1")))
        usage = get_storage_usage()
        assert usage["count"] == 1
        assert usage["total_size_bytes"] > 0
        assert len(usage["snapshots"]) == 1


class TestHumanSize:
    def test_bytes(self):
        assert "B" in _human_size(100)

    def test_kilobytes(self):
        assert "KB" in _human_size(2048)

    def test_megabytes(self):
        assert "MB" in _human_size(2 * 1024 * 1024)

    def test_gigabytes(self):
        assert "GB" in _human_size(2 * 1024 * 1024 * 1024)
