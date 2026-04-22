"""Tests for petrichor.groundwater module."""

from petrichor.db import SoilDB
from petrichor.groundwater import GroundwaterDetector, GroundwaterLayer
from petrichor.hash import string_hash


class TestGroundwaterLayer:
    def test_consistent_layer(self):
        h = string_hash("key=val\n")
        layer = GroundwaterLayer(
            path="/etc/test.conf",
            declared_hash=h,
            effective_hash=h,
            intended_hash=h,
        )
        assert layer.is_consistent is True
        assert layer.latent_drift is False
        assert layer.config_drift is False
        assert layer.deep_drift is False

    def test_latent_drift(self):
        layer = GroundwaterLayer(
            path="/etc/test.conf",
            declared_hash="hash1",
            effective_hash="hash2",
            intended_hash="hash1",
        )
        assert layer.latent_drift is True
        assert layer.config_drift is False
        assert layer.is_consistent is False

    def test_config_drift(self):
        layer = GroundwaterLayer(
            path="/etc/test.conf",
            declared_hash="hash1",
            effective_hash="hash1",
            intended_hash="hash2",
        )
        assert layer.config_drift is True
        assert layer.latent_drift is False

    def test_deep_drift(self):
        layer = GroundwaterLayer(
            path="/etc/test.conf",
            declared_hash="hash1",
            effective_hash="hash2",
            intended_hash="hash3",
        )
        assert layer.deep_drift is True
        assert layer.latent_drift is True

    def test_empty_hashes_consistent(self):
        layer = GroundwaterLayer(path="/etc/test.conf")
        assert layer.is_consistent is True

    def test_partial_hashes(self):
        layer = GroundwaterLayer(
            path="/etc/test.conf",
            declared_hash="hash1",
        )
        assert layer.is_consistent is True  # Only one non-empty hash


class TestGroundwaterDetector:
    def test_analyze_with_no_data(self, db):
        detector = GroundwaterDetector(db)
        result = detector.analyze("/etc/test.conf")
        assert result.path == "/etc/test.conf"
        assert result.is_consistent is True

    def test_analyze_with_layer(self, db):
        db.add_layer("/etc/test.conf", "hash1", "key=val\n")
        detector = GroundwaterDetector(db)
        result = detector.analyze("/etc/test.conf")
        assert result.declared_hash == "hash1"

    def test_analyze_with_desired_state(self, db):
        db.add_layer("/etc/test.conf", "hash1", "key=val\n")
        db.set_desired_state("/etc/test.conf", "hash1", "key=val\n")
        detector = GroundwaterDetector(db)
        result = detector.analyze("/etc/test.conf")
        assert result.is_consistent is True

    def test_analyze_drift_detected(self, db):
        db.add_layer("/etc/test.conf", "hash1", "key=wrong\n")
        db.set_desired_state("/etc/test.conf", "hash2", "key=right\n")
        detector = GroundwaterDetector(db)
        result = detector.analyze("/etc/test.conf")
        assert result.config_drift is True

    def test_analyze_with_effective(self, db):
        db.add_layer("/etc/test.conf", "hash1", "key=val\n")
        detector = GroundwaterDetector(db)
        result = detector.analyze_with_effective("/etc/test.conf", "key=wrong\n")
        assert result.latent_drift is True

    def test_analyze_all(self, db):
        db.add_tracked_path("/etc/a.conf")
        db.add_tracked_path("/etc/b.conf")
        detector = GroundwaterDetector(db)
        results = detector.analyze_all()
        assert len(results) == 2

    def test_format_groundwater(self, db):
        db.add_layer("/etc/test.conf", "hash1", "key=val\n")
        db.set_desired_state("/etc/test.conf", "hash1", "key=val\n")
        db.add_tracked_path("/etc/test.conf")
        detector = GroundwaterDetector(db)
        output = detector.format_groundwater("/etc/test.conf")
        assert "Groundwater Detection" in output
