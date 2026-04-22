"""SQLite storage for Coroner forensic data."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ussy_coroner.models import (
    CustodyChain,
    CustodyComparison,
    CustodyEntry,
    ErrorStain,
    Investigation,
    LuminolFinding,
    LuminolReport,
    LuminolResult,
    PipelineRun,
    SpatterReconstruction,
    Stage,
    StageStatus,
    StriationMatch,
    TraceEvidence,
    TraceTransferResult,
    TraceType,
    VelocityClass,
)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS stages (
    run_id TEXT NOT NULL,
    name TEXT NOT NULL,
    stage_index INTEGER NOT NULL,
    status TEXT NOT NULL,
    start_time TEXT,
    end_time TEXT,
    log_content TEXT DEFAULT '',
    env_vars TEXT DEFAULT '{}',
    artifacts TEXT DEFAULT '[]',
    artifact_hashes TEXT DEFAULT '{}',
    PRIMARY KEY (run_id, name),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    source_stage TEXT NOT NULL,
    target_stage TEXT NOT NULL,
    trace_type TEXT NOT NULL,
    strength REAL DEFAULT 1.0,
    description TEXT DEFAULT '',
    source_index INTEGER DEFAULT 0,
    target_index INTEGER DEFAULT 0,
    suspicion_score REAL DEFAULT 0.0,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS stains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    stage_name TEXT NOT NULL,
    stage_index INTEGER NOT NULL,
    breadth INTEGER DEFAULT 0,
    depth INTEGER DEFAULT 0,
    impact_angle REAL DEFAULT 0.0,
    component TEXT DEFAULT '',
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS striations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    compare_run_id TEXT NOT NULL,
    correlation REAL DEFAULT 0.0,
    same_root_cause INTEGER DEFAULT 0,
    resolution_note TEXT DEFAULT '',
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS luminol_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    category TEXT NOT NULL,
    path TEXT DEFAULT '',
    expected_hash TEXT DEFAULT '',
    actual_hash TEXT DEFAULT '',
    env_vars TEXT DEFAULT '[]',
    source_stage TEXT DEFAULT '',
    target_stage TEXT DEFAULT '',
    result TEXT NOT NULL,
    description TEXT DEFAULT '',
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS custody_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    stage_name TEXT NOT NULL,
    stage_index INTEGER NOT NULL,
    handler TEXT DEFAULT '',
    timestamp TEXT NOT NULL,
    action TEXT DEFAULT '',
    hash_value TEXT DEFAULT '',
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
"""


