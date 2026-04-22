"""Carbon dating — enhanced blame that shows the full depositional history.

Like radiocarbon dating in geology, this module provides deep insight
into when and how a specific line of code was deposited in the
stratigraphic record.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from typing import List, Optional

from ussy_strata.core import Stratum


def _run_git(args: List[str], cwd: str) -> str:
    """Run a git command and return its stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def carbon_date(
    repo_path: str,
    file_path: str,
    line_number: int,
) -> dict:
    """Perform carbon dating on a specific line in a file.

    Enhanced blame that traces the full depositional history of a line:
    when it was first deposited, how it evolved, and its current state.

    Args:
        repo_path: Path to the git repository.
        file_path: Path to the file (relative to repo root).
        line_number: 1-indexed line number to date.

    Returns:
        Dictionary with depositional history information.
    """
    result = {
        "file": file_path,
        "line_number": line_number,
        "current_content": "",
        "deposited_commit": "",
        "deposited_date": None,
        "deposited_author": "",
        "age_days": 0.0,
        "stability": "unknown",
        "history": [],
    }

    # Get current content
    try:
        content = _run_git(
            ["show", f"HEAD:{file_path}"],
            cwd=repo_path,
        )
        lines = content.split("\n")
        if 0 < line_number <= len(lines):
            result["current_content"] = lines[line_number - 1]
    except RuntimeError:
        pass

    # Run git blame
    try:
        blame_output = _run_git(
            ["blame", "-L", f"{line_number},{line_number}", "--porcelain", file_path],
            cwd=repo_path,
        )
    except RuntimeError:
        return result

    # Parse blame output
    current_hash = ""
    for bline in blame_output.split("\n"):
        if bline.startswith("author "):
            result["deposited_author"] = bline[7:]
        elif bline.startswith("author-mail "):
            pass
        elif bline.startswith("author-time "):
            try:
                timestamp = int(bline[12:])
                result["deposited_date"] = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except (ValueError, OSError):
                pass
        elif bline.startswith("summary "):
            pass
        elif not bline.startswith("\t") and len(bline) >= 40:
            # First line of porcelain blame is the commit hash
            current_hash = bline[:40]
            result["deposited_commit"] = current_hash

    # Calculate age
    if result["deposited_date"]:
        result["age_days"] = (datetime.now(timezone.utc) - result["deposited_date"]).total_seconds() / 86400.0

    # Determine stability based on age
    if result["age_days"] > 365:
        result["stability"] = "bedrock"
    elif result["age_days"] > 180:
        result["stability"] = "mature"
    elif result["age_days"] > 30:
        result["stability"] = "settling"
    elif result["age_days"] > 7:
        result["stability"] = "active"
    else:
        result["stability"] = "volatile"

    # Get the full history of this line using git log -L
    result["history"] = _trace_line_history(repo_path, file_path, line_number)

    return result


def _trace_line_history(
    repo_path: str, file_path: str, line_number: int
) -> List[dict]:
    """Trace the full history of a line using git log -L.

    Returns a list of historical entries showing how the line evolved.
    """
    history: List[dict] = []

    try:
        # Use git log -L to trace line evolution
        output = _run_git(
            [
                "log",
                "-L",
                f"{line_number},{line_number}:{file_path}",
                "--format=%H|%aI|%an|%s",
                "--no-patch",
            ],
            cwd=repo_path,
        )
    except RuntimeError:
        return history

    for line in output.strip().split("\n"):
        if "|" in line and not line.startswith(" "):
            parts = line.split("|", 3)
            if len(parts) >= 4:
                try:
                    date = datetime.fromisoformat(parts[1].strip())
                except (ValueError, TypeError):
                    date = None

                history.append({
                    "commit": parts[0].strip(),
                    "date": date,
                    "author": parts[2].strip(),
                    "message": parts[3].strip(),
                })

    return history


def carbon_date_file(
    repo_path: str,
    file_path: str,
) -> List[dict]:
    """Carbon date an entire file — show depositional history for all lines.

    Returns a summary showing age distribution of lines in the file.
    """
    try:
        blame_output = _run_git(
            ["blame", "--porcelain", file_path],
            cwd=repo_path,
        )
    except RuntimeError:
        return []

    line_ages: List[dict] = []
    current_commit = ""
    current_author = ""
    current_date: Optional[datetime] = None

    for line in blame_output.split("\n"):
        if line.startswith("\t"):
            # This is the actual content line
            age_days = 0.0
            if current_date:
                age_days = (datetime.now(timezone.utc) - current_date).total_seconds() / 86400.0

            line_ages.append({
                "commit": current_commit,
                "author": current_author,
                "date": current_date,
                "age_days": age_days,
                "content": line[1:],
            })
        elif len(line) >= 40 and not line.startswith("author") and not line.startswith("summary"):
            current_commit = line[:40]
        elif line.startswith("author "):
            current_author = line[7:]
        elif line.startswith("author-time "):
            try:
                timestamp = int(line[12:])
                current_date = datetime.fromtimestamp(timestamp)
            except (ValueError, OSError):
                current_date = None

    return line_ages
