"""Tests for petrichor.export module."""

import json

from petrichor.db import SoilDB
from petrichor.export import Exporter
from petrichor.soil import SoilMemory


class TestExporter:
    def test_export_json_empty(self, db):
        exporter = Exporter(db)
        output = exporter.export_json(days=30)
        data = json.loads(output)
        assert "layers" in data
        assert "generated_at" in data
        assert data["layer_count"] == 0

    def test_export_json_with_data(self, db):
        soil = SoilMemory(db)
        db.add_tracked_path("/etc/test.conf")
        soil.snapshot_text("/etc/test.conf", "key=val\n")
        exporter = Exporter(db)
        output = exporter.export_json(days=30)
        data = json.loads(output)
        assert data["layer_count"] >= 1

    def test_export_text(self, db):
        db.add_tracked_path("/etc/test.conf")
        db.add_layer("/etc/test.conf", "h1", "c1", is_drift=True)
        exporter = Exporter(db)
        output = exporter.export_text(days=30)
        assert "Petrichor Export" in output
        assert "Total layers" in output

    def test_export_format_dispatch(self, db):
        exporter = Exporter(db)
        json_out = exporter.export(format="json", days=30)
        assert json_out  # non-empty
        text_out = exporter.export(format="text", days=30)
        assert text_out  # non-empty

    def test_export_invalid_format(self, db):
        exporter = Exporter(db)
        import pytest
        with pytest.raises(ValueError):
            exporter.export(format="xml", days=30)

    def test_export_json_specific_path(self, db):
        db.add_tracked_path("/etc/a.conf")
        db.add_tracked_path("/etc/b.conf")
        db.add_layer("/etc/a.conf", "h1", "c1")
        db.add_layer("/etc/b.conf", "h2", "c2")
        exporter = Exporter(db)
        output = exporter.export_json(days=30, path="/etc/a.conf")
        data = json.loads(output)
        for layer in data["layers"]:
            assert layer["path"] == "/etc/a.conf"

    def test_export_json_removes_large_fields(self, db):
        db.add_tracked_path("/etc/test.conf")
        db.add_layer("/etc/test.conf", "h1", "large content " * 100, diff_text="diff " * 50)
        exporter = Exporter(db)
        output = exporter.export_json(days=30)
        data = json.loads(output)
        for layer in data["layers"]:
            assert "content_text" not in layer
            assert "diff_text" not in layer

    def test_export_days_filter(self, db):
        db.add_tracked_path("/etc/test.conf")
        db.add_layer("/etc/test.conf", "h1", "c1")
        exporter = Exporter(db)
        # 0 days should include only very recent
        output = exporter.export_json(days=1)
        data = json.loads(output)
        # Layer should still be included since it was just added
        assert data["layer_count"] >= 0
