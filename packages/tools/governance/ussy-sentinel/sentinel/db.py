"""SQLite persistence for profiles and detectors.

Provides storage for self-profiles and detector populations using SQLite.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .detectors import Detector, DetectorPopulation
from .profile import SelfProfile


# Schema version for migrations
SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL,
    granularity TEXT NOT NULL DEFAULT 'function',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS detector_populations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    profile_id INTEGER REFERENCES profiles(id),
    metric TEXT NOT NULL DEFAULT 'euclidean',
    matching_threshold REAL NOT NULL DEFAULT 0.3,
    generation INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detector_id TEXT NOT NULL,
    is_true_positive INTEGER NOT NULL,
    comment TEXT,
    created_at TEXT NOT NULL
);
"""


class SentinelDB:
    """SQLite database for Sentinel persistence."""

    def __init__(self, db_path: str):
        """Initialize the database.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._initialize()

    def _initialize(self):
        """Initialize the database schema."""
        conn = self._get_conn()
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION))
        )
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # --- Profile operations ---

    def save_profile(self, profile: SelfProfile, name: Optional[str] = None) -> int:
        """Save a self-profile to the database.

        Returns:
            The profile ID
        """
        conn = self._get_conn()
        pname = name or profile.name
        now = datetime.now().isoformat()

        # Check if profile with same name exists
        existing = conn.execute(
            "SELECT id FROM profiles WHERE name = ?", (pname,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE profiles SET root_path=?, granularity=?, updated_at=?, data=? WHERE name=?",
                (profile.root_path, profile.granularity, now, profile.to_json(), pname)
            )
            return existing['id']
        else:
            cursor = conn.execute(
                "INSERT INTO profiles (name, root_path, granularity, created_at, updated_at, data) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (pname, profile.root_path, profile.granularity, now, now, profile.to_json())
            )
            conn.commit()
            return cursor.lastrowid

    def load_profile(self, name: str) -> Optional[SelfProfile]:
        """Load a self-profile by name."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data FROM profiles WHERE name = ?", (name,)
        ).fetchone()

        if row:
            return SelfProfile.from_json(row['data'])
        return None

    def list_profiles(self) -> List[Dict]:
        """List all saved profiles."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, name, root_path, granularity, created_at, updated_at FROM profiles"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_profile(self, name: str) -> bool:
        """Delete a profile by name."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM profiles WHERE name = ?", (name,))
        conn.commit()
        return cursor.rowcount > 0

    # --- Detector population operations ---

    def save_detectors(self, population: DetectorPopulation, name: str,
                       profile_name: Optional[str] = None) -> int:
        """Save a detector population to the database.

        Returns:
            The population ID
        """
        conn = self._get_conn()
        now = datetime.now().isoformat()

        profile_id = None
        if profile_name:
            row = conn.execute(
                "SELECT id FROM profiles WHERE name = ?", (profile_name,)
            ).fetchone()
            if row:
                profile_id = row['id']

        # Check if population with same name exists
        existing = conn.execute(
            "SELECT id FROM detector_populations WHERE name = ?", (name,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE detector_populations SET metric=?, matching_threshold=?, "
                "generation=?, data=? WHERE name=?",
                (population.metric, population.matching_threshold,
                 population.generation, json.dumps(population.to_dict()), name)
            )
            return existing['id']
        else:
            cursor = conn.execute(
                "INSERT INTO detector_populations "
                "(name, profile_id, metric, matching_threshold, generation, created_at, data) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, profile_id, population.metric, population.matching_threshold,
                 population.generation, now, json.dumps(population.to_dict()))
            )
            conn.commit()
            return cursor.lastrowid

    def load_detectors(self, name: str) -> Optional[DetectorPopulation]:
        """Load a detector population by name."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data FROM detector_populations WHERE name = ?", (name,)
        ).fetchone()

        if row:
            return DetectorPopulation.from_dict(json.loads(row['data']))
        return None

    def list_detector_populations(self) -> List[Dict]:
        """List all saved detector populations."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, name, profile_id, metric, matching_threshold, "
            "generation, created_at FROM detector_populations"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_detectors(self, name: str) -> bool:
        """Delete a detector population by name."""
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM detector_populations WHERE name = ?", (name,)
        )
        conn.commit()
        return cursor.rowcount > 0

    # --- Feedback operations ---

    def save_feedback(self, detector_id: str, is_true_positive: bool,
                      comment: str = "") -> int:
        """Save feedback for a detector."""
        conn = self._get_conn()
        now = datetime.now().isoformat()
        cursor = conn.execute(
            "INSERT INTO feedback (detector_id, is_true_positive, comment, created_at) "
            "VALUES (?, ?, ?, ?)",
            (detector_id, 1 if is_true_positive else 0, comment, now)
        )
        conn.commit()
        return cursor.lastrowid

    def get_feedback(self, detector_id: str) -> List[Dict]:
        """Get all feedback for a detector."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM feedback WHERE detector_id = ? ORDER BY created_at",
            (detector_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_feedback_stats(self, detector_id: str) -> Dict:
        """Get feedback statistics for a detector."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN is_true_positive = 1 THEN 1 ELSE 0 END) as tp, "
            "SUM(CASE WHEN is_true_positive = 0 THEN 1 ELSE 0 END) as fp "
            "FROM feedback WHERE detector_id = ?",
            (detector_id,)
        ).fetchone()
        return dict(row) if row else {"total": 0, "tp": 0, "fp": 0}
