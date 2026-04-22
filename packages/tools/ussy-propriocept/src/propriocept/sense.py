"""Passive state sense — proprioception for the workspace."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def sense_processes() -> list[dict]:
    """Gather running processes with their CWD and command line.

    On Linux reads ``/proc`` directly; on macOS falls back to ``ps``.
    """
    processes: list[dict] = []
    if sys.platform.startswith("linux"):
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                cmdline_path = Path(f"/proc/{entry}/cmdline")
                cmdline = cmdline_path.read_text().replace("\0", " ")
                cwd = os.readlink(f"/proc/{entry}/cwd")
                processes.append({
                    "pid": int(entry),
                    "cmd": cmdline.strip()[:80],
                    "cwd": cwd,
                })
            except (PermissionError, FileNotFoundError, OSError):
                continue
    else:
        # macOS / BSD fallback — we at least get PID + command name
        result = subprocess.run(
            ["ps", "-eo", "pid,comm"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines()[1:]:
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                pid_str, comm = parts
                processes.append({
                    "pid": int(pid_str),
                    "cmd": comm,
                    "cwd": "",
                })
    return processes


def sense(schema: dict) -> dict:
    """Augment *schema* limbs with active PIDs anchored inside them."""
    procs = sense_processes()
    for limb in schema.get("limbs", []):
        limb_path = limb["path"]
        limb.setdefault("state", {})
        limb["state"]["active_pids"] = [
            p["pid"]
            for p in procs
            if p["cwd"].startswith(limb_path)
        ]
    return schema


def render_ascii(schema: dict) -> str:
    """Return an ASCII soma-map of the workspace."""
    lines = ["Soma Map", "=" * 40]
    for limb in schema.get("limbs", []):
        name = Path(limb["path"]).name
        ltype = limb["type"]
        state = limb.get("state", {})
        active = len(state.get("active_pids", []))
        dirty = state.get("dirty", False)
        head = state.get("head", "")
        status = []
        if active:
            status.append(f"active:{active}")
        if dirty:
            status.append("dirty")
        if not status:
            status.append("numb")
        lines.append(f"  {name:20s} [{ltype}] {' '.join(status)}")
        if head:
            lines.append(f"    └─ {head}")
    return "\n".join(lines)
