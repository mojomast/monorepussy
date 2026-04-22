"""Tests for Cambium storage module."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from cambium.models import GCISnapshot
from cambium.storage import Storage


class TestStorageInit:
    """Tests for Storage initialization."""

    def test_create_with_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = Storage(db_path)
            assert os.path.exists(db_path)
            storage.close()

    def test_schema_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = Storage(db_path)
            conn = storage._get_conn()
            # Check tables exist
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]
            assert "gci_snapshots" in table_names
            assert "drift_time_series" in table_names
            storage.close()


class TestGCISnapshotStorage:
    """Tests for saving and retrieving GCI snapshots."""

    def test_save_and_retrieve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = Storage(db_path)

            snap = GCISnapshot(
                compatibility=0.8, alignment=0.9, adapter_quality=0.7,
                drift_fraction=0.1, bond_fraction=0.85, system_vigor=0.9,
            )
            row_id = storage.save_gci_snapshot("consumer_a", "provider_b", snap)
            assert row_id > 0

            history = storage.get_gci_history("consumer_a", "provider_b")
            assert len(history) == 1
            assert history[0]["consumer"] == "consumer_a"
            assert history[0]["provider"] == "provider_b"
            assert abs(history[0]["gci"] - snap.gci) < 0.01

            storage.close()

    def test_multiple_snapshots(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = Storage(db_path)

            for i in range(5):
                snap = GCISnapshot(
                    compatibility=0.8 - i * 0.05,
                    alignment=0.9,
                    adapter_quality=0.7,
                    drift_fraction=0.1 + i * 0.05,
                    bond_fraction=0.85,
                    system_vigor=0.9,
                )
                storage.save_gci_snapshot("a", "b", snap)

            history = storage.get_gci_history("a", "b")
            assert len(history) == 5

            storage.close()

    def test_filter_by_consumer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = Storage(db_path)

            snap = GCISnapshot()
            storage.save_gci_snapshot("consumer_x", "provider_y", snap)
            storage.save_gci_snapshot("consumer_z", "provider_y", snap)

            history = storage.get_gci_history(consumer="consumer_x")
            assert len(history) == 1
            assert history[0]["consumer"] == "consumer_x"

            storage.close()

    def test_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = Storage(db_path)

            snap = GCISnapshot()
            for _ in range(10):
                storage.save_gci_snapshot("a", "b", snap)

            history = storage.get_gci_history("a", "b", limit=3)
            assert len(history) == 3

            storage.close()


class TestDriftSeriesStorage:
    """Tests for saving and retrieving drift time series."""

    def test_save_and_retrieve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = Storage(db_path)

            series = [
                {"month": 0, "drift_debt": 0.0, "budget_consumed": 0.0},
                {"month": 1, "drift_debt": 0.05, "budget_consumed": 0.05},
                {"month": 2, "drift_debt": 0.1, "budget_consumed": 0.1},
            ]
            count = storage.save_drift_series("dep_a", series)
            assert count == 3

            history = storage.get_drift_history("dep_a")
            assert len(history) == 3

            storage.close()


class TestExportJson:
    """Tests for JSON export."""

    def test_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = Storage(db_path)

            snap = GCISnapshot(compatibility=0.8, alignment=0.9)
            storage.save_gci_snapshot("a", "b", snap)

            json_path = os.path.join(tmpdir, "export.json")
            storage.export_json(json_path)

            with open(json_path) as f:
                data = json.load(f)

            assert "gci_snapshots" in data
            assert "drift_time_series" in data
            assert "exported_at" in data
            assert len(data["gci_snapshots"]) == 1

            storage.close()
