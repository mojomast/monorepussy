"""SQLite storage for Stemma projects."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import (
    Classification,
    CollationResult,
    StemmaTree,
    VariantType,
    VariationUnit,
    Witness,
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class StemmaDB:
    """SQLite database for storing stemma analysis results."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self.conn: Optional[sqlite3.Connection] = None

    def open(self) -> "StemmaDB":
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        return self

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> "StemmaDB":
        return self.open()

    def __exit__(self, *args) -> None:
        self.close()

    def _create_tables(self) -> None:
        assert self.conn is not None
        cursor = self.conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS witnesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                source TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS collations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                witness_count INTEGER NOT NULL,
                variant_count INTEGER NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS stemmata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                collation_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (collation_id) REFERENCES collations(id)
            );

            CREATE TABLE IF NOT EXISTS classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                collation_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (collation_id) REFERENCES collations(id)
            );
        """)
        self.conn.commit()

    def create_project(self, name: str) -> int:
        assert self.conn is not None
        now = _utcnow()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO projects (name, created_at, updated_at) VALUES (?, ?, ?)",
            (name, now, now),
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore

    def save_witnesses(self, project_id: int, witnesses: list[Witness]) -> None:
        assert self.conn is not None
        now = _utcnow()
        cursor = self.conn.cursor()
        for w in witnesses:
            cursor.execute(
                "INSERT INTO witnesses (project_id, label, source, content, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (project_id, w.label, w.source, "\n".join(w.lines), now),
            )
        self.conn.commit()

    def save_collation(self, project_id: int, collation: CollationResult) -> int:
        assert self.conn is not None
        now = _utcnow()
        data = self._serialize_collation(collation)
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO collations (project_id, witness_count, variant_count, data, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (project_id, len(collation.witnesses), collation.variant_count, data, now),
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore

    def save_stemma(self, project_id: int, collation_id: int, stemma: StemmaTree) -> int:
        assert self.conn is not None
        now = _utcnow()
        data = self._serialize_stemma(stemma)
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO stemmata (project_id, collation_id, data, created_at) "
            "VALUES (?, ?, ?, ?)",
            (project_id, collation_id, data, now),
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore

    def save_classifications(self, project_id: int, collation_id: int, collation: CollationResult) -> int:
        assert self.conn is not None
        now = _utcnow()
        data = self._serialize_classifications(collation)
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO classifications (project_id, collation_id, data, created_at) "
            "VALUES (?, ?, ?, ?)",
            (project_id, collation_id, data, now),
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore

    def get_project(self, project_id: int) -> Optional[dict]:
        assert self.conn is not None
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_projects(self) -> list[dict]:
        assert self.conn is not None
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_witnesses(self, project_id: int) -> list[dict]:
        assert self.conn is not None
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM witnesses WHERE project_id = ?", (project_id,))
        return [dict(row) for row in cursor.fetchall()]

    def _serialize_collation(self, collation: CollationResult) -> str:
        data = {
            "witnesses": [
                {"label": w.label, "source": w.source, "lines": w.lines}
                for w in collation.witnesses
            ],
            "variation_units": [
                {
                    "line_number": v.line_number,
                    "readings": [
                        {
                            "text": r.text,
                            "witnesses": r.witnesses,
                            "variant_type": r.variant_type.value,
                        }
                        for r in v.readings
                    ],
                    "classification": v.classification.value if v.classification else None,
                    "confidence": v.confidence,
                    "rationale": v.rationale,
                }
                for v in collation.variation_units
            ],
        }
        return json.dumps(data)

    def _serialize_stemma(self, stemma: StemmaTree) -> str:
        data = {
            "contaminated": stemma.contaminated,
            "nodes": self._serialize_node(stemma.root) if stemma.root else None,
        }
        return json.dumps(data)

    def _serialize_node(self, node: Optional[StemmaNode]) -> Optional[dict]:
        if node is None:
            return None
        return {
            "label": node.label,
            "role": node.role.value,
            "children": [self._serialize_node(c) for c in node.children],
            "annotation": node.annotation,
        }

    def _serialize_classifications(self, collation: CollationResult) -> str:
        data = []
        for v in collation.variation_units:
            if v.is_variant and v.classification:
                data.append({
                    "line_number": v.line_number,
                    "classification": v.classification.value,
                    "confidence": v.confidence,
                    "rationale": v.rationale,
                })
        return json.dumps(data)
