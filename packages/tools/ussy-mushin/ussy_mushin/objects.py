"""Live object cache — serialize and restore Python runtime objects.

Provides a thin wrapper around ``pickle`` for saving and loading Python
objects within a workspace.  For objects that cannot be pickled, a
placeholder with ``repr()`` is stored instead.
"""

from __future__ import annotations

import pickle
from typing import Any

from ussy_mushin.storage import OBJECTS_DIR, _ensure_subdir, atomic_write_bytes, mushin_root, read_bytes


class ObjectCache:
    """A key-value object store backed by pickle files.

    Each workspace gets its own subdirectory under
    ``.mushin/objects/<workspace_id>/``.
    """

    def __init__(self, project_dir: str | Path, workspace_id: str) -> None:
        from pathlib import Path

        self.project_dir = Path(project_dir)
        self.workspace_id = workspace_id

    @property
    def _dir(self) -> Any:
        root = mushin_root(self.project_dir)
        return _ensure_subdir(root, OBJECTS_DIR, self.workspace_id)

    def put(self, key: str, obj: Any) -> None:
        """Store *obj* under *key*."""
        path = self._dir / f"{key}.pkl"
        try:
            data = pickle.dumps(obj)
        except (pickle.PicklingError, TypeError, AttributeError):
            data = pickle.dumps({"__mushin_unpicklable__": True, "repr": repr(obj)})
        atomic_write_bytes(path, data)

    def get(self, key: str) -> Any:
        """Retrieve the object stored under *key*."""
        path = self._dir / f"{key}.pkl"
        data = read_bytes(path)
        if data is None:
            raise KeyError(f"No object with key '{key}'")
        return pickle.loads(data)

    def has(self, key: str) -> bool:
        """Check if *key* exists in the cache."""
        path = self._dir / f"{key}.pkl"
        return path.exists()

    def keys(self) -> list[str]:
        """Return all stored keys."""
        d = self._dir
        if not d.exists():
            return []
        return sorted(p.stem for p in d.glob("*.pkl"))

    def delete(self, key: str) -> bool:
        """Delete the object under *key*.  Returns ``True`` if it existed."""
        path = self._dir / f"{key}.pkl"
        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self) -> int:
        """Remove all objects.  Returns the count of deleted objects."""
        count = 0
        for p in list(self._dir.glob("*.pkl")):
            p.unlink()
            count += 1
        return count
