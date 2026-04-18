"""SQLite database for persistent storage of dependency data."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from gridiron.models import DependencyEdge, PackageInfo


class GridironDB:
    """SQLite-backed storage for dependency graph data."""

    def __init__(self, path: str = ":memory:") -> None:
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS packages (
                name TEXT PRIMARY KEY,
                version TEXT DEFAULT '0.0.0',
                is_direct INTEGER DEFAULT 0,
                maintainers INTEGER DEFAULT 1,
                last_release TEXT,
                release_frequency_days REAL DEFAULT 30.0,
                issue_response_days REAL DEFAULT 7.0,
                has_types INTEGER DEFAULT 0,
                has_docs INTEGER DEFAULT 0,
                has_tests INTEGER DEFAULT 0,
                api_surface_size INTEGER DEFAULT 1,
                side_effect_ratio REAL DEFAULT 0.0,
                type_pollution REAL DEFAULT 0.0,
                metadata_completeness REAL DEFAULT 1.0,
                semver_compliance REAL DEFAULT 1.0,
                risk_weight REAL DEFAULT 1.0,
                version_rigidity REAL DEFAULT 0.5,
                has_error_handler INTEGER DEFAULT 0,
                handler_timeout_ms REAL DEFAULT 1000.0,
                handler_retry_count INTEGER DEFAULT 3,
                handler_tds REAL DEFAULT 1.0,
                handler_pickup REAL DEFAULT 1.0,
                backup_packages TEXT DEFAULT '[]'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                version_constraint TEXT DEFAULT '*',
                coupling_strength REAL DEFAULT 1.0,
                is_dev INTEGER DEFAULT 0,
                FOREIGN KEY (source) REFERENCES packages(name),
                FOREIGN KEY (target) REFERENCES packages(name)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_type TEXT NOT NULL,
                project_path TEXT NOT NULL,
                result_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def save_package(self, pkg: PackageInfo) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO packages (
                name, version, is_direct, maintainers, last_release,
                release_frequency_days, issue_response_days, has_types,
                has_docs, has_tests, api_surface_size, side_effect_ratio,
                type_pollution, metadata_completeness, semver_compliance,
                risk_weight, version_rigidity, has_error_handler,
                handler_timeout_ms, handler_retry_count, handler_tds,
                handler_pickup, backup_packages
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pkg.name, pkg.version, int(pkg.is_direct), pkg.maintainers,
            pkg.last_release.isoformat() if pkg.last_release else None,
            pkg.release_frequency_days, pkg.issue_response_days,
            int(pkg.has_types), int(pkg.has_docs), int(pkg.has_tests),
            pkg.api_surface_size, pkg.side_effect_ratio, pkg.type_pollution,
            pkg.metadata_completeness, pkg.semver_compliance, pkg.risk_weight,
            pkg.version_rigidity, int(pkg.has_error_handler),
            pkg.handler_timeout_ms, pkg.handler_retry_count, pkg.handler_tds,
            pkg.handler_pickup, json.dumps(pkg.backup_packages),
        ))
        self.conn.commit()

    def save_edge(self, edge: DependencyEdge) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO edges (source, target, version_constraint, coupling_strength, is_dev)
            VALUES (?, ?, ?, ?, ?)
        """, (edge.source, edge.target, edge.version_constraint,
              edge.coupling_strength, int(edge.is_dev)))
        self.conn.commit()

    def load_package(self, name: str) -> Optional[PackageInfo]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM packages WHERE name = ?", (name,))
        row = cur.fetchone()
        if row is None:
            return None
        last_rel = None
        if row["last_release"]:
            last_rel = datetime.fromisoformat(row["last_release"])
        return PackageInfo(
            name=row["name"],
            version=row["version"],
            is_direct=bool(row["is_direct"]),
            maintainers=row["maintainers"],
            last_release=last_rel,
            release_frequency_days=row["release_frequency_days"],
            issue_response_days=row["issue_response_days"],
            has_types=bool(row["has_types"]),
            has_docs=bool(row["has_docs"]),
            has_tests=bool(row["has_tests"]),
            api_surface_size=row["api_surface_size"],
            side_effect_ratio=row["side_effect_ratio"],
            type_pollution=row["type_pollution"],
            metadata_completeness=row["metadata_completeness"],
            semver_compliance=row["semver_compliance"],
            risk_weight=row["risk_weight"],
            version_rigidity=row["version_rigidity"],
            has_error_handler=bool(row["has_error_handler"]),
            handler_timeout_ms=row["handler_timeout_ms"],
            handler_retry_count=row["handler_retry_count"],
            handler_tds=row["handler_tds"],
            handler_pickup=row["handler_pickup"],
            backup_packages=json.loads(row["backup_packages"]),
        )

    def load_all_packages(self) -> List[PackageInfo]:
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM packages")
        return [self.load_package(row["name"]) for row in cur.fetchall()]

    def load_all_edges(self) -> List[DependencyEdge]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM edges")
        edges = []
        for row in cur.fetchall():
            edges.append(DependencyEdge(
                source=row["source"],
                target=row["target"],
                version_constraint=row["version_constraint"],
                coupling_strength=row["coupling_strength"],
                is_dev=bool(row["is_dev"]),
            ))
        return edges

    def save_analysis(self, analysis_type: str, project_path: str, result: Dict[str, Any]) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO analysis_results (analysis_type, project_path, result_json, timestamp)
            VALUES (?, ?, ?, ?)
        """, (analysis_type, project_path, json.dumps(result, default=str),
              datetime.now(timezone.utc).isoformat()))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
