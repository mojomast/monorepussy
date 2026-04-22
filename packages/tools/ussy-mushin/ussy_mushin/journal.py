"""Evaluation journal — replayable computation history.

Every expression evaluated within a Mushin workspace is recorded in a
journal entry.  The journal is an append-only log that can be replayed
to reconstruct workspace state.

Each entry records:
- timestamp  (ISO-8601, UTC)
- expression (the code or command that was evaluated)
- output     (stdout / result text)
- result_type(one of ``"success"``, ``"error"``, ``"info"``)
- context    (optional dict — file, line, language, etc.)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from ussy_mushin.storage import (
    JOURNALS_DIR,
    _ensure_subdir,
    atomic_write_json,
    mushin_root,
    read_json,
    ts_now,
    ts_parse,
)


@dataclass
class JournalEntry:
    """A single evaluation record in the journal."""

    expression: str
    output: str = ""
    result_type: str = "success"  # success | error | info
    timestamp: str = ""
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = ts_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "expression": self.expression,
            "output": self.output,
            "result_type": self.result_type,
            "timestamp": self.timestamp,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JournalEntry:
        return cls(
            expression=data["expression"],
            output=data.get("output", ""),
            result_type=data.get("result_type", "success"),
            timestamp=data.get("timestamp", ""),
            context=data.get("context", {}),
        )


class Journal:
    """Append-only evaluation journal for a workspace.

    The journal is stored as a single JSON file per workspace:
    ``.mushin/journals/<workspace_id>.json``
    """

    def __init__(self, project_dir: str | Path, workspace_id: str) -> None:
        self.project_dir = Path(project_dir)
        self.workspace_id = workspace_id
        self._entries: list[JournalEntry] = []
        self._load()

    # -- persistence ----------------------------------------------------------

    @property
    def _path(self) -> Path:
        root = mushin_root(self.project_dir)
        d = _ensure_subdir(root, JOURNALS_DIR)
        return d / f"{self.workspace_id}.json"

    def _load(self) -> None:
        data = read_json(self._path)
        if data and isinstance(data, list):
            self._entries = [JournalEntry.from_dict(e) for e in data]

    def save(self) -> None:
        atomic_write_json(self._path, [e.to_dict() for e in self._entries])

    # -- mutation -------------------------------------------------------------

    def record(
        self,
        expression: str,
        output: str = "",
        result_type: str = "success",
        context: dict[str, Any] | None = None,
    ) -> JournalEntry:
        """Append a new entry and persist the journal."""
        entry = JournalEntry(
            expression=expression,
            output=output,
            result_type=result_type,
            context=context or {},
        )
        self._entries.append(entry)
        self.save()
        return entry

    # -- query ----------------------------------------------------------------

    @property
    def entries(self) -> list[JournalEntry]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[JournalEntry]:
        return iter(self._entries)

    def __getitem__(self, index: int) -> JournalEntry:
        return self._entries[index]

    def last(self) -> JournalEntry | None:
        return self._entries[-1] if self._entries else None

    def search(self, query: str) -> list[JournalEntry]:
        """Return entries whose expression or output contains *query*."""
        q = query.lower()
        return [
            e
            for e in self._entries
            if q in e.expression.lower() or q in e.output.lower()
        ]

    def filter_by_type(self, result_type: str) -> list[JournalEntry]:
        """Return entries with the given *result_type*."""
        return [e for e in self._entries if e.result_type == result_type]

    def filter_by_time_range(
        self, start: datetime, end: datetime
    ) -> list[JournalEntry]:
        """Return entries whose timestamp falls within [*start*, *end*]."""
        results: list[JournalEntry] = []
        for e in self._entries:
            if e.timestamp:
                try:
                    ts = ts_parse(e.timestamp)
                    if start <= ts <= end:
                        results.append(e)
                except (ValueError, TypeError):
                    continue
        return results

    # -- replay ---------------------------------------------------------------

    def replay(self, executor: Any | None = None) -> list[tuple[str, str]]:
        """Replay every expression in the journal.

        If *executor* is a callable, it is called with ``(expression,)``
        and must return ``(output, result_type)``.  Otherwise the stored
        outputs are returned verbatim.

        Returns a list of ``(expression, output)`` pairs.
        """
        results: list[tuple[str, str]] = []
        for entry in self._entries:
            if executor is not None and callable(executor):
                try:
                    out, rtype = executor(entry.expression)
                    results.append((entry.expression, out))
                except Exception as exc:
                    results.append((entry.expression, f"REPLAY ERROR: {exc}"))
            else:
                results.append((entry.expression, entry.output))
        return results

    # -- export ---------------------------------------------------------------

    def export_text(self) -> str:
        """Export the journal as a human-readable text transcript."""
        lines: list[str] = []
        for e in self._entries:
            lines.append(f"[{e.timestamp}] ({e.result_type}) >>> {e.expression}")
            if e.output:
                lines.append(e.output)
            lines.append("")
        return "\n".join(lines)
