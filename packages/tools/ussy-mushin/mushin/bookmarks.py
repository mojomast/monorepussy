"""Spatial bookmarks — "I was here" markers for code exploration.

Bookmarks capture more than just file:line — they record the surrounding
context (visible code, scroll position, annotations) so you can return
to exactly where you were in your thought process.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mushin.storage import (
    BOOKMARKS_DIR,
    _ensure_subdir,
    atomic_write_json,
    mushin_root,
    read_json,
    ts_now,
)


@dataclass
class Bookmark:
    """A spatial bookmark in the workspace."""

    name: str
    file_path: str = ""
    line: int = 0
    column: int = 0
    scroll_position: int = 0
    visible_range: tuple[int, int] = (0, 0)
    annotation: str = ""
    workspace_id: str = ""
    created_at: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = ts_now()
        if not self.workspace_id:
            from mushin.workspace import get_active_workspace_id

            wid = get_active_workspace_id(".")
            if wid:
                self.workspace_id = wid

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "scroll_position": self.scroll_position,
            "visible_range": list(self.visible_range),
            "annotation": self.annotation,
            "workspace_id": self.workspace_id,
            "created_at": self.created_at,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Bookmark:
        vr = data.get("visible_range", [0, 0])
        return cls(
            name=data["name"],
            file_path=data.get("file_path", ""),
            line=data.get("line", 0),
            column=data.get("column", 0),
            scroll_position=data.get("scroll_position", 0),
            visible_range=tuple(vr) if isinstance(vr, list) else (0, 0),
            annotation=data.get("annotation", ""),
            workspace_id=data.get("workspace_id", ""),
            created_at=data.get("created_at", ""),
            tags=data.get("tags", []),
        )


class BookmarkManager:
    """Manage spatial bookmarks for a project."""

    def __init__(self, project_dir: str | Path) -> None:
        self.project_dir = Path(project_dir)
        self._bookmarks: dict[str, Bookmark] = {}
        self._load()

    # -- persistence ----------------------------------------------------------

    @property
    def _path(self) -> Path:
        root = mushin_root(self.project_dir)
        d = _ensure_subdir(root, BOOKMARKS_DIR)
        return d / "bookmarks.json"

    def _load(self) -> None:
        data = read_json(self._path)
        if data and isinstance(data, list):
            for b in data:
                bm = Bookmark.from_dict(b)
                self._bookmarks[bm.name] = bm

    def save(self) -> None:
        atomic_write_json(
            self._path, [b.to_dict() for b in self._bookmarks.values()]
        )

    # -- operations -----------------------------------------------------------

    def add(
        self,
        name: str,
        file_path: str = "",
        line: int = 0,
        column: int = 0,
        scroll_position: int = 0,
        visible_range: tuple[int, int] = (0, 0),
        annotation: str = "",
        workspace_id: str = "",
        tags: list[str] | None = None,
    ) -> Bookmark:
        """Create and store a new bookmark."""
        if name in self._bookmarks:
            raise ValueError(f"Bookmark '{name}' already exists")
        bm = Bookmark(
            name=name,
            file_path=file_path,
            line=line,
            column=column,
            scroll_position=scroll_position,
            visible_range=visible_range,
            annotation=annotation,
            workspace_id=workspace_id,
            tags=tags or [],
        )
        self._bookmarks[name] = bm
        self.save()
        return bm

    def get(self, name: str) -> Bookmark | None:
        return self._bookmarks.get(name)

    def list_bookmarks(
        self, workspace_id: str | None = None, tag: str | None = None
    ) -> list[Bookmark]:
        """List bookmarks, optionally filtered by workspace or tag."""
        result = list(self._bookmarks.values())
        if workspace_id is not None:
            result = [b for b in result if b.workspace_id == workspace_id]
        if tag is not None:
            result = [b for b in result if tag in b.tags]
        return result

    def delete(self, name: str) -> bool:
        if name not in self._bookmarks:
            return False
        del self._bookmarks[name]
        self.save()
        return True

    def update(
        self,
        name: str,
        **kwargs: Any,
    ) -> Bookmark | None:
        """Update fields of an existing bookmark."""
        bm = self._bookmarks.get(name)
        if bm is None:
            return None
        for key, value in kwargs.items():
            if hasattr(bm, key):
                setattr(bm, key, value)
        self.save()
        return bm

    def search(self, query: str) -> list[Bookmark]:
        """Search bookmarks by name, file_path, or annotation."""
        q = query.lower()
        return [
            b
            for b in self._bookmarks.values()
            if q in b.name.lower()
            or q in b.file_path.lower()
            or q in b.annotation.lower()
        ]
