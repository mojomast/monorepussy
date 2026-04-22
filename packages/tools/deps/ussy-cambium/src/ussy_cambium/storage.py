"""Storage layer — JSON + SQLite persistence for GCI snapshots and drift time series."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

from ussy_cambium.models import GCISnapshot


SCHEMA = """
CREATE TABLE IF NOT EXISTS gci_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consumer TEXT NOT NULL,
    provider TEXT NOT NULL,
    gci REAL NOT NULL,
    compatibility REAL,
    alignment REAL,
    adapter_quality REAL,
    drift_fraction REAL,
    bond_fraction REAL,
    system_vigor REAL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drift_time_series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dep_name TEXT NOT NULL,
    month REAL NOT NULL,
    drift_debt REAL,
    budget_consumed REAL,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gci_pair ON gci_snapshots(consumer, provider);
CREATE INDEX IF NOT EXISTS idx_drift_dep ON drift_time_series(dep_name);
"""


class Storage:
    """SQLite + JSON storage for Cambium analysis results."""

    def __init__(self, db_path: str = "") -> None:
        if not db_path:
            db_path = os.path.join(os.getcwd(), "cambium.db")
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(SCHEMA)
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def save_gci_snapshot(
        self,
        consumer: str,
        provider: str,
        snapshot: GCISnapshot,
    ) -> int:
        """Save a GCI snapshot to the database."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO gci_snapshots
               (consumer, provider, gci, compatibility, alignment,
                adapter_quality, drift_fraction, bond_fraction, system_vigor, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                consumer,
                provider,
                snapshot.gci,
                snapshot.compatibility,
                snapshot.alignment,
                snapshot.adapter_quality,
                snapshot.drift_fraction,
                snapshot.bond_fraction,
                snapshot.system_vigor,
                snapshot.timestamp,
            ),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore

    def get_gci_history(
        self,
        consumer: str = "",
        provider: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve GCI snapshot history, optionally filtered by dependency pair."""
        conn = self._get_conn()

        if consumer and provider:
            rows = conn.execute(
                """SELECT * FROM gci_snapshots
                   WHERE consumer = ? AND provider = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (consumer, provider, limit),
            ).fetchall()
        elif consumer:
            rows = conn.execute(
                """SELECT * FROM gci_snapshots
                   WHERE consumer = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (consumer, limit),
            ).fetchall()
        elif provider:
            rows = conn.execute(
                """SELECT * FROM gci_snapshots
                   WHERE provider = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (provider, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM gci_snapshots ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def save_drift_series(
        self,
        dep_name: str,
        series: list[dict],
    ) -> int:
        """Save a drift time series to the database."""
        conn = self._get_conn()
        ts = datetime.now(timezone.utc).isoformat()
        count = 0
        for point in series:
            conn.execute(
                """INSERT INTO drift_time_series
                   (dep_name, month, drift_debt, budget_consumed, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    dep_name,
                    point.get("month", 0),
                    point.get("drift_debt", 0),
                    point.get("budget_consumed", 0),
                    ts,
                ),
            )
            count += 1
        conn.commit()
        return count

    def get_drift_history(
        self,
        dep_name: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve drift time series history for a dependency."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM drift_time_series
               WHERE dep_name = ?
               ORDER BY timestamp DESC, month ASC LIMIT ?""",
            (dep_name, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def export_json(self, output_path: str) -> None:
        """Export all data to a JSON file."""
        gci_data = self.get_gci_history(limit=10000)
        conn = self._get_conn()
        drift_rows = conn.execute(
            "SELECT * FROM drift_time_series ORDER BY dep_name, month"
        ).fetchall()
        drift_data = [dict(row) for row in drift_rows]

        export = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "gci_snapshots": gci_data,
            "drift_time_series": drift_data,
        }

        with open(output_path, "w") as f:
            json.dump(export, f, indent=2, default=str)

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
