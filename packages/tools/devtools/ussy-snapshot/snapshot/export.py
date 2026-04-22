"""Snapshot export and import — sharing development state."""

from __future__ import annotations

import io
import json
import os
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import Snapshot
from .storage import load_snapshot, save_snapshot, snapshot_exists


def export_snapshot(
    name: str,
    output_path: str = "",
    include_secrets: bool = False,
) -> str:
    """Export a snapshot to a portable tar.gz archive.
    
    The archive contains:
    - snapshot.json: Full snapshot data (secrets sanitized unless --include-secrets)
    - metadata.json: Snapshot metadata
    - env_restore.sh: Shell script to restore environment variables
    - README.txt: Instructions for importing
    
    Args:
        name: Snapshot name to export.
        output_path: Output file path. Defaults to <name>.tar.gz in current dir.
        include_secrets: If True, include secret env vars in the export.
    
    Returns:
        The path to the created archive.
    """
    snapshot = load_snapshot(name)
    if snapshot is None:
        raise ValueError(f"Snapshot '{name}' not found")

    if not output_path:
        output_path = f"{name}.tar.gz"

    # Sanitize secrets if needed
    if not include_secrets:
        snapshot = _sanitize_secrets(snapshot)

    # Create the archive
    with tarfile.open(output_path, "w:gz") as tar:
        # Add snapshot data
        _add_text_to_tar(tar, "snapshot.json", snapshot.to_json())
        _add_text_to_tar(tar, "metadata.json", json.dumps(snapshot.metadata.__dict__, indent=2, default=str))
        
        # Generate and add env restore script
        from .environment import generate_env_export_script
        env_script = generate_env_export_script(snapshot.environment)
        _add_text_to_tar(tar, "env_restore.sh", env_script)
        
        # Add README
        readme = _generate_export_readme(name, snapshot)
        _add_text_to_tar(tar, "README.txt", readme)

    return output_path


def import_snapshot(
    archive_path: str,
    new_name: str = "",
) -> str:
    """Import a snapshot from a portable tar.gz archive.
    
    Args:
        archive_path: Path to the tar.gz archive.
        new_name: Optional new name for the imported snapshot.
    
    Returns:
        The name of the imported snapshot.
    """
    if not os.path.exists(archive_path):
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    with tarfile.open(archive_path, "r:gz") as tar:
        # Extract snapshot.json
        snapshot_member = None
        for member in tar.getmembers():
            if member.name.endswith("snapshot.json"):
                snapshot_member = member
                break

        if snapshot_member is None:
            raise ValueError("Archive does not contain snapshot.json")

        f = tar.extractfile(snapshot_member)
        if f is None:
            raise ValueError("Could not read snapshot.json from archive")
        
        data = json.loads(f.read().decode("utf-8"))
        snapshot = Snapshot.from_dict(data)

    # Rename if requested
    if new_name:
        snapshot.name = new_name
        snapshot.metadata.name = new_name

    if not snapshot.name:
        raise ValueError("Snapshot has no name")

    # Save the imported snapshot
    save_snapshot(snapshot)
    return snapshot.name


def _sanitize_secrets(snapshot: Snapshot) -> Snapshot:
    """Remove secret environment variables from a snapshot."""
    from .environment import _is_secret
    
    sanitized_vars = {
        k: v for k, v in snapshot.environment.variables.items()
        if not _is_secret(k)
    }
    snapshot.environment.variables = sanitized_vars
    return snapshot


def _add_text_to_tar(tar: tarfile.TarFile, name: str, content: str) -> None:
    """Add a text string as a file to a tar archive."""
    data = content.encode("utf-8")
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    info.mtime = datetime.now(timezone.utc).timestamp()
    tar.addfile(info, io.BytesIO(data))


def _generate_export_readme(name: str, snapshot: Snapshot) -> str:
    """Generate a README for the exported snapshot archive."""
    lines = [
        f"Snapshot Export: {name}",
        "=" * 40,
        "",
        f"Created: {snapshot.metadata.created_at}",
        f"Terminals: {len(snapshot.terminals)}",
        f"Open files: {len(snapshot.editor.open_files)}",
        f"Processes: {len(snapshot.processes)}",
        "",
        "To import this snapshot:",
        "  snapshot import <path_to_this_file.tar.gz>",
        "",
        "To restore environment variables:",
        "  source env_restore.sh",
        "",
    ]
    if snapshot.mental_context.note:
        lines.append(f"Context note: {snapshot.mental_context.note}")
        lines.append("")

    return "\n".join(lines)
