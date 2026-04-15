"""Core Snapshot operations — save, load, new, list, peek, tag, diff."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional

from .context import capture_mental_context, format_context_display
from .editor import capture_editor_state
from .environment import capture_environment
from .models import Snapshot, SnapshotMetadata
from .process import capture_processes
from .storage import (
    delete_snapshot,
    get_snapshot_size,
    list_snapshots,
    load_snapshot,
    save_snapshot,
    snapshot_exists,
)
from .terminal import capture_terminals


def save(
    name: str,
    note: str = "",
    project_dir: str = "",
    include_secrets: bool = False,
) -> Snapshot:
    """Save the current development state as a named snapshot.
    
    Args:
        name: Name for the snapshot.
        note: Optional mental context note.
        project_dir: Project directory for context capture.
        include_secrets: Include secret env vars.
    
    Returns:
        The saved Snapshot object.
    """
    if not project_dir:
        project_dir = os.getcwd()

    # Capture all state dimensions
    terminals = capture_terminals()
    editor = capture_editor_state(project_dir)
    processes = capture_processes()
    environment = capture_environment(project_dir, include_secrets)
    mental_ctx = capture_mental_context(note, project_dir)

    # Build snapshot
    snapshot = Snapshot(
        name=name,
        metadata=SnapshotMetadata(
            name=name,
            created_at=datetime.now(timezone.utc).isoformat(),
            tags=[],
            terminal_count=len(terminals),
            file_count=len(editor.open_files),
            process_count=len(processes),
            note_preview=note[:80] if note else "",
        ),
        terminals=terminals,
        editor=editor,
        processes=processes,
        environment=environment,
        mental_context=mental_ctx,
    )

    save_snapshot(snapshot)
    return snapshot


def load(name: str, dry_run: bool = False) -> Optional[Snapshot]:
    """Load a previously saved snapshot.
    
    Restores environment, displays mental context, and provides
    instructions for restoring terminals, editor, and processes.
    
    Args:
        name: Name of the snapshot to load.
        dry_run: If True, only show what would be restored.
    
    Returns:
        The loaded Snapshot, or None if not found.
    """
    snapshot = load_snapshot(name)
    if snapshot is None:
        return None

    if not dry_run:
        # Restore environment
        from .environment import restore_environment
        restore_environment(snapshot.environment)

    # Always display mental context
    print(format_context_display(snapshot.mental_context))

    # Provide restore instructions
    if not dry_run:
        _print_restore_instructions(snapshot)

    return snapshot


def new(name: str, project_dir: str = "") -> Snapshot:
    """Create a clean snapshot (minimal state) for starting fresh.
    
    Args:
        name: Name for the new snapshot.
        project_dir: Project directory.
    
    Returns:
        The new minimal Snapshot.
    """
    if not project_dir:
        project_dir = os.getcwd()

    snapshot = Snapshot(
        name=name,
        metadata=SnapshotMetadata(
            name=name,
            created_at=datetime.now(timezone.utc).isoformat(),
        ),
        mental_context=capture_mental_context(
            note="Clean environment",
            project_dir=project_dir,
        ),
    )
    save_snapshot(snapshot)
    return snapshot


def peek(name: str) -> Optional[dict]:
    """Show what's in a snapshot without loading it.
    
    Returns a summary dict of the snapshot contents.
    """
    snapshot = load_snapshot(name)
    if snapshot is None:
        return None

    return {
        "name": snapshot.name,
        "created_at": snapshot.metadata.created_at,
        "tags": snapshot.metadata.tags,
        "terminals": [
            {
                "session_id": t.session_id,
                "working_directory": t.working_directory,
                "foreground_command": t.foreground_command,
            }
            for t in snapshot.terminals
        ],
        "open_files": [
            {
                "path": f.path,
                "cursor": f"{f.cursor.line}:{f.cursor.column}",
                "modified": f.is_modified,
            }
            for f in snapshot.editor.open_files
        ],
        "processes": [
            {
                "command": p.startup_command,
                "auto_restart": p.auto_restart,
            }
            for p in snapshot.processes
        ],
        "env_var_count": len(snapshot.environment.variables),
        "env_files": snapshot.environment.env_files,
        "note": snapshot.mental_context.note,
        "auto_suggestion": snapshot.mental_context.auto_suggestion,
        "git_branch": snapshot.mental_context.git_branch,
        "git_status": snapshot.mental_context.git_status_summary,
        "size_bytes": snapshot.metadata.size_bytes,
    }


def tag(name: str, tag_value: str) -> bool:
    """Add a tag to a snapshot for long-term retention.
    
    Args:
        name: Snapshot name.
        tag_value: Tag to add.
    
    Returns:
        True if the tag was added successfully.
    """
    snapshot = load_snapshot(name)
    if snapshot is None:
        return False

    if tag_value not in snapshot.metadata.tags:
        snapshot.metadata.tags.append(tag_value)
        save_snapshot(snapshot)
    return True


def untag(name: str, tag_value: str) -> bool:
    """Remove a tag from a snapshot.
    
    Args:
        name: Snapshot name.
        tag_value: Tag to remove.
    
    Returns:
        True if the tag was removed successfully.
    """
    snapshot = load_snapshot(name)
    if snapshot is None:
        return False

    if tag_value in snapshot.metadata.tags:
        snapshot.metadata.tags.remove(tag_value)
        save_snapshot(snapshot)
    return True


def format_snapshot_list(snapshots: List[SnapshotMetadata], verbose: bool = False) -> str:
    """Format a list of snapshots for display."""
    if not snapshots:
        return "No snapshots found."

    lines = []
    for snap in snapshots:
        age = _format_age(snap.created_at)
        summary = f"{snap.terminal_count} terms, {snap.file_count} files, {snap.process_count} procs"
        tags_str = f" [{', '.join(snap.tags)}]" if snap.tags else ""
        note_str = f' — "{snap.note_preview}"' if snap.note_preview else ""
        lines.append(f"  {snap.name:<30} {age:<12} {summary}{tags_str}{note_str}")

        if verbose:
            lines.append(f"    Created: {snap.created_at}")
            lines.append(f"    Size: {_human_size(snap.size_bytes)}")

    return "\n".join(lines)


def _print_restore_instructions(snapshot: Snapshot) -> None:
    """Print instructions for manually restoring parts of the snapshot."""
    if snapshot.terminals:
        print(f"\n📱 Terminals to restore: {len(snapshot.terminals)}")
        for t in snapshot.terminals:
            if t.working_directory:
                print(f"  cd {t.working_directory}")
            if t.foreground_command:
                print(f"  Run: {t.foreground_command}")

    if snapshot.editor.open_files:
        print(f"\n📝 Files to open: {len(snapshot.editor.open_files)}")
        for f in snapshot.editor.open_files[:10]:
            cursor = f" (line {f.cursor.line})" if f.cursor.line > 1 else ""
            print(f"  {f.path}{cursor}")
        if len(snapshot.editor.open_files) > 10:
            print(f"  ... and {len(snapshot.editor.open_files) - 10} more")

    if snapshot.processes:
        auto_restart = [p for p in snapshot.processes if p.auto_restart]
        if auto_restart:
            print(f"\n⚙️  Processes to restart: {len(auto_restart)}")
            for p in auto_restart:
                print(f"  {p.startup_command}")


def _format_age(created_at: str) -> str:
    """Format a timestamp as a human-readable age string."""
    try:
        created = datetime.fromisoformat(created_at)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - created

        if delta.days > 365:
            return f"{delta.days // 365}y ago"
        elif delta.days > 30:
            return f"{delta.days // 30}mo ago"
        elif delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600}h ago"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60}m ago"
        else:
            return "just now"
    except (ValueError, TypeError):
        return created_at


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
