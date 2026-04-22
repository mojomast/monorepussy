"""SQLite storage for Portmore classification data."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_DEFAULT_DB = Path.home() / ".portmore" / "portmore.db"


def _get_db_path(db_path: str | None = None) -> Path:
    if db_path:
        return Path(db_path)
    return _DEFAULT_DB


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Get a connection to the Portmore database, creating schema if needed."""
    path = _get_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    _create_schema(conn)
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    """Create database tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hs_codes (
            subheading TEXT PRIMARY KEY,
            chapter TEXT NOT NULL,
            heading TEXT NOT NULL,
            description TEXT NOT NULL,
            family TEXT NOT NULL,
            spdx_ids TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS origin_determinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module TEXT NOT NULL,
            status TEXT NOT NULL,
            wholly_obtained INTEGER NOT NULL,
            ct_classification_changed INTEGER NOT NULL,
            value_added_ratio REAL NOT NULL,
            de_minimis_ratio REAL NOT NULL,
            accumulation_applied INTEGER NOT NULL,
            absorption_applied INTEGER NOT NULL,
            threshold REAL NOT NULL,
            deminimis_threshold REAL NOT NULL,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS compatibility_agreements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_license TEXT NOT NULL,
            to_license TEXT NOT NULL,
            status TEXT NOT NULL,
            condition TEXT DEFAULT '',
            quota_limit INTEGER DEFAULT 0,
            zone_from TEXT DEFAULT '',
            zone_to TEXT DEFAULT '',
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS valuations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_id TEXT NOT NULL,
            method INTEGER NOT NULL,
            value REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            article8_adjustments REAL DEFAULT 0.0,
            related_party_adjustment REAL DEFAULT 0.0,
            reasoning TEXT DEFAULT '',
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS contagion_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_id TEXT NOT NULL,
            dumping_margin REAL NOT NULL,
            copyleft_ratio REAL NOT NULL,
            within_duty_order INTEGER NOT NULL,
            injury_indicators TEXT DEFAULT '[]',
            causal_link_established INTEGER NOT NULL,
            lesser_duty_remedy TEXT NOT NULL,
            scope_ruling TEXT DEFAULT '',
            threshold REAL DEFAULT 0.60,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS quarantine_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dependency TEXT NOT NULL,
            zone TEXT NOT NULL,
            legal_status TEXT NOT NULL,
            obligations TEXT DEFAULT '[]',
            withdrawal_type TEXT,
            manipulation_warning INTEGER DEFAULT 0,
            constructive_warehouse INTEGER DEFAULT 0,
            in_bond_movement INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        );
    """)
    conn.commit()


def save_origin(conn: sqlite3.Connection, det: dict) -> int:
    """Save an origin determination record."""
    cursor = conn.execute("""
        INSERT INTO origin_determinations
        (module, status, wholly_obtained, ct_classification_changed,
         value_added_ratio, de_minimis_ratio, accumulation_applied,
         absorption_applied, threshold, deminimis_threshold, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        det["module"], det["status"], int(det["wholly_obtained"]),
        int(det["ct_classification_changed"]), det["value_added_ratio"],
        det["de_minimis_ratio"], int(det["accumulation_applied"]),
        int(det["absorption_applied"]), det["threshold"],
        det["deminimis_threshold"],
        det.get("timestamp", datetime.now(timezone.utc).isoformat()),
    ))
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def save_valuation(conn: sqlite3.Connection, val: dict) -> int:
    """Save a valuation record."""
    cursor = conn.execute("""
        INSERT INTO valuations
        (license_id, method, value, currency, article8_adjustments,
         related_party_adjustment, reasoning, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        val["license_id"], val["method"], val["value"], val.get("currency", "USD"),
        val.get("article8_adjustments", 0.0), val.get("related_party_adjustment", 0.0),
        val.get("reasoning", ""),
        val.get("timestamp", datetime.now(timezone.utc).isoformat()),
    ))
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def save_contagion(conn: sqlite3.Connection, assessment: dict) -> int:
    """Save a contagion assessment record."""
    cursor = conn.execute("""
        INSERT INTO contagion_assessments
        (license_id, dumping_margin, copyleft_ratio, within_duty_order,
         injury_indicators, causal_link_established, lesser_duty_remedy,
         scope_ruling, threshold, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        assessment["license_id"], assessment["dumping_margin"],
        assessment["copyleft_ratio"], int(assessment["within_duty_order"]),
        json.dumps(assessment.get("injury_indicators", [])),
        int(assessment["causal_link_established"]),
        assessment["lesser_duty_remedy"], assessment.get("scope_ruling", ""),
        assessment.get("threshold", 0.60),
        assessment.get("timestamp", datetime.now(timezone.utc).isoformat()),
    ))
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def save_quarantine_entry(conn: sqlite3.Connection, entry: dict) -> int:
    """Save a quarantine entry."""
    cursor = conn.execute("""
        INSERT INTO quarantine_registry
        (dependency, zone, legal_status, obligations, withdrawal_type,
         manipulation_warning, constructive_warehouse, in_bond_movement, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry["dependency"], entry["zone"], entry["legal_status"],
        json.dumps(entry.get("obligations", [])),
        entry.get("withdrawal_type"),
        int(entry.get("manipulation_warning", False)),
        int(entry.get("constructive_warehouse", False)),
        int(entry.get("in_bond_movement", False)),
        entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
    ))
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def query_origins(conn: sqlite3.Connection, module: str = "") -> list[dict]:
    """Query origin determinations."""
    if module:
        rows = conn.execute(
            "SELECT * FROM origin_determinations WHERE module = ? ORDER BY id DESC",
            (module,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM origin_determinations ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return [dict(r) for r in rows]


def query_valuations(conn: sqlite3.Connection, license_id: str = "") -> list[dict]:
    """Query valuation records."""
    if license_id:
        rows = conn.execute(
            "SELECT * FROM valuations WHERE license_id = ? ORDER BY id DESC",
            (license_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM valuations ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return [dict(r) for r in rows]


def query_contagions(conn: sqlite3.Connection, license_id: str = "") -> list[dict]:
    """Query contagion assessments."""
    if license_id:
        rows = conn.execute(
            "SELECT * FROM contagion_assessments WHERE license_id = ? ORDER BY id DESC",
            (license_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM contagion_assessments ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return [dict(r) for r in rows]


def query_quarantine(conn: sqlite3.Connection, dependency: str = "") -> list[dict]:
    """Query quarantine registry."""
    if dependency:
        rows = conn.execute(
            "SELECT * FROM quarantine_registry WHERE dependency = ? ORDER BY id DESC",
            (dependency,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM quarantine_registry ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return [dict(r) for r in rows]
