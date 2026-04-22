"""Archaeology module — reconstructs fracture history of a file from git and joints."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from .joint import Joint, JointStore


@dataclass
class FractureEvent:
    """A single fracture event in a file's history."""

    timestamp: str = ""
    bug_ref: str = ""
    severity: str = ""
    break_description: str = ""
    repair_description: str = ""
    removal_impact: str = ""
    status: str = ""
    joint_id: str = ""


@dataclass
class ArchaeologyReport:
    """Full archaeology report for a file."""

    file: str = ""
    fractures: List[FractureEvent] = field(default_factory=list)
    total_months: int = 0
    pattern: str = ""
    suggestion: str = ""


def get_git_log_for_file(file_path: str, root: Optional[str] = None) -> List[dict]:
    """Get git log entries for a specific file.

    Returns:
        List of dicts with keys: hash, author, date, subject.
    """
    root = root or os.getcwd()
    cmd = [
        "git", "log", "--follow",
        '--format=%H|%an|%aI|%s',
        "--", file_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []

        entries = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                entries.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "subject": parts[3],
                })
        return entries
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def build_archaeology_report(
    file_path: str,
    root: Optional[str] = None,
) -> ArchaeologyReport:
    """Build an archaeology report for a file.

    Combines joint data with git history to reconstruct the fracture timeline.
    """
    store = JointStore(root)
    joints = store.find_by_file(file_path)

    report = ArchaeologyReport(file=file_path)

    if not joints:
        return report

    # Build fracture events from joints
    for j in sorted(joints, key=lambda j: j.timestamp):
        event = FractureEvent(
            timestamp=j.timestamp,
            bug_ref=j.bug_ref,
            severity=j.severity,
            break_description=j.break_description,
            repair_description=j.repair_description,
            removal_impact=j.removal_impact,
            status=j.status,
            joint_id=j.id,
        )
        report.fractures.append(event)

    # Calculate timespan
    if len(report.fractures) >= 2:
        try:
            first = datetime.fromisoformat(report.fractures[0].timestamp)
            last = datetime.fromisoformat(report.fractures[-1].timestamp)
            delta_days = (last - first).days
            report.total_months = max(1, round(delta_days / 30))
        except (ValueError, TypeError):
            report.total_months = 0
    else:
        report.total_months = 0

    # Detect patterns
    report.pattern = detect_pattern(report.fractures)
    report.suggestion = generate_suggestion(report)

    return report


def detect_pattern(fractures: List[FractureEvent]) -> str:
    """Detect recurring patterns in fracture events."""
    if not fractures:
        return ""

    # Check for repeated severity
    critical_count = sum(1 for f in fractures if f.severity == "critical")
    if critical_count == len(fractures) and len(fractures) > 1:
        return "All fractures are critical — this file is a chronic failure point"

    # Check for repeated keywords in break descriptions
    words = {}
    for f in fractures:
        for w in f.break_description.lower().split():
            w = w.strip(".,;:()[]")
            if len(w) > 4:  # Skip short words
                words[w] = words.get(w, 0) + 1

    repeated = [w for w, c in words.items() if c >= 2]
    if repeated:
        return f"Repeated themes: {', '.join(repeated[:3])} — fractures cluster around these concepts"

    return f"{len(fractures)} distinct fractures, no obvious pattern"


def generate_suggestion(report: ArchaeologyReport) -> str:
    """Generate a refactoring suggestion based on the archaeology report."""
    if not report.fractures:
        return ""

    count = len(report.fractures)
    critical = sum(1 for f in report.fractures if f.severity == "critical")
    hollow = sum(1 for f in report.fractures if f.status == "hollow")

    suggestions = []

    if count >= 3:
        suggestions.append("High fracture count — consider splitting this file into smaller modules")

    if critical >= 2:
        suggestions.append("Multiple critical fractures — this module handles high-risk logic that needs extra protection")

    if hollow > 0:
        suggestions.append(f"{hollow} hollow joint{'s' if hollow != 1 else ''} — consider cleaning up redundant repairs")

    if not suggestions:
        return "No specific suggestions — the file's repair history looks healthy"

    return "; ".join(suggestions)


def format_archaeology_report(report: ArchaeologyReport) -> str:
    """Format an archaeology report as a human-readable string."""
    lines = []

    if report.total_months > 0:
        lines.append(f"{report.file} — {report.total_months} months of fractures")
    else:
        lines.append(f"{report.file} — fracture history")

    lines.append("")

    if not report.fractures:
        lines.append("  No golden joints found — this file is intact.")
        return "\n".join(lines)

    for f in report.fractures:
        # Format the timestamp
        try:
            dt = datetime.fromisoformat(f.timestamp)
            month_str = dt.strftime("%b %Y")
        except (ValueError, TypeError):
            month_str = f.timestamp[:10]

        severity_label = f.severity.upper() if f.severity else "UNKNOWN"
        status_label = f.status.upper().replace("_", " ") if f.status else "UNKNOWN"

        lines.append(f"  {month_str} ──⚡ CRACK: {f.break_description} ({f.bug_ref})")
        lines.append(f"              ⛩️ REPAIRED: {f.repair_description}")
        lines.append(f"              Status: {status_label}")
        lines.append("")

    if report.pattern:
        lines.append(f"  Pattern: {report.pattern}")
    if report.suggestion:
        lines.append(f"           → {report.suggestion}")

    return "\n".join(lines)
