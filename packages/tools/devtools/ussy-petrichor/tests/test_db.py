"""Tests for petrichor.db module."""

import json
import os
from datetime import datetime, timezone

from petrichor.db import SoilDB


class TestSoilDBInit:
    def test_initialize_creates_db(self, tmp_dir):
        db = SoilDB(tmp_dir)
        path = db.initialize()
        assert os.path.exists(path)

    def test_initialize_idempotent(self, tmp_dir):
        db = SoilDB(tmp_dir)
        path1 = db.initialize()
        path2 = db.initialize()
        assert path1 == path2
        assert os.path.exists(path1)

    def test_db_dir_created(self, tmp_dir):
        db = SoilDB(tmp_dir)
        db.initialize()
        assert os.path.isdir(os.path.join(tmp_dir, ".petrichor"))


class TestSoilDBLayers:
    def test_add_layer(self, db):
        layer_id = db.add_layer(
            path="/etc/test.conf",
            content_hash="abc123",
            content_text="key=val",
        )
        assert layer_id > 0

    def test_get_layers(self, db):
        db.add_layer("/etc/test.conf", "hash1", "content1")
        db.add_layer("/etc/test.conf", "hash2", "content2")
        layers = db.get_layers("/etc/test.conf")
        assert len(layers) == 2

    def test_get_layers_depth(self, db):
        for i in range(5):
            db.add_layer("/etc/test.conf", f"hash{i}", f"content{i}")
        layers = db.get_layers("/etc/test.conf", depth=3)
        assert len(layers) == 3

    def test_get_layers_ordered_newest_first(self, db):
        import time
        db.add_layer("/etc/test.conf", "hash1", "content1")
        time.sleep(0.01)
        db.add_layer("/etc/test.conf", "hash2", "content2")
        layers = db.get_layers("/etc/test.conf")
        assert layers[0]["content_hash"] == "hash2"
        assert layers[1]["content_hash"] == "hash1"

    def test_get_latest_layer(self, db):
        db.add_layer("/etc/test.conf", "hash1", "content1")
        db.add_layer("/etc/test.conf", "hash2", "content2")
        latest = db.get_latest_layer("/etc/test.conf")
        assert latest["content_hash"] == "hash2"

    def test_get_latest_layer_none(self, db):
        result = db.get_latest_layer("/nonexistent/path")
        assert result is None

    def test_layer_has_timestamp(self, db):
        db.add_layer("/etc/test.conf", "hash1", "content1")
        layer = db.get_latest_layer("/etc/test.conf")
        assert layer["timestamp"]
        # Should be parseable as ISO format
        dt = datetime.fromisoformat(layer["timestamp"])
        assert dt.tzinfo is not None


class TestSoilDBDriftLayers:
    def test_get_drift_layers(self, db):
        db.add_layer("/etc/test.conf", "hash1", "content1", is_drift=False)
        db.add_layer("/etc/test.conf", "hash2", "content2", is_drift=True)
        drifts = db.get_drift_layers("/etc/test.conf")
        assert len(drifts) == 1
        assert drifts[0]["content_hash"] == "hash2"

    def test_drift_count(self, db):
        db.add_layer("/etc/test.conf", "hash1", "content1", is_drift=False)
        db.add_layer("/etc/test.conf", "hash2", "content2", is_drift=True)
        db.add_layer("/etc/test.conf", "hash3", "content3", is_drift=True)
        count = db.get_drift_count("/etc/test.conf")
        assert count == 2

    def test_get_all_drift_layers(self, db):
        db.add_layer("/etc/a.conf", "hash1", "content1", is_drift=True)
        db.add_layer("/etc/b.conf", "hash2", "content2", is_drift=True)
        db.add_layer("/etc/a.conf", "hash3", "content3", is_drift=False)
        drifts = db.get_all_drift_layers()
        assert len(drifts) == 2

    def test_path_drift_counts(self, db):
        db.add_layer("/etc/a.conf", "hash1", "content1", is_drift=True)
        db.add_layer("/etc/b.conf", "hash2", "content2", is_drift=True)
        db.add_layer("/etc/a.conf", "hash3", "content3", is_drift=True)
        counts = db.get_path_drift_counts()
        assert counts["/etc/a.conf"] == 2
        assert counts["/etc/b.conf"] == 1


class TestSoilDBDesiredState:
    def test_set_and_get_desired_state(self, db):
        db.set_desired_state("/etc/test.conf", "desired_hash_123", "desired_text", "git://...")
        result = db.get_desired_state("/etc/test.conf")
        assert result["desired_hash"] == "desired_hash_123"
        assert result["desired_text"] == "desired_text"
        assert result["source"] == "git://..."

    def test_desired_state_update(self, db):
        db.set_desired_state("/etc/test.conf", "hash1", "text1")
        db.set_desired_state("/etc/test.conf", "hash2", "text2")
        result = db.get_desired_state("/etc/test.conf")
        assert result["desired_hash"] == "hash2"

    def test_no_desired_state(self, db):
        result = db.get_desired_state("/nonexistent")
        assert result is None


class TestSoilDBTrackedPaths:
    def test_add_and_get_tracked(self, db):
        db.add_tracked_path("/etc/test.conf", "git://...")
        paths = db.get_tracked_paths()
        assert "/etc/test.conf" in paths

    def test_multiple_tracked(self, db):
        db.add_tracked_path("/etc/a.conf")
        db.add_tracked_path("/etc/b.conf")
        paths = db.get_tracked_paths()
        assert len(paths) == 2

    def test_remove_tracked(self, db):
        db.add_tracked_path("/etc/test.conf")
        db.remove_tracked_path("/etc/test.conf")
        paths = db.get_tracked_paths()
        assert "/etc/test.conf" not in paths

    def test_add_tracked_idempotent(self, db):
        db.add_tracked_path("/etc/test.conf")
        db.add_tracked_path("/etc/test.conf")
        paths = db.get_tracked_paths()
        assert len(paths) == 1
