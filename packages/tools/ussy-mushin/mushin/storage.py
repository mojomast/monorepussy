"""Low-level storage helpers — JSON persistence for workspace data.

All files live under a ``.mushin/`` directory at the root of the user's
project.  This module provides a thin abstraction for reading/writing
JSON and binary blobs with atomic writes.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MUSHIN_DIR = ".mushin"
WORKSPACES_DIR = "workspaces"
JOURNALS_DIR = "journals"
BOOKMARKS_DIR = "bookmarks"
OBJECTS_DIR = "objects"
BRANCHES_FILE = "branches.json"
ACTIVE_FILE = "active"


def mushin_root(project_dir: str | Path = ".") -> Path:
    """Return the ``.mushin`` directory for *project_dir*, creating it if needed."""
    root = Path(project_dir).resolve() / MUSHIN_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def _ensure_subdir(root: Path, *parts: str) -> Path:
    d = root.joinpath(*parts)
    d.mkdir(parents=True, exist_ok=True)
    return d


def atomic_write_json(path: Path, data: Any) -> None:
    """Write *data* as JSON to *path* atomically (write-to-temp + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, default=_json_default)
        # Atomic on POSIX when src and dst are on same filesystem
        shutil.move(tmp, str(path))
    except BaseException:
        # Clean up the temp file on any error
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_json(path: Path) -> Any:
    """Read JSON from *path*, returning ``None`` if the file does not exist."""
    if not path.exists():
        return None
    with open(path, "r") as f:
        return json.load(f)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write binary *data* to *path* atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        shutil.move(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_bytes(path: Path) -> bytes | None:
    """Read binary data from *path*, returning ``None`` if it does not exist."""
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return f.read()


def _json_default(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def ts_now() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def ts_parse(s: str) -> datetime:
    """Parse an ISO-8601 timestamp string into a *datetime*."""
    return datetime.fromisoformat(s)
