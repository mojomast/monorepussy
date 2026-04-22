"""Tests for petrichor.profile module."""

from petrichor.db import SoilDB
from petrichor.hash import string_hash
from petrichor.profile import SoilProfiler
from petrichor.soil import SoilMemory


class TestSoilProfiler:
    def test_profile_empty(self, db):
        profiler = SoilProfiler(db)
        output = profiler.profile("/etc/test.conf")
        assert "No soil layers" in output

    def test_profile_with_layers(self, db):
        soil = SoilMemory(db)
        soil.snapshot_text("/etc/test.conf", "key=1024\n")
        soil.snapshot_text("/etc/test.conf", "key=2048\n", actor="root@prod")
        profiler = SoilProfiler(db)
        output = profiler.profile("/etc/test.conf")
        assert "Soil Profile" in output
        assert "Layer" in output

    def test_profile_with_correction(self, db):
        soil = SoilMemory(db)
        desired_hash = string_hash("key=1024\n")
        db.set_desired_state("/etc/test.conf", desired_hash, "key=1024\n")

        soil.snapshot_text("/etc/test.conf", "key=1024\n")
        soil.snapshot_text("/etc/test.conf", "key=2048\n", actor="root@prod")
        soil.snapshot_text("/etc/test.conf", "key=1024\n")
        soil.snapshot_text("/etc/test.conf", "key=2048\n", actor="root@prod")

        profiler = SoilProfiler(db)
        output = profiler.profile("/etc/test.conf")
        assert "CORRECTION" in output

    def test_profile_depth(self, db):
        soil = SoilMemory(db)
        for i in range(15):
            soil.snapshot_text("/etc/test.conf", f"key={i}\n")
        profiler = SoilProfiler(db)
        output = profiler.profile("/etc/test.conf", depth=5)
        assert "Layer" in output

    def test_brief(self, db):
        soil = SoilMemory(db)
        soil.snapshot_text("/etc/test.conf", "key=val\n")
        profiler = SoilProfiler(db)
        output = profiler.brief("/etc/test.conf")
        assert "/etc/test.conf" in output

    def test_brief_no_data(self, db):
        profiler = SoilProfiler(db)
        output = profiler.brief("/etc/nonexistent.conf")
        assert "no data" in output

    def test_profile_shows_drift_status(self, db):
        soil = SoilMemory(db)
        soil.snapshot_text("/etc/test.conf", "key=1024\n")
        soil.snapshot_text("/etc/test.conf", "key=2048\n", actor="root@prod")
        profiler = SoilProfiler(db)
        output = profiler.profile("/etc/test.conf")
        assert "DRIFTED" in output
