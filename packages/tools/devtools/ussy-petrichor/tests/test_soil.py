"""Tests for petrichor.soil module."""

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from petrichor.db import SoilDB
from petrichor.hash import string_hash
from petrichor.soil import SoilMemory, SoilLayer


class TestSoilLayer:
    def test_create_layer(self):
        layer = SoilLayer(
            path="/etc/test.conf",
            content_hash="abc123",
            content_text="key=val",
        )
        assert layer.path == "/etc/test.conf"
        assert layer.content_hash == "abc123"
        assert layer.is_drift is False

    def test_layer_has_timestamp(self):
        layer = SoilLayer(
            path="/etc/test.conf",
            content_hash="abc123",
            content_text="key=val",
        )
        assert layer.timestamp is not None
        assert layer.timestamp.tzinfo is not None


class TestSoilMemorySnapshot:
    def test_snapshot_creates_layer(self, db, sample_file):
        soil = SoilMemory(db)
        layer = soil.snapshot(sample_file)
        assert layer is not None
        assert layer.content_hash
        assert layer.content_text

    def test_snapshot_first_time_not_drift(self, db, sample_file):
        soil = SoilMemory(db)
        layer = soil.snapshot(sample_file)
        assert layer.is_drift is False

    def test_snapshot_detects_drift(self, db, sample_file):
        soil = SoilMemory(db)
        soil.snapshot(sample_file)

        # Modify the file
        Path(sample_file).write_text("worker_connections=2048\n")

        layer = soil.snapshot(sample_file)
        assert layer.is_drift is True
        assert layer.diff_text != ""

    def test_snapshot_no_change_no_drift(self, db, sample_file):
        soil = SoilMemory(db)
        soil.snapshot(sample_file)
        layer = soil.snapshot(sample_file)
        assert layer.is_drift is False
        assert layer.diff_text == ""

    def test_snapshot_file_not_found(self, db):
        soil = SoilMemory(db)
        import pytest
        with pytest.raises(FileNotFoundError):
            soil.snapshot("/nonexistent/file.conf")

    def test_snapshot_stores_in_db(self, db, sample_file):
        soil = SoilMemory(db)
        soil.snapshot(sample_file)
        layers = db.get_layers(os.path.abspath(sample_file))
        assert len(layers) == 1


class TestSoilMemorySnapshotText:
    def test_snapshot_text(self, db):
        soil = SoilMemory(db)
        layer = soil.snapshot_text("/etc/test.conf", "key=val\n")
        assert layer.content_hash == string_hash("key=val\n")
        assert layer.is_drift is False

    def test_snapshot_text_detects_drift(self, db):
        soil = SoilMemory(db)
        soil.snapshot_text("/etc/test.conf", "key=old\n")
        layer = soil.snapshot_text("/etc/test.conf", "key=new\n")
        assert layer.is_drift is True
        assert layer.diff_text != ""

    def test_snapshot_text_with_desired(self, db):
        soil = SoilMemory(db)
        desired_hash = string_hash("key=val\n")
        db.set_desired_state("/etc/test.conf", desired_hash, "key=val\n")
        layer = soil.snapshot_text("/etc/test.conf", "key=val\n", desired_hash=desired_hash)
        assert layer.is_drift is False

    def test_snapshot_text_drift_from_desired(self, db):
        soil = SoilMemory(db)
        desired_hash = string_hash("key=val\n")
        db.set_desired_state("/etc/test.conf", desired_hash, "key=val\n")
        layer = soil.snapshot_text("/etc/test.conf", "key=wrong\n", desired_hash=desired_hash)
        assert layer.is_drift is True


class TestSoilMemoryDriftDetection:
    def test_detect_drift_none_when_no_data(self, db):
        soil = SoilMemory(db)
        result = soil.detect_drift("/etc/test.conf")
        assert result is None

    def test_detect_drift_matches_desired(self, db):
        soil = SoilMemory(db)
        content = "key=val\n"
        desired_hash = string_hash(content)
        db.set_desired_state("/etc/test.conf", desired_hash, content)
        soil.snapshot_text("/etc/test.conf", content)
        result = soil.detect_drift("/etc/test.conf")
        assert result is None  # No drift

    def test_detect_drift_found(self, db):
        soil = SoilMemory(db)
        desired_hash = string_hash("key=val\n")
        db.set_desired_state("/etc/test.conf", desired_hash, "key=val\n")
        soil.snapshot_text("/etc/test.conf", "key=wrong\n")
        result = soil.detect_drift("/etc/test.conf")
        assert result is not None
        assert result["is_drift"] is True
        assert "changed_keys" in result


class TestSoilMemoryCorrectionDetection:
    def test_no_correction_with_few_layers(self, db):
        soil = SoilMemory(db)
        soil.snapshot_text("/etc/test.conf", "key=val\n")
        result = soil.detect_correction("/etc/test.conf")
        assert result is None

    def test_correction_detected(self, db):
        soil = SoilMemory(db)
        desired_hash = string_hash("key=1024\n")
        db.set_desired_state("/etc/test.conf", desired_hash, "key=1024\n")

        # Baseline
        soil.snapshot_text("/etc/test.conf", "key=1024\n")
        # Drift to 2048
        soil.snapshot_text("/etc/test.conf", "key=2048\n", actor="root@prod")
        # Correction back
        soil.snapshot_text("/etc/test.conf", "key=1024\n")
        # Drift to 2048 again
        soil.snapshot_text("/etc/test.conf", "key=2048\n", actor="root@prod")

        result = soil.detect_correction("/etc/test.conf")
        assert result is not None
        assert result["diagnosis"] == "DRIFT_IS_CORRECTION"
        assert result["recurrence_count"] >= 2

    def test_no_correction_for_unique_drifts(self, db):
        soil = SoilMemory(db)
        soil.snapshot_text("/etc/test.conf", "key=1\n")
        soil.snapshot_text("/etc/test.conf", "key=2\n")
        soil.snapshot_text("/etc/test.conf", "key=3\n")
        result = soil.detect_correction("/etc/test.conf")
        assert result is None

    def test_correction_suggestion(self, db):
        soil = SoilMemory(db)
        desired_hash = string_hash("key=1024\n")
        db.set_desired_state("/etc/test.conf", desired_hash, "key=1024\n")

        soil.snapshot_text("/etc/test.conf", "key=1024\n")
        soil.snapshot_text("/etc/test.conf", "key=2048\n")
        soil.snapshot_text("/etc/test.conf", "key=1024\n")
        soil.snapshot_text("/etc/test.conf", "key=2048\n")

        result = soil.detect_correction("/etc/test.conf")
        assert result is not None
        assert "suggestion" in result
