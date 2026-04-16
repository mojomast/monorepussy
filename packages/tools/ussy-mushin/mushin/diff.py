"""Diff — compare workspace snapshots.

``mushin diff`` shows what changed between sessions or between branches,
at the level of journal entries, objects, and metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mushin.journal import Journal, JournalEntry
from mushin.workspace import Workspace, list_workspaces


@dataclass
class DiffResult:
    """The result of comparing two workspaces."""

    left_id: str = ""
    right_id: str = ""
    added_entries: list[JournalEntry] = field(default_factory=list)
    removed_entries: list[JournalEntry] = field(default_factory=list)
    added_objects: list[str] = field(default_factory=list)
    removed_objects: list[str] = field(default_factory=list)
    common_objects: list[str] = field(default_factory=list)
    meta_changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(
            self.added_entries
            or self.removed_entries
            or self.added_objects
            or self.removed_objects
            or self.meta_changes
        )

    def summary(self) -> str:
        lines: list[str] = []
        lines.append(f"Diff: {self.left_id[:8]}..{self.right_id[:8]}")
        lines.append(f"  Journal entries: +{len(self.added_entries)} / -{len(self.removed_entries)}")
        lines.append(f"  Objects: +{len(self.added_objects)} / -{len(self.removed_objects)} / ~{len(self.common_objects)}")
        if self.meta_changes:
            lines.append(f"  Metadata changes: {len(self.meta_changes)}")
            for key, (old, new) in self.meta_changes.items():
                lines.append(f"    {key}: {old!r} → {new!r}")
        return "\n".join(lines)


def diff_workspaces(
    left: Workspace, right: Workspace
) -> DiffResult:
    """Compare two workspaces and return the differences."""
    result = DiffResult(left_id=left.id, right_id=right.id)

    # --- Journal diff (by expression + timestamp) ---
    left_entries = {(e.expression, e.timestamp): e for e in left.journal.entries}
    right_entries = {(e.expression, e.timestamp): e for e in right.journal.entries}

    left_keys = set(left_entries.keys())
    right_keys = set(right_entries.keys())

    for key in sorted(right_keys - left_keys, key=lambda k: k[1]):
        result.added_entries.append(right_entries[key])
    for key in sorted(left_keys - right_keys, key=lambda k: k[1]):
        result.removed_entries.append(left_entries[key])

    # --- Objects diff ---
    left_objs = set(left.list_objects())
    right_objs = set(right.list_objects())

    result.added_objects = sorted(right_objs - left_objs)
    result.removed_objects = sorted(left_objs - right_objs)
    result.common_objects = sorted(left_objs & right_objs)

    # --- Meta diff ---
    left_dict = left.meta.to_dict()
    right_dict = right.meta.to_dict()
    all_keys = set(left_dict.keys()) | set(right_dict.keys())
    for k in sorted(all_keys):
        lv = left_dict.get(k)
        rv = right_dict.get(k)
        if lv != rv:
            result.meta_changes[k] = (lv, rv)

    return result
