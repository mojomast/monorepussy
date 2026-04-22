"""SQLite storage for Calibre test results and metadata."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from calibre.models import (
    DriftObservation,
    RRObservation,
    TestResult,
    TestRun,
    TraceabilityLink,
)


_DEFAULT_DB = Path("calibre.db")


class CalibreDB:
    """SQLite database interface for Calibre."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._init_schema()
        return self._conn

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS test_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT NOT NULL,
                module TEXT NOT NULL,
                suite TEXT NOT NULL,
                build_id TEXT NOT NULL,
                environment TEXT NOT NULL,
                result TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                duration REAL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS rr_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                build_id TEXT NOT NULL,
                environment TEXT NOT NULL,
                test_name TEXT NOT NULL,
                replicate INTEGER NOT NULL,
                value REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS drift_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                observed_value REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS traceability_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT NOT NULL,
                level TEXT NOT NULL,
                reference TEXT NOT NULL,
                uncertainty REAL DEFAULT 0.0,
                last_verified TEXT,
                review_interval_days INTEGER DEFAULT 365
            );

            CREATE INDEX IF NOT EXISTS idx_test_runs_suite ON test_runs(suite);
            CREATE INDEX IF NOT EXISTS idx_test_runs_name ON test_runs(test_name);
            CREATE INDEX IF NOT EXISTS idx_test_runs_build ON test_runs(build_id);
            CREATE INDEX IF NOT EXISTS idx_test_runs_env ON test_runs(environment);
        """)
        self.conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ---- TestRun CRUD ----

    def insert_test_run(self, run: TestRun) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO test_runs
               (test_name, module, suite, build_id, environment, result, timestamp, duration)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run.test_name,
                run.module,
                run.suite,
                run.build_id,
                run.environment,
                run.result.value,
                run.timestamp.isoformat(),
                run.duration,
            ),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def insert_test_runs(self, runs: List[TestRun]) -> None:
        for run in runs:
            self.insert_test_run(run)

    def get_test_runs(
        self,
        suite: Optional[str] = None,
        test_name: Optional[str] = None,
        module: Optional[str] = None,
        build_id: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> List[TestRun]:
        query = "SELECT * FROM test_runs WHERE 1=1"
        params: list = []
        if suite:
            query += " AND suite = ?"
            params.append(suite)
        if test_name:
            query += " AND test_name = ?"
            params.append(test_name)
        if module:
            query += " AND module = ?"
            params.append(module)
        if build_id:
            query += " AND build_id = ?"
            params.append(build_id)
        if environment:
            query += " AND environment = ?"
            params.append(environment)
        query += " ORDER BY timestamp"

        rows = self.conn.execute(query, params).fetchall()
        results: List[TestRun] = []
        for row in rows:
            results.append(
                TestRun(
                    test_name=row["test_name"],
                    module=row["module"],
                    suite=row["suite"],
                    build_id=row["build_id"],
                    environment=row["environment"],
                    result=TestResult(row["result"]),
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    duration=row["duration"],
                )
            )
        return results

    def get_unique_builds(self, suite: Optional[str] = None) -> List[str]:
        query = "SELECT DISTINCT build_id FROM test_runs"
        params: list = []
        if suite:
            query += " WHERE suite = ?"
            params.append(suite)
        query += " ORDER BY build_id"
        rows = self.conn.execute(query, params).fetchall()
        return [row["build_id"] for row in rows]

    def get_unique_environments(self, suite: Optional[str] = None) -> List[str]:
        query = "SELECT DISTINCT environment FROM test_runs"
        params: list = []
        if suite:
            query += " WHERE suite = ?"
            params.append(suite)
        query += " ORDER BY environment"
        rows = self.conn.execute(query, params).fetchall()
        return [row["environment"] for row in rows]

    # ---- RR Observations ----

    def insert_rr_observation(self, obs: RRObservation) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO rr_observations
               (build_id, environment, test_name, replicate, value)
               VALUES (?, ?, ?, ?, ?)""",
            (obs.build_id, obs.environment, obs.test_name, obs.replicate, obs.value),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def insert_rr_observations(self, obs_list: List[RRObservation]) -> None:
        for obs in obs_list:
            self.insert_rr_observation(obs)

    def get_rr_observations(
        self,
        test_name: Optional[str] = None,
    ) -> List[RRObservation]:
        query = "SELECT * FROM rr_observations WHERE 1=1"
        params: list = []
        if test_name:
            query += " AND test_name = ?"
            params.append(test_name)
        rows = self.conn.execute(query, params).fetchall()
        results: List[RRObservation] = []
        for row in rows:
            results.append(
                RRObservation(
                    build_id=row["build_id"],
                    environment=row["environment"],
                    test_name=row["test_name"],
                    replicate=row["replicate"],
                    value=row["value"],
                )
            )
        return results

    # ---- Drift Observations ----

    def insert_drift_observation(self, obs: DriftObservation) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO drift_observations
               (test_name, timestamp, observed_value)
               VALUES (?, ?, ?)""",
            (obs.test_name, obs.timestamp.isoformat(), obs.observed_value),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def insert_drift_observations(self, obs_list: List[DriftObservation]) -> None:
        for obs in obs_list:
            self.insert_drift_observation(obs)

    def get_drift_observations(
        self, test_name: Optional[str] = None
    ) -> List[DriftObservation]:
        query = "SELECT * FROM drift_observations WHERE 1=1"
        params: list = []
        if test_name:
            query += " AND test_name = ?"
            params.append(test_name)
        query += " ORDER BY timestamp"
        rows = self.conn.execute(query, params).fetchall()
        results: List[DriftObservation] = []
        for row in rows:
            results.append(
                DriftObservation(
                    test_name=row["test_name"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    observed_value=row["observed_value"],
                )
            )
        return results

    # ---- Traceability Links ----

    def insert_traceability_link(self, link: TraceabilityLink) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO traceability_links
               (test_name, level, reference, uncertainty, last_verified, review_interval_days)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                link.test_name,
                link.level,
                link.reference,
                link.uncertainty,
                link.last_verified.isoformat() if link.last_verified else None,
                link.review_interval_days,
            ),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def insert_traceability_links(self, links: List[TraceabilityLink]) -> None:
        for link in links:
            self.insert_traceability_link(link)

    def get_traceability_links(
        self, test_name: Optional[str] = None
    ) -> List[TraceabilityLink]:
        query = "SELECT * FROM traceability_links WHERE 1=1"
        params: list = []
        if test_name:
            query += " AND test_name = ?"
            params.append(test_name)
        rows = self.conn.execute(query, params).fetchall()
        results: List[TraceabilityLink] = []
        for row in rows:
            results.append(
                TraceabilityLink(
                    test_name=row["test_name"],
                    level=row["level"],
                    reference=row["reference"],
                    uncertainty=row["uncertainty"],
                    last_verified=(
                        datetime.fromisoformat(row["last_verified"])
                        if row["last_verified"]
                        else None
                    ),
                    review_interval_days=row["review_interval_days"],
                )
            )
        return results

    def import_json_results(self, path: str) -> int:
        """Import test results from a JSON file (pytest/jest style)."""
        with open(path, "r") as f:
            data = json.load(f)

        count = 0
        # Support pytest-json-report format
        tests = data.get("tests", data.get("testResults", []))
        for entry in tests:
            test_name = entry.get("nodeid", entry.get("name", "unknown"))
            outcome = entry.get("outcome", entry.get("status", "unknown"))
            duration = entry.get("duration", entry.get("duration_ms", 0) / 1000.0)

            if outcome in ("passed", "pass"):
                result = TestResult.PASS
            elif outcome in ("failed", "fail"):
                result = TestResult.FAIL
            elif outcome in ("error",):
                result = TestResult.ERROR
            else:
                result = TestResult.SKIP

            # Parse module from test name
            parts = test_name.split("::")
            module = parts[0] if parts else "unknown"
            suite = parts[0].replace(".py", "").replace("/", ".") if parts else "unknown"

            run = TestRun(
                test_name=test_name,
                module=module,
                suite=suite,
                build_id=data.get("build_id", "unknown"),
                environment=data.get("environment", "unknown"),
                result=result,
                timestamp=datetime.now(timezone.utc),
                duration=duration,
            )
            self.insert_test_run(run)
            count += 1

        return count