class ForensicDB:
    """SQLite database for forensic evidence storage."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = Path(path) if path != ":memory:" else path
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ── Runs ───────────────────────────────────────────────────────────

    def save_run(self, run: PipelineRun) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, timestamp, metadata) VALUES (?, ?, ?)",
            (run.run_id, run.timestamp.isoformat(), json.dumps(run.metadata)),
        )
        for stage in run.stages:
            self._save_stage(run.run_id, stage)
        self.conn.commit()

    def _save_stage(self, run_id: str, stage: Stage) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO stages
               (run_id, name, stage_index, status, start_time, end_time,
                log_content, env_vars, artifacts, artifact_hashes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                stage.name,
                stage.index,
                stage.status.value,
                stage.start_time.isoformat() if stage.start_time else None,
                stage.end_time.isoformat() if stage.end_time else None,
                stage.log_content,
                json.dumps(stage.env_vars),
                json.dumps(stage.artifacts),
                json.dumps(stage.artifact_hashes),
            ),
        )

    def load_run(self, run_id: str) -> PipelineRun | None:
        row = self.conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if not row:
            return None
        run = PipelineRun(
            run_id=row["run_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            metadata=json.loads(row["metadata"]),
        )
        stage_rows = self.conn.execute(
            "SELECT * FROM stages WHERE run_id = ? ORDER BY stage_index",
            (run_id,),
        ).fetchall()
        for sr in stage_rows:
            stage = Stage(
                name=sr["name"],
                index=sr["stage_index"],
                status=StageStatus(sr["status"]),
                start_time=datetime.fromisoformat(sr["start_time"]) if sr["start_time"] else None,
                end_time=datetime.fromisoformat(sr["end_time"]) if sr["end_time"] else None,
                log_content=sr["log_content"] or "",
                env_vars=json.loads(sr["env_vars"]),
                artifacts=json.loads(sr["artifacts"]),
                artifact_hashes=json.loads(sr["artifact_hashes"]),
            )
            run.stages.append(stage)
        return run

    def list_runs(self) -> list[str]:
        rows = self.conn.execute("SELECT run_id FROM runs ORDER BY timestamp DESC").fetchall()
        return [r["run_id"] for r in rows]

    # ── Traces ─────────────────────────────────────────────────────────

    def save_traces(self, run_id: str, result: TraceTransferResult) -> None:
        for t in result.forward_traces + result.reverse_traces + result.suspicious_transfers:
            self.conn.execute(
                """INSERT INTO traces
                   (run_id, source_stage, target_stage, trace_type, strength,
                    description, source_index, target_index, suspicion_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id, t.source_stage, t.target_stage, t.trace_type.value,
                    t.strength, t.description, t.source_index, t.target_index,
                    t.suspicion_score,
                ),
            )
        self.conn.commit()

    def load_traces(self, run_id: str) -> TraceTransferResult:
        rows = self.conn.execute(
            "SELECT * FROM traces WHERE run_id = ?", (run_id,)
        ).fetchall()
        forward: list[TraceEvidence] = []
        reverse: list[TraceEvidence] = []
        suspicious: list[TraceEvidence] = []
        for r in rows:
            te = TraceEvidence(
                source_stage=r["source_stage"],
                target_stage=r["target_stage"],
                trace_type=TraceType(r["trace_type"]),
                strength=r["strength"],
                description=r["description"],
                source_index=r["source_index"],
                target_index=r["target_index"],
            )
            te.suspicion_score = r["suspicion_score"]
            if r["source_index"] < r["target_index"]:
                forward.append(te)
            else:
                reverse.append(te)
            if te.suspicion_score > 0.7:
                suspicious.append(te)
        return TraceTransferResult(
            forward_traces=forward,
            reverse_traces=reverse,
            suspicious_transfers=suspicious,
        )

    # ── Stains ─────────────────────────────────────────────────────────

    def save_stains(self, run_id: str, stains: list[ErrorStain]) -> None:
        for s in stains:
            self.conn.execute(
                """INSERT INTO stains
                   (run_id, stage_name, stage_index, breadth, depth, impact_angle, component)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (run_id, s.stage_name, s.stage_index, s.breadth, s.depth, s.impact_angle, s.component),
            )
        self.conn.commit()

    def load_stains(self, run_id: str) -> list[ErrorStain]:
        rows = self.conn.execute(
            "SELECT * FROM stains WHERE run_id = ?", (run_id,)
        ).fetchall()
        result: list[ErrorStain] = []
        for r in rows:
            es = ErrorStain(
                stage_name=r["stage_name"],
                stage_index=r["stage_index"],
                breadth=r["breadth"],
                depth=r["depth"],
                component=r["component"],
            )
            es.impact_angle = r["impact_angle"]
            result.append(es)
        return result

    # ── Striations ─────────────────────────────────────────────────────

    def save_striation(self, run_id: str, match: StriationMatch) -> None:
        self.conn.execute(
            """INSERT INTO striations
               (run_id, compare_run_id, correlation, same_root_cause, resolution_note)
               VALUES (?, ?, ?, ?, ?)""",
            (run_id, match.build_id_2, match.correlation, int(match.same_root_cause), match.resolution_note),
        )
        self.conn.commit()

    def load_striations(self, run_id: str) -> list[StriationMatch]:
        rows = self.conn.execute(
            "SELECT * FROM striations WHERE run_id = ?", (run_id,)
        ).fetchall()
        result: list[StriationMatch] = []
        for r in rows:
            sm = StriationMatch(
                build_id_1=run_id,
                build_id_2=r["compare_run_id"],
                correlation=r["correlation"],
                resolution_note=r["resolution_note"],
            )
            sm.same_root_cause = bool(r["same_root_cause"])
            result.append(sm)
        return result

    # ── Luminol ────────────────────────────────────────────────────────

    def save_luminol(self, run_id: str, report: LuminolReport) -> None:
        for f in report.findings:
            self.conn.execute(
                """INSERT INTO luminol_findings
                   (run_id, category, path, expected_hash, actual_hash, env_vars,
                    source_stage, target_stage, result, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id, f.category, f.path, f.expected_hash, f.actual_hash,
                    json.dumps(f.env_vars), f.source_stage, f.target_stage,
                    f.result.value, f.description,
                ),
            )
        self.conn.commit()

    def load_luminol(self, run_id: str) -> LuminolReport:
        rows = self.conn.execute(
            "SELECT * FROM luminol_findings WHERE run_id = ?", (run_id,)
        ).fetchall()
        findings: list[LuminolFinding] = []
        for r in rows:
            findings.append(LuminolFinding(
                category=r["category"],
                path=r["path"],
                expected_hash=r["expected_hash"],
                actual_hash=r["actual_hash"],
                env_vars=json.loads(r["env_vars"]),
                source_stage=r["source_stage"],
                target_stage=r["target_stage"],
                result=LuminolResult(r["result"]),
                description=r["description"],
            ))
        return LuminolReport(findings=findings)

    # ── Custody ────────────────────────────────────────────────────────

    def save_custody(self, chain: CustodyChain) -> None:
        for e in chain.entries:
            self.conn.execute(
                """INSERT INTO custody_entries
                   (run_id, stage_name, stage_index, handler, timestamp, action, hash_value)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    chain.run_id, e.stage_name, e.stage_index, e.handler,
                    e.timestamp.isoformat(), e.action, e.hash_value,
                ),
            )
        self.conn.commit()

    def load_custody(self, run_id: str) -> CustodyChain:
        rows = self.conn.execute(
            "SELECT * FROM custody_entries WHERE run_id = ? ORDER BY stage_index",
            (run_id,),
        ).fetchall()
        entries: list[CustodyEntry] = []
        for r in rows:
            entries.append(CustodyEntry(
                stage_name=r["stage_name"],
                stage_index=r["stage_index"],
                handler=r["handler"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                action=r["action"],
                hash_value=r["hash_value"],
            ))
        return CustodyChain(run_id=run_id, entries=entries)
