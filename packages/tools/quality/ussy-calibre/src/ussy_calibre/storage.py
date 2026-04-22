"""
SQLite-based test result storage for Marksman.

Provides persistent storage and retrieval of test execution history.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ussy_calibre.models import TestExecution, TestOutcomeMarksman as TestOutcome

SCHEMA = """
CREATE TABLE IF NOT EXISTS test_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name TEXT NOT NULL,
    suite TEXT NOT NULL DEFAULT '',
    outcome TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    is_false_positive INTEGER NOT NULL DEFAULT 0,
    is_false_negative INTEGER NOT NULL DEFAULT 0,
    run_id TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_test_name ON test_executions(test_name);
CREATE INDEX IF NOT EXISTS idx_suite ON test_executions(suite);
CREATE INDEX IF NOT EXISTS idx_timestamp ON test_executions(timestamp);
CREATE INDEX IF NOT EXISTS idx_run_id ON test_executions(run_id);
"""


class TestResultDB:
    """SQLite storage for test execution results."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def insert(self, execution: TestExecution) -> int:
        """Insert a test execution record."""
        cursor = self.conn.execute(
            """INSERT INTO test_executions
               (test_name, suite, outcome, timestamp, is_false_positive,
                is_false_negative, run_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                execution.test_name,
                execution.suite,
                execution.outcome.value,
                execution.timestamp.isoformat(),
                int(execution.is_false_positive),
                int(execution.is_false_negative),
                execution.run_id,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def insert_many(self, executions: list[TestExecution]) -> list[int]:
        """Insert multiple test execution records."""
        ids = []
        for ex in executions:
            ids.append(self.insert(ex))
        return ids

    def get_by_suite(self, suite: str) -> list[TestExecution]:
        """Get all executions for a given suite."""
        rows = self.conn.execute(
            "SELECT * FROM test_executions WHERE suite = ? ORDER BY timestamp",
            (suite,),
        ).fetchall()
        return [self._row_to_execution(r) for r in rows]

    def get_by_test(self, test_name: str) -> list[TestExecution]:
        """Get all executions for a given test."""
        rows = self.conn.execute(
            "SELECT * FROM test_executions WHERE test_name = ? ORDER BY timestamp",
            (test_name,),
        ).fetchall()
        return [self._row_to_execution(r) for r in rows]

    def get_by_run(self, run_id: str) -> list[TestExecution]:
        """Get all executions for a given run."""
        rows = self.conn.execute(
            "SELECT * FROM test_executions WHERE run_id = ? ORDER BY timestamp",
            (run_id,),
        ).fetchall()
        return [self._row_to_execution(r) for r in rows]

    def get_all(self) -> list[TestExecution]:
        """Get all test executions."""
        rows = self.conn.execute(
            "SELECT * FROM test_executions ORDER BY timestamp"
        ).fetchall()
        return [self._row_to_execution(r) for r in rows]

    def get_suites(self) -> list[str]:
        """Get all distinct suite names."""
        rows = self.conn.execute(
            "SELECT DISTINCT suite FROM test_executions ORDER BY suite"
        ).fetchall()
        return [r["suite"] for r in rows]

    def get_test_names(self, suite: str | None = None) -> list[str]:
        """Get all distinct test names, optionally filtered by suite."""
        if suite:
            rows = self.conn.execute(
                "SELECT DISTINCT test_name FROM test_executions WHERE suite = ? ORDER BY test_name",
                (suite,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT DISTINCT test_name FROM test_executions ORDER BY test_name"
            ).fetchall()
        return [r["test_name"] for r in rows]

    def get_failure_times(self, suite: str) -> list[datetime]:
        """Get timestamps of all failures in a suite, sorted."""
        rows = self.conn.execute(
            """SELECT timestamp FROM test_executions
               WHERE suite = ? AND outcome IN ('fail', 'error')
               ORDER BY timestamp""",
            (suite,),
        ).fetchall()
        return [datetime.fromisoformat(r["timestamp"]) for r in rows]

    def get_fp_fn_rates(self, test_name: str) -> tuple[float, float]:
        """Compute false positive and false negative rates for a test."""
        rows = self.conn.execute(
            "SELECT * FROM test_executions WHERE test_name = ?",
            (test_name,),
        ).fetchall()
        if not rows:
            return 0.0, 0.0
        n = len(rows)
        fp_count = sum(r["is_false_positive"] for r in rows)
        fn_count = sum(r["is_false_negative"] for r in rows)
        return fp_count / n, fn_count / n

    def delete_all(self) -> None:
        """Delete all records."""
        self.conn.execute("DELETE FROM test_executions")
        self.conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    def _row_to_execution(self, row: sqlite3.Row) -> TestExecution:
        """Convert a database row to a TestExecution."""
        return TestExecution(
            test_name=row["test_name"],
            outcome=TestOutcome(row["outcome"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            suite=row["suite"],
            is_false_positive=bool(row["is_false_positive"]),
            is_false_negative=bool(row["is_false_negative"]),
            run_id=row["run_id"],
        )

    def __enter__(self) -> TestResultDB:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def load_fixture(path: str | Path) -> list[TestExecution]:
    """Load test executions from a JSON fixture file."""
    with open(path) as f:
        data = json.load(f)
    executions = []
    for item in data:
        ts = item.get("timestamp", datetime.now(timezone.utc).isoformat())
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        executions.append(TestExecution(
            test_name=item["test_name"],
            outcome=TestOutcome(item["outcome"]),
            timestamp=ts,
            suite=item.get("suite", ""),
            is_false_positive=item.get("is_false_positive", False),
            is_false_negative=item.get("is_false_negative", False),
            run_id=item.get("run_id", ""),
        ))
    return executions
