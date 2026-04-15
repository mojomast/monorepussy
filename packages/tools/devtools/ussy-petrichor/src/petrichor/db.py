"""SQLite storage layer for soil memory."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_DB_DIR = ".petrichor"
DEFAULT_DB_NAME = "soil.db"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SoilDB:
    """Manages the SQLite database that stores soil layers (drift history)."""

    def __init__(self, root: Optional[str] = None):
        """Initialize the soil database.

        Args:
            root: Root directory for the .petrichor/ folder.
                  Defaults to current working directory.
        """
        if root is None:
            root = str(Path.cwd())
        self.root = root
        self.db_dir = Path(root) / DEFAULT_DB_DIR
        self.db_path = self.db_dir / DEFAULT_DB_NAME

    def _connect(self) -> sqlite3.Connection:
        """Open a connection to the SQLite database."""
        self.db_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def initialize(self) -> str:
        """Create the database schema if it doesn't exist.

        Returns:
            Path to the created database.
        """
        conn = self._connect()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS soil_layers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    content_text TEXT NOT NULL,
                    diff_text TEXT DEFAULT '',
                    actor TEXT DEFAULT '',
                    context TEXT DEFAULT '',
                    is_drift INTEGER DEFAULT 0,
                    desired_hash TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_layers_path ON soil_layers(path);
                CREATE INDEX IF NOT EXISTS idx_layers_timestamp ON soil_layers(timestamp);
                CREATE INDEX IF NOT EXISTS idx_layers_path_ts ON soil_layers(path, timestamp);

                CREATE TABLE IF NOT EXISTS desired_state (
                    path TEXT PRIMARY KEY,
                    desired_hash TEXT NOT NULL,
                    desired_text TEXT DEFAULT '',
                    source TEXT DEFAULT '',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tracked_paths (
                    path TEXT PRIMARY KEY,
                    added_at TEXT NOT NULL,
                    source TEXT DEFAULT ''
                );
            """)
            conn.commit()
            return str(self.db_path)
        finally:
            conn.close()

    def add_layer(
        self,
        path: str,
        content_hash: str,
        content_text: str,
        diff_text: str = "",
        actor: str = "",
        context: str = "",
        is_drift: bool = False,
        desired_hash: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Record a new soil layer (state snapshot).

        Args:
            path: File path being tracked.
            content_hash: SHA-256 hash of the current content.
            content_text: Full content text.
            diff_text: Unified diff from previous layer.
            actor: Who/what made the change.
            context: Context for the change (e.g., incident ID).
            is_drift: Whether this layer represents drift.
            desired_hash: Hash of the desired state at this point.
            metadata: Optional JSON-serializable metadata dict.

        Returns:
            Row ID of the inserted layer.
        """
        conn = self._connect()
        try:
            cursor = conn.execute(
                """INSERT INTO soil_layers
                   (path, timestamp, content_hash, content_text, diff_text,
                    actor, context, is_drift, desired_hash, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    path,
                    _now().isoformat(),
                    content_hash,
                    content_text,
                    diff_text,
                    actor,
                    context,
                    int(is_drift),
                    desired_hash,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_layers(self, path: str, depth: int = 10) -> List[Dict[str, Any]]:
        """Retrieve soil layers for a path, most recent first.

        Args:
            path: File path.
            depth: Maximum number of layers to return.

        Returns:
            List of layer dicts with all columns.
        """
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT * FROM soil_layers
                   WHERE path = ?
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (path, depth),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_latest_layer(self, path: str) -> Optional[Dict[str, Any]]:
        """Get the most recent soil layer for a path.

        Args:
            path: File path.

        Returns:
            Layer dict or None if no layers exist.
        """
        layers = self.get_layers(path, depth=1)
        return layers[0] if layers else None

    def get_drift_layers(self, path: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get drift layers for a path within a time window.

        Args:
            path: File path.
            days: Number of days to look back.

        Returns:
            List of drift layer dicts.
        """
        conn = self._connect()
        try:
            cutoff = _now().timestamp() - (days * 86400)
            cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
            rows = conn.execute(
                """SELECT * FROM soil_layers
                   WHERE path = ? AND is_drift = 1 AND timestamp >= ?
                   ORDER BY timestamp DESC""",
                (path, cutoff_dt),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_all_drift_layers(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get all drift layers across all paths within a time window.

        Args:
            days: Number of days to look back.

        Returns:
            List of drift layer dicts.
        """
        conn = self._connect()
        try:
            cutoff = _now().timestamp() - (days * 86400)
            cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
            rows = conn.execute(
                """SELECT * FROM soil_layers
                   WHERE is_drift = 1 AND timestamp >= ?
                   ORDER BY timestamp DESC""",
                (cutoff_dt,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def set_desired_state(self, path: str, desired_hash: str, desired_text: str = "", source: str = "") -> None:
        """Set the desired state for a path.

        Args:
            path: File path.
            desired_hash: Hash of the desired content.
            desired_text: The desired content text.
            source: Source of the desired state (e.g., git URL).
        """
        conn = self._connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO desired_state
                   (path, desired_hash, desired_text, source, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (path, desired_hash, desired_text, source, _now().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_desired_state(self, path: str) -> Optional[Dict[str, Any]]:
        """Get the desired state for a path.

        Args:
            path: File path.

        Returns:
            Desired state dict or None.
        """
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM desired_state WHERE path = ?", (path,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def add_tracked_path(self, path: str, source: str = "") -> None:
        """Add a path to the tracking list.

        Args:
            path: File path to track.
            source: Source of the desired state.
        """
        conn = self._connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO tracked_paths (path, added_at, source)
                   VALUES (?, ?, ?)""",
                (path, _now().isoformat(), source),
            )
            conn.commit()
        finally:
            conn.close()

    def get_tracked_paths(self) -> List[str]:
        """Get all tracked file paths.

        Returns:
            List of path strings.
        """
        conn = self._connect()
        try:
            rows = conn.execute("SELECT path FROM tracked_paths").fetchall()
            return [r["path"] for r in rows]
        finally:
            conn.close()

    def remove_tracked_path(self, path: str) -> None:
        """Remove a path from tracking.

        Args:
            path: File path to stop tracking.
        """
        conn = self._connect()
        try:
            conn.execute("DELETE FROM tracked_paths WHERE path = ?", (path,))
            conn.commit()
        finally:
            conn.close()

    def get_drift_count(self, path: str, days: int = 30) -> int:
        """Count drift events for a path within a time window.

        Args:
            path: File path.
            days: Number of days to look back.

        Returns:
            Number of drift events.
        """
        return len(self.get_drift_layers(path, days))

    def get_path_drift_counts(self, days: int = 30) -> Dict[str, int]:
        """Get drift counts for all paths.

        Args:
            days: Number of days to look back.

        Returns:
            Dict mapping path to drift count.
        """
        drifts = self.get_all_drift_layers(days)
        counts: Dict[str, int] = {}
        for d in drifts:
            counts[d["path"]] = counts.get(d["path"], 0) + 1
        return counts
