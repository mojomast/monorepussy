"""SQLite storage backend for Curator."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class Storage:
    """Manages SQLite storage for all curation instruments."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS accession_registry (
        accession_number TEXT PRIMARY KEY,
        path TEXT NOT NULL,
        submitter TEXT,
        date TEXT,
        origin TEXT,
        status TEXT
    );

    CREATE TABLE IF NOT EXISTS marc_records (
        path TEXT PRIMARY KEY,
        fields TEXT,
        completeness_score REAL
    );

    CREATE TABLE IF NOT EXISTS classification (
        path TEXT PRIMARY KEY,
        notation TEXT,
        hierarchy TEXT,
        facets TEXT
    );

    CREATE TABLE IF NOT EXISTS conservation_reports (
        path TEXT PRIMARY KEY,
        metrics TEXT,
        deterioration_rate REAL,
        condition_index REAL,
        grade TEXT,
        treatment TEXT
    );

    CREATE TABLE IF NOT EXISTS provenance_chains (
        path TEXT PRIMARY KEY,
        accession_number TEXT,
        chain TEXT,
        completeness REAL,
        gaps TEXT
    );

    CREATE TABLE IF NOT EXISTS exhibitions (
        name TEXT PRIMARY KEY,
        theme TEXT,
        audience_profile TEXT,
        max_items INTEGER,
        selection TEXT
    );

    CREATE TABLE IF NOT EXISTS weeding_proposals (
        path TEXT PRIMARY KEY,
        accession_number TEXT,
        title TEXT,
        weed_score REAL,
        triggered_criteria TEXT,
        justification TEXT,
        impact_assessment TEXT,
        disposition TEXT,
        ethical_review INTEGER
    );
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def initialize(self) -> None:
        """Create all tables."""
        self.conn.executescript(self.SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # Accession registry
    def next_acquisition_sequence(self, year: int) -> int:
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM accession_registry WHERE accession_number LIKE ?",
            (f"{year}.%",)
        )
        row = cur.fetchone()
        return (row[0] if row else 0) + 1

    def record_accession(self, record: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO accession_registry
            (accession_number, path, submitter, date, origin, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record.get("accession_number"),
                record.get("path"),
                record.get("submitter"),
                record.get("date"),
                record.get("origin"),
                record.get("status"),
            ),
        )
        self.conn.commit()

    def get_accession(self, path: Path) -> str | None:
        cur = self.conn.execute(
            "SELECT accession_number FROM accession_registry WHERE path = ?",
            (str(path),)
        )
        row = cur.fetchone()
        return row[0] if row else None

    def get_accession_by_number(self, number: str) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM accession_registry WHERE accession_number = ?",
            (number,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    # MARC records
    def save_marc_record(self, path: Path, fields: dict[str, Any], score: float) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO marc_records (path, fields, completeness_score) VALUES (?, ?, ?)",
            (str(path), json.dumps(fields), score),
        )
        self.conn.commit()

    def get_marc_record(self, path: Path) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM marc_records WHERE path = ?", (str(path),)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "path": row["path"],
            "fields": json.loads(row["fields"]),
            "completeness_score": row["completeness_score"],
        }

    # Classification
    def save_classification(self, path: Path, notation: str, hierarchy: str, facets: dict[str, str]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO classification (path, notation, hierarchy, facets) VALUES (?, ?, ?, ?)",
            (str(path), notation, hierarchy, json.dumps(facets)),
        )
        self.conn.commit()

    def get_classification(self, path: Path) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM classification WHERE path = ?", (str(path),)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "path": row["path"],
            "notation": row["notation"],
            "hierarchy": row["hierarchy"],
            "facets": json.loads(row["facets"]),
        }

    # Conservation
    def save_conservation_report(self, path: Path, report: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO conservation_reports
            (path, metrics, deterioration_rate, condition_index, grade, treatment)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(path),
                json.dumps(report.get("metrics", {})),
                report.get("deterioration_rate", 0.0),
                report.get("condition_index", 0.0),
                report.get("grade", ""),
                report.get("treatment", ""),
            ),
        )
        self.conn.commit()

    def get_conservation_report(self, path: Path) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM conservation_reports WHERE path = ?", (str(path),)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "path": row["path"],
            "metrics": json.loads(row["metrics"]),
            "deterioration_rate": row["deterioration_rate"],
            "condition_index": row["condition_index"],
            "grade": row["grade"],
            "treatment": row["treatment"],
        }

    # Provenance
    def save_provenance_chain(self, path: Path, chain_data: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO provenance_chains
            (path, accession_number, chain, completeness, gaps)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(path),
                chain_data.get("accession_number", ""),
                json.dumps(chain_data.get("chain", [])),
                chain_data.get("completeness", 0.0),
                json.dumps(chain_data.get("gaps", [])),
            ),
        )
        self.conn.commit()

    def get_provenance_chain(self, path: Path) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM provenance_chains WHERE path = ?", (str(path),)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "path": row["path"],
            "accession_number": row["accession_number"],
            "chain": json.loads(row["chain"]),
            "completeness": row["completeness"],
            "gaps": json.loads(row["gaps"]),
        }

    # Exhibitions
    def save_exhibition(self, exhibition: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO exhibitions
            (name, theme, audience_profile, max_items, selection)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                exhibition.get("name"),
                exhibition.get("theme"),
                json.dumps(exhibition.get("audience_profile", {})),
                exhibition.get("max_items", 20),
                json.dumps([str(s) for s in exhibition.get("selection", [])]),
            ),
        )
        self.conn.commit()

    def get_exhibition(self, name: str) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM exhibitions WHERE name = ?", (name,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "name": row["name"],
            "theme": row["theme"],
            "audience_profile": json.loads(row["audience_profile"]),
            "max_items": row["max_items"],
            "selection": json.loads(row["selection"]),
        }

    # Weeding
    def save_weeding_proposal(self, proposal: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO weeding_proposals
            (path, accession_number, title, weed_score, triggered_criteria,
             justification, impact_assessment, disposition, ethical_review)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(proposal.get("path", "")),
                proposal.get("accession_number", ""),
                proposal.get("title", ""),
                proposal.get("weed_score", 0.0),
                json.dumps(proposal.get("triggered_criteria", [])),
                proposal.get("justification", ""),
                json.dumps(proposal.get("impact_assessment", {})),
                proposal.get("disposition", ""),
                1 if proposal.get("ethical_review") else 0,
            ),
        )
        self.conn.commit()

    def get_weeding_proposal(self, path: Path) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM weeding_proposals WHERE path = ?", (str(path),)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "path": row["path"],
            "accession_number": row["accession_number"],
            "title": row["title"],
            "weed_score": row["weed_score"],
            "triggered_criteria": json.loads(row["triggered_criteria"]),
            "justification": row["justification"],
            "impact_assessment": json.loads(row["impact_assessment"]),
            "disposition": row["disposition"],
            "ethical_review": bool(row["ethical_review"]),
        }

    def list_weeding_proposals(self) -> list[dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM weeding_proposals ORDER BY weed_score DESC")
        rows = cur.fetchall()
        result = []
        for row in rows:
            result.append({
                "path": row["path"],
                "accession_number": row["accession_number"],
                "title": row["title"],
                "weed_score": row["weed_score"],
                "triggered_criteria": json.loads(row["triggered_criteria"]),
                "justification": row["justification"],
                "impact_assessment": json.loads(row["impact_assessment"]),
                "disposition": row["disposition"],
                "ethical_review": bool(row["ethical_review"]),
            })
        return result
