"""SQLite storage for per-project assay results."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ussy_assay.models import (
    Category,
    FunctionAnalysis,
    ModuleAnalysis,
    ProjectAnalysis,
)


_DB_NAME = ".assay.db"


def _db_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / _DB_NAME


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            project_path TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS function_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            function_name TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            grade REAL NOT NULL,
            total_lines INTEGER NOT NULL,
            business_lines INTEGER NOT NULL,
            category_counts TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs(id)
        );
    """)
    conn.commit()


def save_analysis(project: ProjectAnalysis, project_dir: str | Path) -> int:
    """Save a project analysis run to the database. Returns the run ID."""
    db = _db_path(project_dir)
    conn = _connect(db)
    _init_schema(conn)

    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO runs (timestamp, project_path) VALUES (?, ?)",
        (now, str(project_dir)),
    )
    run_id = cur.lastrowid

    for mod in project.modules:
        for func in mod.functions:
            conn.execute(
                """INSERT INTO function_results
                   (run_id, file_path, function_name, start_line, end_line,
                    grade, total_lines, business_lines, category_counts)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    func.file_path,
                    func.name,
                    func.start_line,
                    func.end_line,
                    func.grade,
                    func.total_lines,
                    func.business_lines,
                    json.dumps(func.category_counts),
                ),
            )

    conn.commit()
    conn.close()
    return run_id  # type: ignore[return-value]


def load_latest_run(project_dir: str | Path) -> Optional[ProjectAnalysis]:
    """Load the most recent analysis run from the database."""
    db = _db_path(project_dir)
    if not db.exists():
        return None

    conn = _connect(db)
    _init_schema(conn)

    row = conn.execute(
        "SELECT id FROM runs ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    if not row:
        conn.close()
        return None

    run_id = row["id"]
    rows = conn.execute(
        "SELECT * FROM function_results WHERE run_id = ?", (run_id,)
    ).fetchall()
    conn.close()

    # Reconstruct
    modules_map: dict[str, list[FunctionAnalysis]] = {}
    for r in rows:
        func = FunctionAnalysis(
            name=r["function_name"],
            file_path=r["file_path"],
            start_line=r["start_line"],
            end_line=r["end_line"],
            grade=r["grade"],
            category_counts=json.loads(r["category_counts"]),
            total_lines=r["total_lines"],
            business_lines=r["business_lines"],
        )
        modules_map.setdefault(r["file_path"], []).append(func)

    modules = [
        ModuleAnalysis(file_path=fp, functions=funcs)
        for fp, funcs in modules_map.items()
    ]

    return ProjectAnalysis(modules=modules)


def list_runs(project_dir: str | Path, limit: int = 10) -> list[dict]:
    """List recent analysis runs."""
    db = _db_path(project_dir)
    if not db.exists():
        return []

    conn = _connect(db)
    _init_schema(conn)

    rows = conn.execute(
        "SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()

    return [dict(r) for r in rows]
