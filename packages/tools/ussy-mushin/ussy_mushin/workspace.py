"""Workspace — the central persistence unit.

A workspace captures the full development context: the evaluation
journal, live objects, open files, and environment metadata.  Workspaces
are saved with ``mushin save`` and restored with ``mushin resume``.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ussy_mushin.journal import Journal
from ussy_mushin.storage import (
    ACTIVE_FILE,
    OBJECTS_DIR,
    WORKSPACES_DIR,
    _ensure_subdir,
    atomic_write_bytes,
    atomic_write_json,
    mushin_root,
    read_bytes,
    read_json,
    ts_now,
    ts_parse,
)


@dataclass
class WorkspaceMeta:
    """Metadata for a workspace snapshot."""

    id: str = ""
    name: str = ""
    created_at: str = ""
    saved_at: str = ""
    parent_id: str = ""  # for branches — empty means root
    branch_name: str = ""
    description: str = ""
    open_files: list[str] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = ts_now()
        if not self.saved_at:
            self.saved_at = self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "saved_at": self.saved_at,
            "parent_id": self.parent_id,
            "branch_name": self.branch_name,
            "description": self.description,
            "open_files": self.open_files,
            "environment": self.environment,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceMeta:
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            created_at=data.get("created_at", ""),
            saved_at=data.get("saved_at", ""),
            parent_id=data.get("parent_id", ""),
            branch_name=data.get("branch_name", ""),
            description=data.get("description", ""),
            open_files=data.get("open_files", []),
            environment=data.get("environment", {}),
        )


class Workspace:
    """A persistent workspace that can be saved, resumed, and branched.

    Usage::

        ws = Workspace.create("/path/to/project", name="explore-auth")
        ws.journal.record("import pandas as pd", "imported pandas")
        ws.save_object("df", my_dataframe)
        ws.save()
    """

    def __init__(self, project_dir: str | Path, workspace_id: str) -> None:
        self.project_dir = Path(project_dir)
        self.id = workspace_id
        self.meta: WorkspaceMeta = WorkspaceMeta(id=workspace_id)
        self.journal: Journal = Journal(project_dir, workspace_id)
        self._objects_cache: dict[str, Any] = {}
        self._loaded = False
        self._load()

    # -- factory / loading ----------------------------------------------------

    @classmethod
    def create(
        cls,
        project_dir: str | Path,
        name: str = "",
        description: str = "",
        parent_id: str = "",
        branch_name: str = "",
    ) -> Workspace:
        """Create a brand-new workspace with a generated ID."""
        uid = _generate_id()
        ws = cls.__new__(cls)
        ws.project_dir = Path(project_dir)
        ws.id = uid
        ws.meta = WorkspaceMeta(
            id=uid,
            name=name or uid[:8],
            description=description,
            parent_id=parent_id,
            branch_name=branch_name,
        )
        ws.journal = Journal(project_dir, uid)
        ws._objects_cache = {}
        ws._loaded = True
        return ws

    @classmethod
    def load(cls, project_dir: str | Path, workspace_id: str) -> Workspace:
        """Load an existing workspace from disk."""
        ws = cls(project_dir, workspace_id)
        return ws

    def _load(self) -> None:
        if self._loaded:
            return
        root = mushin_root(self.project_dir)
        meta_path = root / WORKSPACES_DIR / self.id / "meta.json"
        data = read_json(meta_path)
        if data:
            self.meta = WorkspaceMeta.from_dict(data)
        self._loaded = True

    # -- paths ----------------------------------------------------------------

    @property
    def _ws_dir(self) -> Path:
        root = mushin_root(self.project_dir)
        return _ensure_subdir(root, WORKSPACES_DIR, self.id)

    @property
    def _objects_dir(self) -> Path:
        root = mushin_root(self.project_dir)
        return _ensure_subdir(root, OBJECTS_DIR, self.id)

    # -- save / export --------------------------------------------------------

    def save(self) -> None:
        """Persist the workspace (meta + journal + objects) to disk."""
        self.meta.saved_at = ts_now()
        # Save metadata
        meta_path = self._ws_dir / "meta.json"
        atomic_write_json(meta_path, self.meta.to_dict())
        # Save journal
        self.journal.save()
        # Save cached objects
        for key, obj in self._objects_cache.items():
            self._save_object_to_disk(key, obj)

    # -- object cache ---------------------------------------------------------

    def save_object(self, key: str, obj: Any) -> None:
        """Serialize and store a Python object under *key*."""
        self._objects_cache[key] = obj
        try:
            pickle.dumps(obj)
        except (pickle.PicklingError, TypeError, AttributeError):
            # Replace cache entry with placeholder so loads return it too
            self._objects_cache[key] = {"__mushin_unpicklable__": True, "repr": repr(obj)}
        self._save_object_to_disk(key, obj)

    def _save_object_to_disk(self, key: str, obj: Any) -> None:
        """Write one pickled object to the objects directory."""
        path = self._objects_dir / f"{key}.pkl"
        try:
            data = pickle.dumps(obj)
            atomic_write_bytes(path, data)
        except (pickle.PicklingError, TypeError, AttributeError):
            # Not everything is picklable — store a placeholder
            placeholder = pickle.dumps(
                {"__mushin_unpicklable__": True, "repr": repr(obj)}
            )
            atomic_write_bytes(path, placeholder)

    def load_object(self, key: str) -> Any:
        """Load a previously saved object by *key*."""
        if key in self._objects_cache:
            return self._objects_cache[key]
        path = self._objects_dir / f"{key}.pkl"
        data = read_bytes(path)
        if data is None:
            raise KeyError(f"No object found with key '{key}'")
        obj = pickle.loads(data)
        self._objects_cache[key] = obj
        return obj

    def list_objects(self) -> list[str]:
        """Return the keys of all saved objects."""
        if not self._objects_dir.exists():
            return []
        return sorted(p.stem for p in self._objects_dir.glob("*.pkl"))

    def delete_object(self, key: str) -> None:
        """Remove a stored object."""
        path = self._objects_dir / f"{key}.pkl"
        if path.exists():
            path.unlink()
        self._objects_cache.pop(key, None)

    # -- active workspace tracking --------------------------------------------

    def set_active(self) -> None:
        """Mark this workspace as the currently active one."""
        root = mushin_root(self.project_dir)
        atomic_write_json(root / ACTIVE_FILE, {"workspace_id": self.id})

    # -- dunder ---------------------------------------------------------------

    def __repr__(self) -> str:
        name = self.meta.name or self.id[:8]
        return f"Workspace(id={self.id!r}, name={name!r})"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_id() -> str:
    """Generate a short unique identifier using stdlib only."""
    import random
    import string

    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d%H%M%S")
    rand_part = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{date_part}-{rand_part}"


def get_active_workspace_id(project_dir: str | Path) -> str | None:
    """Return the ID of the currently active workspace, or ``None``."""
    root = mushin_root(project_dir)
    data = read_json(root / ACTIVE_FILE)
    if data and "workspace_id" in data:
        return data["workspace_id"]
    return None


def list_workspaces(project_dir: str | Path) -> list[WorkspaceMeta]:
    """Return metadata for all saved workspaces."""
    root = mushin_root(project_dir)
    ws_dir = root / WORKSPACES_DIR
    if not ws_dir.exists():
        return []
    result: list[WorkspaceMeta] = []
    for child in sorted(ws_dir.iterdir()):
        meta_path = child / "meta.json"
        data = read_json(meta_path)
        if data:
            result.append(WorkspaceMeta.from_dict(data))
    return result


def delete_workspace(project_dir: str | Path, workspace_id: str) -> bool:
    """Delete a workspace and all its data.  Returns ``True`` if deleted."""
    import shutil

    root = mushin_root(project_dir)
    ws_path = root / WORKSPACES_DIR / workspace_id
    if ws_path.exists():
        shutil.rmtree(ws_path)
    # Also remove journal and objects
    for sub in [JOURNALS_DIR, OBJECTS_DIR]:
        p = root / sub / f"{workspace_id}.json" if sub == JOURNALS_DIR else root / sub / workspace_id
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    return True


# Need this import at the bottom to avoid circular reference issues
from ussy_mushin.storage import JOURNALS_DIR  # noqa: E402
