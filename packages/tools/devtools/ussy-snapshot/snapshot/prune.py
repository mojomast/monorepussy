"""Snapshot pruning — delete old or excess snapshots."""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from .storage import list_snapshots, delete_snapshot, load_metadata, SnapshotMetadata


def parse_duration(duration_str: str) -> timedelta:
    """Parse a duration string like '7d', '2h', '30m' into a timedelta.
    
    Supported suffixes: d (days), h (hours), m (minutes), w (weeks)
    """
    match = re.match(r'^(\d+)([dhmw])$', duration_str.lower())
    if not match:
        raise ValueError(f"Invalid duration format: '{duration_str}'. Use e.g. '7d', '2h', '30m', '1w'")
    
    amount = int(match.group(1))
    unit = match.group(2)
    
    if unit == "d":
        return timedelta(days=amount)
    elif unit == "h":
        return timedelta(hours=amount)
    elif unit == "m":
        return timedelta(minutes=amount)
    elif unit == "w":
        return timedelta(weeks=amount)
    else:
        raise ValueError(f"Unknown duration unit: '{unit}'")


def prune_snapshots(
    older_than: str = "",
    keep_last: int = 0,
    exclude_tags: Optional[List[str]] = None,
    dry_run: bool = False,
) -> List[str]:
    """Prune snapshots based on criteria.
    
    Args:
        older_than: Delete snapshots older than this duration (e.g. '7d').
        keep_last: Keep at least this many recent snapshots.
        exclude_tags: Don't delete snapshots with any of these tags.
        dry_run: If True, only report what would be deleted.
    
    Returns:
        List of snapshot names that were (or would be) deleted.
    """
    snapshots = list_snapshots(sort="age")  # newest first
    if not snapshots:
        return []

    # Determine cutoff time
    cutoff = None
    if older_than:
        delta = parse_duration(older_than)
        cutoff = datetime.now(timezone.utc) - delta

    # Protected names (keep these)
    protected = set()
    if keep_last > 0:
        for snap in snapshots[:keep_last]:
            protected.add(snap.name)

    # Protect tagged snapshots
    if exclude_tags:
        for snap in snapshots:
            if any(tag in snap.tags for tag in exclude_tags):
                protected.add(snap.name)

    to_delete = []
    for snap in snapshots:
        if snap.name in protected:
            continue

        # Check age
        if cutoff:
            try:
                created = datetime.fromisoformat(snap.created_at)
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if created >= cutoff:
                    continue  # Not old enough
            except (ValueError, TypeError):
                continue  # Can't parse date, skip

        to_delete.append(snap.name)

    # Delete
    if not dry_run:
        for name in to_delete:
            delete_snapshot(name)

    return to_delete


def get_storage_usage() -> dict:
    """Get storage usage statistics for snapshots.
    
    Returns a dict with total_size, count, and per-snapshot sizes.
    """
    snapshots = list_snapshots()
    total = sum(s.size_bytes for s in snapshots)
    return {
        "count": len(snapshots),
        "total_size_bytes": total,
        "total_size_human": _human_size(total),
        "snapshots": [
            {"name": s.name, "size_bytes": s.size_bytes, "size_human": _human_size(s.size_bytes)}
            for s in snapshots
        ],
    }


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
