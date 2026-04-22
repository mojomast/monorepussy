"""Snapshot diffing — compare two development states."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from .models import Snapshot
from .storage import load_snapshot


def diff_snapshots(name1: str, name2: str) -> Dict[str, Any]:
    """Diff two snapshots and return the differences.
    
    Args:
        name1: Name of the first (earlier) snapshot.
        name2: Name of the second (later) snapshot.
    
    Returns:
        A dict with sections: terminals, editor, processes, environment, mental_context
        Each section contains added/removed/changed items.
    """
    snap1 = load_snapshot(name1)
    snap2 = load_snapshot(name2)

    if snap1 is None:
        return {"error": f"Snapshot '{name1}' not found"}
    if snap2 is None:
        return {"error": f"Snapshot '{name2}' not found"}

    return {
        "name1": name1,
        "name2": name2,
        "terminals": _diff_terminals(snap1, snap2),
        "editor": _diff_editor(snap1, snap2),
        "processes": _diff_processes(snap1, snap2),
        "environment": _diff_environment(snap1, snap2),
        "mental_context": _diff_mental_context(snap1, snap2),
    }


def _diff_terminals(snap1: Snapshot, snap2: Snapshot) -> Dict[str, Any]:
    """Diff terminal states between two snapshots."""
    ids1 = {t.session_id: t for t in snap1.terminals}
    ids2 = {t.session_id: t for t in snap2.terminals}

    added = [sid for sid in ids2 if sid not in ids1]
    removed = [sid for sid in ids1 if sid not in ids2]
    common = [sid for sid in ids1 if sid in ids2]

    changed = []
    for sid in common:
        t1, t2 = ids1[sid], ids2[sid]
        changes = []
        if t1.working_directory != t2.working_directory:
            changes.append(("working_directory", t1.working_directory, t2.working_directory))
        if t1.foreground_command != t2.foreground_command:
            changes.append(("foreground_command", t1.foreground_command, t2.foreground_command))
        if changes:
            changed.append({"session_id": sid, "changes": changes})

    return {"added": added, "removed": removed, "changed": changed}


def _diff_editor(snap1: Snapshot, snap2: Snapshot) -> Dict[str, Any]:
    """Diff editor states between two snapshots."""
    files1 = {f.path: f for f in snap1.editor.open_files}
    files2 = {f.path: f for f in snap2.editor.open_files}

    added = [p for p in files2 if p not in files1]
    removed = [p for p in files1 if p not in files2]
    common = [p for p in files1 if p in files2]

    changed = []
    for path in common:
        f1, f2 = files1[path], files2[path]
        changes = []
        if f1.cursor.line != f2.cursor.line or f1.cursor.column != f2.cursor.column:
            changes.append((
                "cursor",
                f"{f1.cursor.line}:{f1.cursor.column}",
                f"{f2.cursor.line}:{f2.cursor.column}",
            ))
        if f1.is_modified != f2.is_modified:
            changes.append(("modified", f1.is_modified, f2.is_modified))
        if changes:
            changed.append({"path": path, "changes": changes})

    return {"added": added, "removed": removed, "changed": changed}


def _diff_processes(snap1: Snapshot, snap2: Snapshot) -> Dict[str, Any]:
    """Diff process states between two snapshots."""
    cmds1 = {p.startup_command: p for p in snap1.processes}
    cmds2 = {p.startup_command: p for p in snap2.processes}

    added = [c for c in cmds2 if c not in cmds1]
    removed = [c for c in cmds1 if c not in cmds2]

    return {"added": added, "removed": removed}


def _diff_environment(snap1: Snapshot, snap2: Snapshot) -> Dict[str, Any]:
    """Diff environment states between two snapshots."""
    env1 = snap1.environment.variables
    env2 = snap2.environment.variables

    keys1 = set(env1.keys())
    keys2 = set(env2.keys())

    added = {k: env2[k] for k in keys2 - keys1}
    removed = {k: env1[k] for k in keys1 - keys2}
    changed = {}
    for k in keys1 & keys2:
        if env1[k] != env2[k]:
            changed[k] = {"from": env1[k], "to": env2[k]}

    return {"added": added, "removed": removed, "changed": changed}


def _diff_mental_context(snap1: Snapshot, snap2: Snapshot) -> Dict[str, Any]:
    """Diff mental context between two snapshots."""
    c1, c2 = snap1.mental_context, snap2.mental_context
    changes = {}
    if c1.note != c2.note:
        changes["note"] = {"from": c1.note, "to": c2.note}
    if c1.git_branch != c2.git_branch:
        changes["git_branch"] = {"from": c1.git_branch, "to": c2.git_branch}
    if c1.git_status_summary != c2.git_status_summary:
        changes["git_status_summary"] = {"from": c1.git_status_summary, "to": c2.git_status_summary}
    return changes


def format_diff(diff_result: Dict[str, Any]) -> str:
    """Format a diff result for display."""
    lines = []
    
    if "error" in diff_result:
        return f"Error: {diff_result['error']}"

    lines.append(f"Diff: {diff_result.get('name1', '?')} → {diff_result.get('name2', '?')}")
    lines.append("")

    # Terminals
    t = diff_result.get("terminals", {})
    if t.get("added") or t.get("removed") or t.get("changed"):
        lines.append("📱 Terminals:")
        for sid in t.get("added", []):
            lines.append(f"  + Session: {sid}")
        for sid in t.get("removed", []):
            lines.append(f"  - Session: {sid}")
        for c in t.get("changed", []):
            lines.append(f"  ~ Session: {c['session_id']}")
            for change in c.get("changes", []):
                lines.append(f"    {change[0]}: {change[1]} → {change[2]}")
        lines.append("")

    # Editor
    e = diff_result.get("editor", {})
    if e.get("added") or e.get("removed") or e.get("changed"):
        lines.append("📝 Editor:")
        for p in e.get("added", []):
            lines.append(f"  + File: {p}")
        for p in e.get("removed", []):
            lines.append(f"  - File: {p}")
        for c in e.get("changed", []):
            lines.append(f"  ~ File: {c['path']}")
            for change in c.get("changes", []):
                lines.append(f"    {change[0]}: {change[1]} → {change[2]}")
        lines.append("")

    # Processes
    p = diff_result.get("processes", {})
    if p.get("added") or p.get("removed"):
        lines.append("⚙️  Processes:")
        for cmd in p.get("added", []):
            lines.append(f"  + {cmd}")
        for cmd in p.get("removed", []):
            lines.append(f"  - {cmd}")
        lines.append("")

    # Environment
    env = diff_result.get("environment", {})
    if env.get("added") or env.get("removed") or env.get("changed"):
        lines.append("🌍 Environment:")
        for k, v in env.get("added", {}).items():
            lines.append(f"  + {k}={v}")
        for k, v in env.get("removed", {}).items():
            lines.append(f"  - {k}={v}")
        for k, v in env.get("changed", {}).items():
            lines.append(f"  ~ {k}: {v['from']} → {v['to']}")
        lines.append("")

    # Mental context
    mc = diff_result.get("mental_context", {})
    if mc:
        lines.append("🧠 Mental Context:")
        for k, v in mc.items():
            lines.append(f"  ~ {k}: {v['from']} → {v['to']}")
        lines.append("")

    if len(lines) <= 2:
        lines.append("No differences found.")

    return "\n".join(lines)
