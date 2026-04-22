"""Storage backends for Parliament."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from parliament.models import Agent, Appeal, EntryType, JournalEntry, Motion, PointOfOrder, Session, Vote


class SQLiteStore:
    """SQLite-backed store for session state."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS motions (
                    motion_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    scope TEXT,
                    impact_score REAL,
                    required_seconds INTEGER,
                    seconders TEXT,
                    status TEXT,
                    parent_id TEXT,
                    depth INTEGER,
                    created_at TEXT,
                    vote_method TEXT,
                    criticality_tier INTEGER
                );
                CREATE TABLE IF NOT EXISTS votes (
                    vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    motion_id TEXT,
                    agent_id TEXT,
                    aye INTEGER,
                    timestamp TEXT,
                    weight REAL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    motion_id TEXT,
                    agents_present TEXT,
                    quorum_required INTEGER,
                    quorum_verified INTEGER,
                    created_at TEXT,
                    closed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS points_of_order (
                    poo_id TEXT PRIMARY KEY,
                    motion_id TEXT,
                    violation_type TEXT,
                    claimant TEXT,
                    evidence TEXT,
                    timestamp TEXT,
                    sustained INTEGER,
                    remedy TEXT
                );
                CREATE TABLE IF NOT EXISTS appeals (
                    appeal_id TEXT PRIMARY KEY,
                    poo_id TEXT,
                    motion_id TEXT,
                    appealers TEXT,
                    timestamp TEXT,
                    outcome TEXT
                );
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    agent_type TEXT,
                    base_weight REAL,
                    error_count_30d INTEGER,
                    public_key TEXT,
                    active INTEGER
                );
                """
            )
            conn.commit()

    # Motions
    def save_motion(self, motion: Motion):
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO motions
                (motion_id, agent_id, action, scope, impact_score, required_seconds,
                 seconders, status, parent_id, depth, created_at, vote_method, criticality_tier)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    motion.motion_id,
                    motion.agent_id,
                    motion.action,
                    json.dumps(sorted(motion.scope)),
                    motion.impact_score,
                    motion.required_seconds,
                    json.dumps(sorted(motion.seconders)),
                    motion.status.value,
                    motion.parent_id,
                    motion.depth,
                    motion.created_at.isoformat(),
                    motion.vote_method.value,
                    motion.criticality_tier,
                ),
            )
            conn.commit()

    def get_motion(self, motion_id: str) -> Optional[Motion]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM motions WHERE motion_id = ?", (motion_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_motion(row)

    def list_motions(self) -> List[Motion]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM motions").fetchall()
        return [self._row_to_motion(r) for r in rows]

    def _row_to_motion(self, row: sqlite3.Row) -> Motion:
        from parliament.models import MotionStatus, VoteMethod

        return Motion(
            motion_id=row["motion_id"],
            agent_id=row["agent_id"],
            action=row["action"],
            scope=set(json.loads(row["scope"]) if row["scope"] else []),
            impact_score=row["impact_score"] or 0.0,
            required_seconds=row["required_seconds"] or 1,
            seconders=set(json.loads(row["seconders"]) if row["seconders"] else []),
            status=MotionStatus(row["status"]),
            parent_id=row["parent_id"],
            depth=row["depth"] or 0,
            vote_method=VoteMethod(row["vote_method"]),
            criticality_tier=row["criticality_tier"] or 1,
        )

    # Votes
    def save_vote(self, vote: Vote, motion_id: str):
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO votes (motion_id, agent_id, aye, timestamp, weight)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    motion_id,
                    vote.agent_id,
                    1 if vote.aye else 0,
                    vote.timestamp.isoformat(),
                    vote.weight,
                ),
            )
            conn.commit()

    def get_votes(self, motion_id: str) -> List[Vote]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM votes WHERE motion_id = ?", (motion_id,)
            ).fetchall()
        return [
            Vote(
                agent_id=r["agent_id"],
                aye=bool(r["aye"]),
                weight=r["weight"] or 0.0,
            )
            for r in rows
        ]

    # Sessions
    def save_session(self, session: Session):
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions
                (session_id, motion_id, agents_present, quorum_required, quorum_verified, created_at, closed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.motion_id,
                    json.dumps(sorted(session.agents_present)),
                    session.quorum_required,
                    1 if session.quorum_verified else 0,
                    session.created_at.isoformat(),
                    session.closed_at.isoformat() if session.closed_at else None,
                ),
            )
            conn.commit()

    def get_session(self, session_id: str) -> Optional[Session]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_session(row)

    def get_session_by_motion(self, motion_id: str) -> Optional[Session]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE motion_id = ?", (motion_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_session(row)

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        return Session(
            session_id=row["session_id"],
            motion_id=row["motion_id"],
            agents_present=set(json.loads(row["agents_present"]) if row["agents_present"] else []),
            quorum_required=row["quorum_required"] or 0,
            quorum_verified=bool(row["quorum_verified"]),
        )

    # Points of order
    def save_point_of_order(self, poo: PointOfOrder):
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO points_of_order
                (poo_id, motion_id, violation_type, claimant, evidence, timestamp, sustained, remedy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    poo.poo_id,
                    poo.motion_id,
                    poo.violation_type.value,
                    poo.claimant,
                    json.dumps(poo.evidence),
                    poo.timestamp.isoformat(),
                    1 if poo.sustained else 0 if poo.sustained is not None else None,
                    poo.remedy,
                ),
            )
            conn.commit()

    def get_point_of_order(self, poo_id: str) -> Optional[PointOfOrder]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM points_of_order WHERE poo_id = ?", (poo_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_poo(row)

    def list_points_of_order(self, motion_id: str) -> List[PointOfOrder]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM points_of_order WHERE motion_id = ?", (motion_id,)
            ).fetchall()
        return [self._row_to_poo(r) for r in rows]

    def _row_to_poo(self, row: sqlite3.Row) -> PointOfOrder:
        from parliament.models import ViolationType

        sustained = row["sustained"]
        if sustained is None:
            sustained = None
        else:
            sustained = bool(sustained)
        return PointOfOrder(
            poo_id=row["poo_id"],
            motion_id=row["motion_id"],
            violation_type=ViolationType(row["violation_type"]),
            claimant=row["claimant"],
            evidence=json.loads(row["evidence"]) if row["evidence"] else {},
            sustained=sustained,
            remedy=row["remedy"],
        )

    # Appeals
    def save_appeal(self, appeal: Appeal):
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO appeals
                (appeal_id, poo_id, motion_id, appealers, timestamp, outcome)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    appeal.appeal_id,
                    appeal.poo_id,
                    appeal.motion_id,
                    json.dumps(appeal.appealers),
                    appeal.timestamp.isoformat(),
                    appeal.outcome.value if appeal.outcome else None,
                ),
            )
            conn.commit()

    def get_appeal(self, appeal_id: str) -> Optional[Appeal]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM appeals WHERE appeal_id = ?", (appeal_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_appeal(row)

    def _row_to_appeal(self, row: sqlite3.Row) -> Appeal:
        from parliament.models import RulingOutcome

        outcome = row["outcome"]
        return Appeal(
            appeal_id=row["appeal_id"],
            poo_id=row["poo_id"],
            motion_id=row["motion_id"],
            appealers=json.loads(row["appealers"]) if row["appealers"] else [],
            outcome=RulingOutcome(outcome) if outcome else None,
        )

    # Agents
    def save_agent(self, agent: Agent):
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO agents
                (agent_id, agent_type, base_weight, error_count_30d, public_key, active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    agent.agent_id,
                    agent.agent_type,
                    agent.base_weight,
                    agent.error_count_30d,
                    agent.public_key,
                    1 if agent.active else 0,
                ),
            )
            conn.commit()

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM agents WHERE agent_id = ?", (agent_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_agent(row)

    def list_agents(self) -> List[Agent]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM agents").fetchall()
        return [self._row_to_agent(r) for r in rows]

    def _row_to_agent(self, row: sqlite3.Row) -> Agent:
        return Agent(
            agent_id=row["agent_id"],
            agent_type=row["agent_type"],
            base_weight=row["base_weight"] or 1.0,
            error_count_30d=row["error_count_30d"] or 0,
            public_key=row["public_key"],
            active=bool(row["active"]),
        )


class JournalStore:
    """Append-only flat file journal with SHA-256 chaining."""

    def __init__(self, journal_path: str | Path):
        self.journal_path = Path(journal_path)
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.journal_path.exists():
            self.journal_path.write_text("")

    def append(self, entry: JournalEntry):
        line = json.dumps(entry.to_dict()) + "\n"
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(line)

    def iter_entries(self) -> List[JournalEntry]:
        entries: List[JournalEntry] = []
        if not self.journal_path.exists():
            return entries
        with open(self.journal_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                entry = JournalEntry(
                    entry_id=obj["entry_id"],
                    timestamp=__import__("datetime").datetime.fromisoformat(obj["timestamp"]),
                    entry_type=EntryType(obj["entry_type"]),
                    data=obj["data"].encode("utf-8"),
                    previous_hash=bytes.fromhex(obj["previous_hash"]),
                    session_id=obj.get("session_id", ""),
                )
                entry._stored_hash = bytes.fromhex(obj["hash"])
                entries.append(entry)
        return entries

    def head_hash(self) -> bytes:
        entries = self.iter_entries()
        if not entries:
            return b""
        return entries[-1]._stored_hash

    def filter_by_session(self, session_id: str) -> List[JournalEntry]:
        return [e for e in self.iter_entries() if e.session_id == session_id]

    def verify_chain(self) -> bool:
        entries = self.iter_entries()
        if not entries:
            return True
        prev_hash = b""
        for entry in entries:
            if entry.previous_hash != prev_hash:
                return False
            computed = __import__("hashlib").sha256(
                entry.previous_hash
                + entry.timestamp.isoformat().encode("utf-8")
                + entry.data
            ).digest()
            if computed != entry._stored_hash:
                return False
            prev_hash = entry._stored_hash
        return True
