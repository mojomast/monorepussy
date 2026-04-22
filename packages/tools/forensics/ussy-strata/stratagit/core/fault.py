"""Fault line detection — find history rewrites and force pushes.

Fault lines are disruptions in the geological record caused by
force pushes, history rewrites, and other operations that alter
the commit chain.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from typing import List, Optional

from stratagit.core import FaultLine


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


def detect_faults(repo_path: str) -> List[FaultLine]:
    """Detect fault lines (history rewrites) in the repository.

    Examines the reflog for evidence of force pushes and other
    history-rewriting operations.

    Args:
        repo_path: Path to the git repository.

    Returns:
        List of FaultLine objects.
    """
    faults: List[FaultLine] = []

    # Check reflog for force pushes
    faults.extend(_detect_reflog_faults(repo_path))

    # Check for amended commits
    faults.extend(_detect_amended_commits(repo_path))

    # Sort by date
    faults.sort(
        key=lambda f: f.date or datetime.min,
        reverse=True,
    )

    return faults


def _detect_reflog_faults(repo_path: str) -> List[FaultLine]:
    """Detect force pushes from reflog entries."""
    faults: List[FaultLine] = []

    # Get all reflogs
    try:
        refs_output = _run_git(
            ["for-each-ref", "--format=%(refname)", "refs/heads/"],
            cwd=repo_path,
        )
    except RuntimeError:
        return faults

    for ref in refs_output.strip().split("\n"):
        if not ref.strip():
            continue
        ref = ref.strip()

        try:
            reflog_output = _run_git(
                ["reflog", "show", "--format=%H|%gd|%gs|%aI", ref],
                cwd=repo_path,
            )
        except RuntimeError:
            continue

        entries = reflog_output.strip().split("\n")
        prev_hash: Optional[str] = None

        for line in entries:
            if not line.strip():
                continue
            parts = line.split("|", 3)
            if len(parts) < 4:
                continue

            commit_hash = parts[0].strip()
            ref_desc = parts[1].strip()
            action = parts[2].strip()
            date_str = parts[3].strip()

            try:
                date = datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                date = None

            # Detect force push: non-fast-forward update
            if prev_hash and "moving from" in action.lower():
                # Extract old hash from action
                import re
                m = re.search(r"moving from ([\da-f]+)", action)
                if m:
                    old_hash = m.group(1)
                    # Check if the old hash is ancestor of new (fast-forward)
                    try:
                        is_ancestor = _run_git(
                            ["merge-base", "--is-ancestor", old_hash, commit_hash],
                            cwd=repo_path,
                        )
                        # If merge-base --is-ancestor succeeds, it's a fast-forward
                        # If it fails, it's a force push
                    except RuntimeError:
                        # Not a fast-forward = force push
                        faults.append(FaultLine(
                            ref_name=ref,
                            old_hash=old_hash,
                            new_hash=commit_hash,
                            date=date,
                            description=f"Force push on {ref}: {old_hash[:8]} → {commit_hash[:8]}",
                            severity=0.9,
                        ))

            prev_hash = commit_hash

    return faults


def _detect_amended_commits(repo_path: str) -> List[FaultLine]:
    """Detect amended commits from the reflog."""
    faults: List[FaultLine] = []

    try:
        reflog_output = _run_git(
            ["reflog", "--format=%H|%gs|%aI"],
            cwd=repo_path,
        )
    except RuntimeError:
        return faults

    for line in reflog_output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue

        commit_hash = parts[0].strip()
        action = parts[1].strip()
        date_str = parts[2].strip()

        if "amend" in action.lower() or "rebase" in action.lower():
            try:
                date = datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                date = None

            faults.append(FaultLine(
                ref_name="HEAD",
                old_hash="",
                new_hash=commit_hash,
                date=date,
                description=f"History rewrite: {action[:80]}",
                severity=0.5,
            ))

    return faults


def get_fault_before_after(
    repo_path: str, fault: FaultLine
) -> tuple[str, str]:
    """Get the before/after state for a fault line.

    Returns the commit messages of the old and new refs for comparison.
    """
    before = ""
    after = ""

    if fault.old_hash:
        try:
            before = _run_git(
                ["log", "--oneline", "-5", fault.old_hash],
                cwd=repo_path,
            )
        except RuntimeError:
            before = "(unavailable)"

    if fault.new_hash:
        try:
            after = _run_git(
                ["log", "--oneline", "-5", fault.new_hash],
                cwd=repo_path,
            )
        except RuntimeError:
            after = "(unavailable)"

    return before, after
