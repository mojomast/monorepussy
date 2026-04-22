"""Journal & Minutes — Immutable Parliamentary Record."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ussy_parliament.models import EntryType, JournalEntry
from ussy_parliament.storage import JournalStore


class JournalEngine:
    def __init__(self, store: JournalStore):
        self.store = store

    def append(
        self,
        entry_type: EntryType,
        data: dict,
        session_id: str = "",
    ) -> JournalEntry:
        entry_id = f"J-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.now(timezone.utc)
        previous_hash = self.store.head_hash()
        payload = json.dumps(data, default=str).encode("utf-8")
        entry = JournalEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            entry_type=entry_type,
            data=payload,
            previous_hash=previous_hash,
            session_id=session_id,
        )
        self.store.append(entry)
        return entry

    def view_session(self, session_id: str) -> List[JournalEntry]:
        return self.store.filter_by_session(session_id)

    def verify(self) -> bool:
        return self.store.verify_chain()

    def generate_minutes(self, session_id: str) -> str:
        entries = self.view_session(session_id)
        lines = [f"# Minutes for Session {session_id}", ""]
        for entry in entries:
            ts = entry.timestamp.isoformat()
            lines.append(f"## [{entry.hash.hex()[:8]}] {ts}  {entry.entry_type.value.upper()}")
            try:
                data = json.loads(entry.data.decode("utf-8"))
                for key, value in data.items():
                    lines.append(f"- **{key}**: {value}")
            except Exception:
                lines.append(f"- {entry.data.decode('utf-8', errors='replace')}")
            lines.append("")
        return "\n".join(lines)

    def last_entry(self) -> Optional[JournalEntry]:
        entries = self.store.iter_entries()
        return entries[-1] if entries else None

    def chain_length(self) -> int:
        return len(self.store.iter_entries())
