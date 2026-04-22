"""Unconformity detection — find gaps in git history.

Unconformities are periods where the geological record is incomplete.
In git terms, these are rebases, squash merges, cherry-picks, and
orphaned commits that break the continuous chain of history.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timedelta
from typing import List, Optional

from stratagit.core import Unconformity, UnconformityType


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


def detect_unconformities(
    repo_path: str,
    max_commits: int = 0,
) -> List[Unconformity]:
    """Detect all unconformities in the repository history.

    Looks for:
    - Squash merges (merge commits with message indicating squash)
    - Cherry-picks (commits with cherry-pick notation)
    - Rebases (sequences of commits with same author in short time)
    - Orphaned branches (commits with no parent in main history)
    - Force pushes (detected via reflog gaps)

    Args:
        repo_path: Path to the git repository.
        max_commits: Max commits to analyze (0 = all).

    Returns:
        List of Unconformity objects.
    """
    unconformities: List[Unconformity] = []

    unconformities.extend(_detect_squash_merges(repo_path, max_commits))
    unconformities.extend(_detect_cherry_picks(repo_path, max_commits))
    unconformities.extend(_detect_rebases(repo_path, max_commits))
    unconformities.extend(_detect_orphans(repo_path))
    unconformities.extend(_detect_force_pushes(repo_path))

    # Sort by date
    unconformities.sort(
        key=lambda u: u.date or datetime.min,
        reverse=True,
    )

    return unconformities


def _detect_squash_merges(repo_path: str, max_commits: int) -> List[Unconformity]:
    """Detect squash merges by looking for merge commits that are actually squashes."""
    unconformities: List[Unconformity] = []

    args = ["log", "--merges", "--format=%H|%aI|%s"]
    if max_commits > 0:
        args.append(f"--max-count={max_commits}")

    try:
        output = _run_git(args, cwd=repo_path)
    except RuntimeError:
        return unconformities

    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue

        commit_hash = parts[0].strip()
        date_str = parts[1].strip()
        message = parts[2].strip()

        try:
            date = datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            date = None

        # Check if this looks like a squash merge
        squash_indicators = [
            "squash",
            "Squash",
            "SQUASH",
            "merged in",
            "Merge pull request",
            "Merge branch",
        ]

        is_squash = any(ind in message for ind in squash_indicators)
        if is_squash:
            # Count parents - a real merge has 2+ parents
            try:
                parent_output = _run_git(
                    ["show", "-s", "--format=%P", commit_hash],
                    cwd=repo_path,
                )
                parent_count = len(parent_output.strip().split())
            except RuntimeError:
                parent_count = 1

            if parent_count <= 1:
                # Single-parent "merge" = squash
                unconformities.append(Unconformity(
                    unconformity_type=UnconformityType.SQUASH,
                    description=f"Squash merge: {message[:80]}",
                    commit_hash=commit_hash,
                    date=date,
                    confidence=0.9,
                ))

    return unconformities


def _detect_cherry_picks(repo_path: str, max_commits: int) -> List[Unconformity]:
    """Detect cherry-picked commits."""
    unconformities: List[Unconformity] = []

    args = ["log", "--format=%H|%aI|%s", "--grep=cherry picked"]
    if max_commits > 0:
        args.append(f"--max-count={max_commits}")

    try:
        output = _run_git(args, cwd=repo_path)
    except RuntimeError:
        return unconformities

    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue

        commit_hash = parts[0].strip()
        date_str = parts[1].strip()
        message = parts[2].strip()

        try:
            date = datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            date = None

        unconformities.append(Unconformity(
            unconformity_type=UnconformityType.CHERRY_PICK,
            description=f"Cherry-pick: {message[:80]}",
            commit_hash=commit_hash,
            date=date,
            confidence=0.95,
        ))

    return unconformities


def _detect_rebases(repo_path: str, max_commits: int) -> List[Unconformity]:
    """Detect potential rebases by looking for unusual commit patterns.

    Rebases create sequences of commits with the same author in very
    short time intervals, often with duplicated or modified messages.
    """
    unconformities: List[Unconformity] = []

    args = ["log", "--format=%H|%aI|%an|%s"]
    if max_commits > 0:
        args.append(f"--max-count={max_commits}")

    try:
        output = _run_git(args, cwd=repo_path)
    except RuntimeError:
        return unconformities

    commits: List[dict] = []
    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue

        try:
            date = datetime.fromisoformat(parts[1].strip())
        except (ValueError, TypeError):
            date = None

        commits.append({
            "hash": parts[0].strip(),
            "date": date,
            "author": parts[2].strip(),
            "message": parts[3].strip(),
        })

    # Look for rapid-fire commits by same author (possible rebase)
    for i in range(len(commits) - 1):
        curr = commits[i]
        next_c = commits[i + 1]

        if (
            curr["date"]
            and next_c["date"]
            and curr["author"] == next_c["author"]
        ):
            diff = (curr["date"] - next_c["date"]).total_seconds()
            # If multiple commits within 30 seconds by same author = likely rebase
            if diff < 30:
                unconformities.append(Unconformity(
                    unconformity_type=UnconformityType.REBASE,
                    description=f"Possible rebase: rapid commits by {curr['author']}",
                    commit_hash=curr["hash"],
                    date=curr["date"],
                    confidence=0.4,
                ))

    return unconformities


def _detect_orphans(repo_path: str) -> List[Unconformity]:
    """Detect orphaned commits (no parent in main history)."""
    unconformities: List[Unconformity] = []

    # Check for refs that might indicate orphaned history
    try:
        output = _run_git(
            ["fsck", "--unreachable", "--no-reflogs"],
            cwd=repo_path,
        )
    except RuntimeError:
        return unconformities

    for line in output.strip().split("\n"):
        if "unreachable commit" in line:
            parts = line.split()
            if len(parts) >= 3:
                commit_hash = parts[2]
                date = None
                try:
                    date = _get_commit_date(repo_path, commit_hash)
                except RuntimeError:
                    pass

                unconformities.append(Unconformity(
                    unconformity_type=UnconformityType.ORPHAN,
                    description=f"Orphaned commit: {commit_hash[:12]}",
                    commit_hash=commit_hash,
                    date=date,
                    confidence=0.7,
                ))

    return unconformities


def _detect_force_pushes(repo_path: str) -> List[Unconformity]:
    """Detect force pushes from the reflog."""
    unconformities: List[Unconformity] = []

    try:
        output = _run_git(
            ["reflog", "--format=%H|%gd|%gs|%aI"],
            cwd=repo_path,
        )
    except RuntimeError:
        return unconformities

    prev_hash: Optional[str] = None
    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue

        commit_hash = parts[0].strip()
        ref = parts[1].strip()
        action = parts[2].strip()
        date_str = parts[3].strip()

        # Look for "moving from" messages that indicate force push
        if "moving from" in action or "rewinding" in action:
            try:
                date = datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                date = None

            unconformities.append(Unconformity(
                unconformity_type=UnconformityType.FORCE_PUSH,
                description=f"Force push detected: {action[:80]}",
                commit_hash=commit_hash,
                date=date,
                confidence=0.6,
            ))

    return unconformities


def _get_commit_date(repo_path: str, commit_hash: str) -> Optional[datetime]:
    """Get the author date of a commit."""
    try:
        output = _run_git(
            ["show", "-s", "--format=%aI", commit_hash],
            cwd=repo_path,
        )
        return datetime.fromisoformat(output.strip())
    except (RuntimeError, ValueError):
        return None
