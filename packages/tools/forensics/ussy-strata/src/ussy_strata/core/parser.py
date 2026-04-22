"""Parser — convert git log output into stratigraphic model objects.

Uses subprocess to run git commands and parse their output into
Stratum, Intrusion, and related data structures.
"""

from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime
from typing import List, Optional, Tuple

from ussy_strata.core import (
    Intrusion,
    IntrusionType,
    Stratum,
)


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


def is_git_repo(path: str) -> bool:
    """Check if the given path is inside a git repository."""
    try:
        _run_git(["rev-parse", "--git-dir"], cwd=path)
        return True
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def parse_commits(repo_path: str, max_count: int = 0) -> List[Stratum]:
    """Parse git log into a list of Stratum objects.

    Args:
        repo_path: Path to the git repository.
        max_count: Maximum number of commits to parse (0 = all).

    Returns:
        List of Stratum objects, ordered newest-first.
    """
    # Format: hash|author|date_iso|message|parent_hashes|numstat
    log_format = "%H|%an|%aI|%s|%P"
    args = [
        "log",
        f"--format={log_format}",
        "--numstat",
    ]
    if max_count > 0:
        args.append(f"--max-count={max_count}")

    output = _run_git(args, cwd=repo_path)

    return _parse_log_output(output)


def _parse_log_output(output: str) -> List[Stratum]:
    """Parse the combined git log + numstat output into Stratum objects."""
    strata: List[Stratum] = []
    lines = output.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Try to parse a header line (hash|author|date|msg|parents)
        parts = line.split("|")
        if len(parts) >= 5:
            commit_hash = parts[0].strip()
            author = parts[1].strip()
            date_str = parts[2].strip()
            message = parts[3].strip()
            parent_hashes = parts[4].strip().split() if parts[4].strip() else []

            try:
                date = datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                date = datetime.now()

            # Parse following numstat lines
            files_changed: List[str] = []
            lines_added = 0
            lines_deleted = 0

            i += 1
            while i < len(lines):
                stat_line = lines[i].strip()
                if not stat_line:
                    i += 1
                    continue
                # numstat lines: added deleted filepath
                stat_match = re.match(
                    r'^(\d+|-)\s+(\d+|-)\s+(.+)$', stat_line
                )
                if stat_match:
                    add_str = stat_match.group(1)
                    del_str = stat_match.group(2)
                    filepath = stat_match.group(3).strip()
                    # Binary files show as '-'
                    if add_str != "-":
                        lines_added += int(add_str)
                    if del_str != "-":
                        lines_deleted += int(del_str)
                    # Handle rename format: old => new
                    if "=>" in filepath:
                        # e.g. "{old_dir => new_dir}/file.py"
                        filepath = filepath.split("=>")[-1].strip()
                        filepath = filepath.strip("} ")
                    files_changed.append(filepath)
                    i += 1
                else:
                    break

            stratum = Stratum(
                commit_hash=commit_hash,
                author=author,
                date=date,
                message=message,
                parent_hashes=parent_hashes,
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                files_changed=files_changed,
            )
            strata.append(stratum)
        else:
            i += 1

    return strata


def classify_intrusions(strata: List[Stratum]) -> List[Intrusion]:
    """Identify and classify branch intrusions from the strata.

    A branch intrusion is a group of commits on a non-default branch.
    Igneous intrusions are fast (high commits/hour); sedimentary are slow.
    """
    if not strata:
        return []

    # Group strata by branch
    branch_groups: dict[str, List[Stratum]] = {}
    for s in strata:
        branch = s.branch_name or "main"
        branch_groups.setdefault(branch, []).append(s)

    intrusions: List[Intrusion] = []
    for branch, branch_strata in branch_groups.items():
        if not branch_strata:
            continue

        dates = [s.date for s in branch_strata if s.date]
        start_date = min(dates) if dates else None
        end_date = max(dates) if dates else None

        intrusion = Intrusion(
            branch_name=branch,
            start_date=start_date,
            end_date=end_date,
            commit_count=len(branch_strata),
            strata=branch_strata,
        )

        # Classify: >2 commits/hour = igneous, else sedimentary
        if intrusion.commits_per_hour > 2.0:
            intrusion.intrusion_type = IntrusionType.IGNEOUS
        else:
            intrusion.intrusion_type = IntrusionType.SEDIMENTARY

        intrusions.append(intrusion)

    return intrusions


def assign_branch_names(strata: List[Stratum], repo_path: str) -> List[Stratum]:
    """Attempt to assign branch names to strata using git branch --contains."""
    if not strata:
        return strata

    try:
        # Get all branch names with their tip commits
        branch_output = _run_git(
            ["for-each-ref", "--format=%(objectname) %(refname:short)", "refs/heads/"],
            cwd=repo_path,
        )
        branch_tips: dict[str, str] = {}
        for bline in branch_output.strip().split("\n"):
            if not bline.strip():
                continue
            parts = bline.strip().split(" ", 1)
            if len(parts) == 2:
                branch_tips[parts[0]] = parts[1]

        # Map each commit to a branch name
        hash_to_branch: dict[str, str] = {}
        for s in strata:
            if s.commit_hash in branch_tips:
                hash_to_branch[s.commit_hash] = branch_tips[s.commit_hash]

        # For merge commits, try to identify the merged branch
        for s in strata:
            if s.is_merge and len(s.parent_hashes) >= 2:
                # The second parent is typically the branch being merged
                try:
                    merged_branches = _run_git(
                        ["branch", "--contains", s.parent_hashes[1], "--format=%(refname:short)"],
                        cwd=repo_path,
                    ).strip().split("\n")
                    for b in merged_branches:
                        b = b.strip()
                        if b and b != "main" and b != "master":
                            hash_to_branch[s.commit_hash] = b
                            break
                except RuntimeError:
                    pass

        for s in strata:
            if s.commit_hash in hash_to_branch:
                s.branch_name = hash_to_branch[s.commit_hash]
    except RuntimeError:
        pass

    return strata


def compute_stability(strata: List[Stratum]) -> List[Stratum]:
    """Compute stability tier for each stratum based on surrounding context.

    Assigns stability_tier based on the commit's position in time and
    the density of surrounding changes.
    """
    if not strata:
        return strata

    # Sort by date for analysis
    sorted_strata = sorted(strata, key=lambda s: s.date)

    for i, s in enumerate(sorted_strata):
        # Look at a window of nearby commits
        window = sorted_strata[max(0, i - 5):i + 6]
        avg_density = sum(w.density for w in window) / max(len(window), 1)

        # Age factor
        from datetime import datetime as dt, timezone
        age_hours = (dt.now(timezone.utc) - s.date).total_seconds() / 3600.0

        if age_hours < 24 and avg_density > 5:
            tier = "volatile"
        elif age_hours < 168:  # <1 week
            tier = "active"
        elif age_hours < 720:  # <1 month
            tier = "settling"
        elif age_hours < 4320:  # <6 months
            tier = "mature"
        else:
            tier = "bedrock"

        s.stability_tier = tier

    return sorted_strata
