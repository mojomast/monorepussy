"""Community Database for anonymous outcome sharing.

Uses SQLite to store and query community architecture decision outcomes.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


# Seed data: anonymized architecture decision outcomes from various organizations
COMMUNITY_SEED_DATA = [
    {
        "decision_type": "RDBMS over NoSQL for microservices",
        "outcome": "Schema rigidity bottleneck",
        "org_count": 18,
        "total_orgs": 50,
        "timeframe_months": 18,
    },
    {
        "decision_type": "RDBMS over NoSQL for microservices",
        "outcome": "No issues",
        "org_count": 22,
        "total_orgs": 50,
        "timeframe_months": 18,
    },
    {
        "decision_type": "Microservices migration",
        "outcome": "Distributed monolith",
        "org_count": 35,
        "total_orgs": 60,
        "timeframe_months": 24,
    },
    {
        "decision_type": "Microservices migration",
        "outcome": "No issues",
        "org_count": 15,
        "total_orgs": 60,
        "timeframe_months": 24,
    },
    {
        "decision_type": "Event sourcing adoption",
        "outcome": "Eventual consistency issues",
        "org_count": 12,
        "total_orgs": 30,
        "timeframe_months": 12,
    },
    {
        "decision_type": "Event sourcing adoption",
        "outcome": "No issues",
        "org_count": 18,
        "total_orgs": 30,
        "timeframe_months": 12,
    },
    {
        "decision_type": "Single AZ deployment",
        "outcome": "Availability outage",
        "org_count": 27,
        "total_orgs": 30,
        "timeframe_months": 6,
    },
    {
        "decision_type": "SOAP API",
        "outcome": "Integration blockers",
        "org_count": 19,
        "total_orgs": 20,
        "timeframe_months": 12,
    },
    {
        "decision_type": "Caching layer addition",
        "outcome": "Cache invalidation bugs",
        "org_count": 14,
        "total_orgs": 40,
        "timeframe_months": 12,
    },
    {
        "decision_type": "Caching layer addition",
        "outcome": "No issues",
        "org_count": 26,
        "total_orgs": 40,
        "timeframe_months": 12,
    },
    {
        "decision_type": "Redis for session storage",
        "outcome": "Memory pressure under load",
        "org_count": 16,
        "total_orgs": 45,
        "timeframe_months": 12,
    },
    {
        "decision_type": "Redis for session storage",
        "outcome": "No issues",
        "org_count": 29,
        "total_orgs": 45,
        "timeframe_months": 12,
    },
    {
        "decision_type": "Read replicas for scaling",
        "outcome": "Replication lag issues",
        "org_count": 11,
        "total_orgs": 35,
        "timeframe_months": 12,
    },
    {
        "decision_type": "Read replicas for scaling",
        "outcome": "No issues",
        "org_count": 24,
        "total_orgs": 35,
        "timeframe_months": 12,
    },
    {
        "decision_type": "Kubernetes adoption",
        "outcome": "Operational complexity overhead",
        "org_count": 30,
        "total_orgs": 55,
        "timeframe_months": 18,
    },
    {
        "decision_type": "Kubernetes adoption",
        "outcome": "No issues",
        "org_count": 25,
        "total_orgs": 55,
        "timeframe_months": 18,
    },
    {
        "decision_type": "Monorepo adoption",
        "outcome": "Build time bottlenecks",
        "org_count": 20,
        "total_orgs": 40,
        "timeframe_months": 12,
    },
    {
        "decision_type": "GraphQL API",
        "outcome": "Performance complexity",
        "org_count": 13,
        "total_orgs": 35,
        "timeframe_months": 12,
    },
    {
        "decision_type": "Serverless adoption",
        "outcome": "Cold start latency issues",
        "org_count": 22,
        "total_orgs": 45,
        "timeframe_months": 12,
    },
    {
        "decision_type": "Service mesh adoption",
        "outcome": "Debugging complexity",
        "org_count": 25,
        "total_orgs": 30,
        "timeframe_months": 18,
    },
]


class CommunityDatabase:
    """SQLite-backed community database for architecture decision outcomes."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = ":memory:"
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        self._seed_if_empty()

    def _init_schema(self):
        """Initialize the database schema."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS community_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_type TEXT NOT NULL,
                outcome TEXT NOT NULL,
                org_count INTEGER NOT NULL DEFAULT 0,
                total_orgs INTEGER NOT NULL DEFAULT 0,
                timeframe_months INTEGER NOT NULL DEFAULT 12,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS submitted_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_type TEXT NOT NULL,
                outcome TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                anonymous_id TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_outcomes_decision
                ON community_outcomes(decision_type);
            CREATE INDEX IF NOT EXISTS idx_submitted_decision
                ON submitted_outcomes(decision_type);
        """)
        self.conn.commit()

    def _seed_if_empty(self):
        """Seed the database with initial community data if empty."""
        count = self.conn.execute(
            "SELECT COUNT(*) FROM community_outcomes"
        ).fetchone()[0]
        if count > 0:
            return

        now = datetime.now(timezone.utc).isoformat()
        for entry in COMMUNITY_SEED_DATA:
            self.conn.execute(
                """INSERT INTO community_outcomes
                   (decision_type, outcome, org_count, total_orgs, timeframe_months, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    entry["decision_type"],
                    entry["outcome"],
                    entry["org_count"],
                    entry["total_orgs"],
                    entry["timeframe_months"],
                    now,
                ),
            )
        self.conn.commit()

    def get_outcomes_for_decision(self, decision_type: str) -> List[Dict]:
        """Get community outcomes for a specific decision type."""
        cursor = self.conn.execute(
            """SELECT decision_type, outcome, org_count, total_orgs, timeframe_months
               FROM community_outcomes
               WHERE decision_type = ?""",
            (decision_type,),
        )
        results = []
        for row in cursor:
            results.append({
                "decision_type": row["decision_type"],
                "outcome": row["outcome"],
                "org_count": row["org_count"],
                "total_orgs": row["total_orgs"],
                "timeframe_months": row["timeframe_months"],
                "probability": round(row["org_count"] / max(1, row["total_orgs"]), 3),
            })
        return results

    def search_outcomes(self, keyword: str) -> List[Dict]:
        """Search community outcomes by keyword."""
        cursor = self.conn.execute(
            """SELECT decision_type, outcome, org_count, total_orgs, timeframe_months
               FROM community_outcomes
               WHERE decision_type LIKE ? OR outcome LIKE ?""",
            (f"%{keyword}%", f"%{keyword}%"),
        )
        results = []
        for row in cursor:
            results.append({
                "decision_type": row["decision_type"],
                "outcome": row["outcome"],
                "org_count": row["org_count"],
                "total_orgs": row["total_orgs"],
                "timeframe_months": row["timeframe_months"],
                "probability": round(row["org_count"] / max(1, row["total_orgs"]), 3),
            })
        return results

    def submit_outcome(
        self, decision_type: str, outcome: str, anonymous_id: str = ""
    ):
        """Submit an anonymous outcome to the community database."""
        if not anonymous_id:
            import hashlib
            anonymous_id = hashlib.sha256(
                f"{decision_type}:{outcome}:{datetime.now(timezone.utc).isoformat()}".encode()
            ).hexdigest()[:16]

        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT INTO submitted_outcomes
               (decision_type, outcome, submitted_at, anonymous_id)
               VALUES (?, ?, ?, ?)""",
            (decision_type, outcome, now, anonymous_id),
        )
        self.conn.commit()

    def get_decision_types(self) -> List[str]:
        """Get all unique decision types in the database."""
        cursor = self.conn.execute(
            "SELECT DISTINCT decision_type FROM community_outcomes ORDER BY decision_type"
        )
        return [row[0] for row in cursor]

    def get_outcome_counts(self) -> Dict[str, int]:
        """Get total outcome counts per decision type."""
        cursor = self.conn.execute(
            """SELECT decision_type, SUM(org_count) as total
               FROM community_outcomes
               GROUP BY decision_type"""
        )
        return {row[0]: row[1] for row in cursor}

    def get_total_decision_types(self) -> int:
        """Get total number of unique decision types."""
        cursor = self.conn.execute(
            "SELECT COUNT(DISTINCT decision_type) FROM community_outcomes"
        )
        return cursor.fetchone()[0]

    def get_total_organizations(self) -> int:
        """Get total number of organizations represented."""
        cursor = self.conn.execute(
            "SELECT SUM(total_orgs) FROM community_outcomes"
        )
        result = cursor.fetchone()[0]
        return result if result else 0

    def close(self):
        """Close the database connection."""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
