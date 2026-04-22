"""Tests for the SQLite storage module."""
import pytest

from ussy_portmore.storage import (
    get_connection,
    query_contagions,
    query_origins,
    query_quarantine,
    query_valuations,
    save_contagion,
    save_origin,
    save_quarantine_entry,
    save_valuation,
)
from datetime import datetime, timezone


@pytest.fixture
def conn(tmp_path):
    """Create a temporary database connection."""
    db_path = tmp_path / "test.db"
    connection = get_connection(str(db_path))
    yield connection
    connection.close()


class TestDatabaseSchema:
    """Tests for database schema creation."""

    def test_tables_created(self, conn):
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t["name"] for t in tables]
        assert "hs_codes" in table_names
        assert "origin_determinations" in table_names
        assert "compatibility_agreements" in table_names
        assert "valuations" in table_names
        assert "contagion_assessments" in table_names
        assert "quarantine_registry" in table_names


class TestSaveOrigin:
    """Tests for saving origin determinations."""

    def test_save_and_query(self, conn):
        det = {
            "module": "core",
            "status": "wholly_obtained",
            "wholly_obtained": True,
            "ct_classification_changed": False,
            "value_added_ratio": 0.0,
            "de_minimis_ratio": 0.02,
            "accumulation_applied": False,
            "absorption_applied": False,
            "threshold": 0.40,
            "deminimis_threshold": 0.05,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        row_id = save_origin(conn, det)
        assert row_id > 0

        results = query_origins(conn, "core")
        assert len(results) == 1
        assert results[0]["module"] == "core"
        assert results[0]["status"] == "wholly_obtained"

    def test_query_all(self, conn):
        for mod in ["core", "utils", "vendor"]:
            det = {
                "module": mod, "status": "non_originating",
                "wholly_obtained": False, "ct_classification_changed": False,
                "value_added_ratio": 0.1, "de_minimis_ratio": 0.5,
                "accumulation_applied": False, "absorption_applied": False,
                "threshold": 0.40, "deminimis_threshold": 0.05,
            }
            save_origin(conn, det)

        results = query_origins(conn)
        assert len(results) == 3


class TestSaveValuation:
    """Tests for saving valuation records."""

    def test_save_and_query(self, conn):
        val = {
            "license_id": "MIT",
            "method": 1,
            "value": 300.0,
            "currency": "USD",
            "reasoning": "MIT obligations",
        }
        row_id = save_valuation(conn, val)
        assert row_id > 0

        results = query_valuations(conn, "MIT")
        assert len(results) == 1
        assert results[0]["value"] == 300.0


class TestSaveContagion:
    """Tests for saving contagion assessments."""

    def test_save_and_query(self, conn):
        assessment = {
            "license_id": "GPL-3.0",
            "dumping_margin": -70.0,
            "copyleft_ratio": 0.70,
            "within_duty_order": True,
            "injury_indicators": ["lost_licensing_options"],
            "causal_link_established": True,
            "lesser_duty_remedy": "Provide source for linked module",
            "scope_ruling": "YES - static linking",
            "threshold": 0.60,
        }
        row_id = save_contagion(conn, assessment)
        assert row_id > 0

        results = query_contagions(conn, "GPL-3.0")
        assert len(results) == 1
        assert results[0]["dumping_margin"] == -70.0


class TestSaveQuarantineEntry:
    """Tests for saving quarantine entries."""

    def test_save_and_query(self, conn):
        entry = {
            "dependency": "requests",
            "zone": "domestic",
            "legal_status": "duty-paid",
            "obligations": ["attribution"],
            "withdrawal_type": None,
            "manipulation_warning": False,
            "constructive_warehouse": False,
            "in_bond_movement": False,
        }
        row_id = save_quarantine_entry(conn, entry)
        assert row_id > 0

        results = query_quarantine(conn, "requests")
        assert len(results) == 1
        assert results[0]["zone"] == "domestic"

    def test_query_all(self, conn):
        for dep in ["requests", "numpy", "pytest"]:
            entry = {
                "dependency": dep, "zone": "bonded",
                "legal_status": "duty-deferred", "obligations": [],
            }
            save_quarantine_entry(conn, entry)

        results = query_quarantine(conn)
        assert len(results) == 3
