"""Snapshot storage — read/write snapshots to disk."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .models import Snapshot, SnapshotMetadata

# Default storage location
DEFAULT_STORAGE_DIR = os.path.expanduser("~/.local/share/snapshot")

# File names within a snapshot directory
METADATA_FILE = "metadata.json"
SNAPSHOT_FILE = "snapshot.json"


def get_storage_dir() -> Path:
    """Get the snapshot storage directory, creating it if needed."""
    # Allow override via environment variable
    storage = os.environ.get("SNAPSHOT_DIR", DEFAULT_STORAGE_DIR)
    path = Path(storage)
    path.mkdir(parents=True, exist_ok=True)
    return path


def snapshot_dir(name: str) -> Path:
    """Get the directory for a named snapshot."""
    return get_storage_dir() / name


def save_snapshot(snapshot: Snapshot) -> Path:
    """Save a complete snapshot to disk. Returns the snapshot directory path."""
    sdir = snapshot_dir(snapshot.name)
    sdir.mkdir(parents=True, exist_ok=True)

    # Update metadata timestamps and counts
    snapshot.metadata.name = snapshot.name
    snapshot.metadata.terminal_count = len(snapshot.terminals)
    snapshot.metadata.file_count = len(snapshot.editor.open_files) if snapshot.editor else 0
    snapshot.metadata.process_count = len(snapshot.processes)
    snapshot.metadata.note_preview = (
        snapshot.mental_context.note[:80] if snapshot.mental_context and snapshot.mental_context.note else ""
    )
    snapshot.metadata.size_bytes = len(snapshot.to_json().encode("utf-8"))

    # Save full snapshot
    snapshot_path = sdir / SNAPSHOT_FILE
    snapshot_path.write_text(snapshot.to_json(), encoding="utf-8")

    # Save metadata separately for fast listing
    meta_path = sdir / METADATA_FILE
    meta_path.write_text(json.dumps(snapshot.metadata.__dict__, indent=2, default=str), encoding="utf-8")

    return sdir


def load_snapshot(name: str) -> Optional[Snapshot]:
    """Load a snapshot by name. Returns None if not found."""
    sdir = snapshot_dir(name)
    snapshot_path = sdir / SNAPSHOT_FILE
    if not snapshot_path.exists():
        return None
    try:
        data = json.loads(snapshot_path.read_text(encoding="utf-8"))
        return Snapshot.from_dict(data)
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def load_metadata(name: str) -> Optional[SnapshotMetadata]:
    """Load only metadata for a snapshot (fast, no full parse)."""
    sdir = snapshot_dir(name)
    meta_path = sdir / METADATA_FILE
    if not meta_path.exists():
        return None
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return SnapshotMetadata(**data)
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def list_snapshots(sort: str = "age") -> List[SnapshotMetadata]:
    """List all snapshots with metadata.
    
    Args:
        sort: Sort order — 'age' (newest first), 'name', 'size'
    """
    storage = get_storage_dir()
    snapshots = []
    for entry in storage.iterdir():
        if entry.is_dir():
            meta = load_metadata(entry.name)
            if meta:
                snapshots.append(meta)
    
    if sort == "name":
        snapshots.sort(key=lambda m: m.name)
    elif sort == "size":
        snapshots.sort(key=lambda m: m.size_bytes, reverse=True)
    else:  # age — newest first
        snapshots.sort(key=lambda m: m.created_at, reverse=True)
    
    return snapshots


def delete_snapshot(name: str) -> bool:
    """Delete a snapshot by name. Returns True if deleted."""
    sdir = snapshot_dir(name)
    if sdir.exists() and sdir.is_dir():
        shutil.rmtree(sdir)
        return True
    return False


def snapshot_exists(name: str) -> bool:
    """Check if a snapshot exists."""
    return snapshot_dir(name).exists()


def get_snapshot_size(name: str) -> int:
    """Get total size of a snapshot in bytes."""
    sdir = snapshot_dir(name)
    if not sdir.exists():
        return 0
    total = 0
    for f in sdir.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total
