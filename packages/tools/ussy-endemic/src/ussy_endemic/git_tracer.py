"""Git tracer — mine git history for transmission events.

Uses subprocess calls to git for stdlib-only compatibility.
"""

from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ussy_endemic.models import (
    TransmissionEvent,
    TransmissionTree,
    TransmissionVector,
)


class GitTracer:
    """Mine git history for pattern transmission events."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.abspath(repo_path)
        self._git_available = self._check_git()

    def _check_git(self) -> bool:
        """Check if git is available and repo exists."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True, text=True,
                cwd=self.repo_path, timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _run_git(self, args: list[str]) -> str:
        """Run a git command and return stdout."""
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True, text=True,
                cwd=self.repo_path, timeout=30,
            )
            return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""

    def get_log(self, since: Optional[str] = None, until: Optional[str] = None,
                pathspec: Optional[str] = None) -> list[dict]:
        """Get commit log entries.

        Returns list of dicts with keys: hash, author, email, date, subject, files.
        """
        if not self._git_available:
            return []

        args = ["log", "--format=%H|%ae|%aI|%s", "--name-only"]
        if since:
            args.append(f"--since={since}")
        if until:
            args.append(f"--until={until}")
        if pathspec:
            args.extend(["--", pathspec])

        output = self._run_git(args)
        if not output:
            return []

        commits = []
        current_commit = None

        for line in output.splitlines():
            if "|" in line and line.count("|") >= 3:
                parts = line.split("|", 3)
                if len(parts) >= 4:
                    current_commit = {
                        "hash": parts[0],
                        "email": parts[1],
                        "date": parts[2],
                        "subject": parts[3],
                        "files": [],
                    }
            elif line.strip() and current_commit is not None:
                current_commit["files"].append(line.strip())
            elif not line.strip() and current_commit is not None:
                if current_commit not in commits:
                    commits.append(current_commit)

        if current_commit and current_commit not in commits:
            commits.append(current_commit)

        return commits

    def get_file_at_commit(self, filepath: str, commit_hash: str) -> str:
        """Get file contents at a specific commit."""
        return self._run_git(["show", f"{commit_hash}:{filepath}"])

    def get_blame(self, filepath: str) -> list[dict]:
        """Get blame info for a file.

        Returns list of dicts with keys: commit, author, line.
        """
        if not self._git_available:
            return []

        output = self._run_git([
            "blame", "--porcelain", filepath,
        ])
        if not output:
            return []

        blames = []
        current = {}
        for line in output.splitlines():
            if line.startswith("author-mail "):
                current["author"] = line.split("<", 1)[-1].rstrip(">")
            elif line.startswith("summary "):
                current["summary"] = line[8:]
            elif line.startswith("\t"):
                current["line"] = line[1:]
                if "commit" in current and "author" in current:
                    blames.append(dict(current))
                current = {}
            elif line and not line.startswith(" "):
                # Header line: hash orig_line result_line [group]
                parts = line.split()
                if parts:
                    current["commit"] = parts[0]

        return blames

    def trace_pattern(self, pattern_name: str, pattern_regex: str,
                      since: Optional[str] = None) -> TransmissionTree:
        """Build a transmission tree for a pattern from git history.

        Tracks when and how the pattern appeared in new files.
        """
        tree = TransmissionTree(pattern_name=pattern_name)

        if not self._git_available:
            return tree

        commits = self.get_log(since=since)

        # Track which files have the pattern and when they got it
        first_occurrence: dict[str, dict] = {}  # filepath -> {commit, email, date}

        for commit in commits:
            email = commit["email"]
            commit_hash = commit["hash"]
            date_str = commit.get("date", "")

            try:
                timestamp = datetime.fromisoformat(date_str)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                timestamp = datetime.now(timezone.utc)

            for filepath in commit["files"]:
                if not filepath or filepath.startswith("."):
                    continue

                if filepath in first_occurrence:
                    continue

                # Check if this file has the pattern at this commit
                content = self.get_file_at_commit(filepath, commit_hash)
                if content and pattern_regex:
                    try:
                        if re.search(pattern_regex, content, re.MULTILINE):
                            first_occurrence[filepath] = {
                                "commit": commit_hash,
                                "email": email,
                                "date": timestamp,
                            }
                    except re.error:
                        pass

        if not first_occurrence:
            return tree

        # Sort by date to find index case
        sorted_occurrences = sorted(
            first_occurrence.items(), key=lambda x: x[1]["date"]
        )

        # Index case
        index_file, index_info = sorted_occurrences[0]
        tree.index_case = index_file
        tree.index_developer = index_info["email"]
        tree.index_timestamp = index_info["date"]

        # Build transmission events
        # For each subsequent file, determine likely source
        infected_set = {index_file}

        for filepath, info in sorted_occurrences[1:]:
            # Determine source: find closest existing infection
            source = self._infer_source(
                filepath, info["email"], infected_set, commits
            )
            vector = self._infer_vector(
                filepath, info["email"], source, commits
            )

            event = TransmissionEvent(
                pattern_name=pattern_name,
                source_module=source,
                target_module=filepath,
                vector=vector,
                developer=info["email"],
                timestamp=info["date"],
                commit_hash=info["commit"],
            )
            tree.add_event(event)
            infected_set.add(filepath)

        return tree

    def _infer_source(self, target: str, developer: str,
                      infected_set: set[str],
                      commits: list[dict]) -> str:
        """Infer the most likely source of infection for a target file."""
        # Check if same developer touched infected files
        developer_infected = set()
        for commit in commits:
            if commit["email"] == developer:
                for f in commit["files"]:
                    if f in infected_set:
                        developer_infected.add(f)

        if developer_infected:
            # Pick the one closest by path
            return self._closest_by_path(target, developer_infected)

        # Otherwise, pick closest by path from all infected
        if infected_set:
            return self._closest_by_path(target, infected_set)

        return ""

    def _infer_vector(self, target: str, developer: str,
                      source: str, commits: list[dict]) -> TransmissionVector:
        """Infer the transmission vector."""
        if not source:
            return TransmissionVector.UNKNOWN

        # Check if same PR/commit touched both source and target
        for commit in commits:
            if developer == commit["email"] and source in commit["files"] and target in commit["files"]:
                return TransmissionVector.COPY_PASTE

        # Check if same developer habit
        dev_commits_with_pattern = 0
        for commit in commits:
            if commit["email"] == developer:
                dev_commits_with_pattern += 1
        if dev_commits_with_pattern >= 3:
            return TransmissionVector.DEVELOPER_HABIT

        # Check if in same directory (shared module)
        if source and target:
            source_dir = str(Path(source).parent)
            target_dir = str(Path(target).parent)
            if source_dir == target_dir:
                return TransmissionVector.SHARED_MODULE

        return TransmissionVector.UNKNOWN

    @staticmethod
    def _closest_by_path(target: str, candidates: set[str]) -> str:
        """Find the candidate closest to target by path distance."""
        target_parts = Path(target).parts
        best = ""
        best_score = -1

        for cand in candidates:
            cand_parts = Path(cand).parts
            # Count common prefix parts
            common = 0
            for a, b in zip(target_parts, cand_parts):
                if a == b:
                    common += 1
                else:
                    break
            if common > best_score:
                best_score = common
                best = cand

        return best or (candidates.pop() if candidates else "")

    def get_developer_stats(self, tree: TransmissionTree) -> dict[str, int]:
        """Count infections caused per developer."""
        stats: dict[str, int] = {}
        for event in tree.events:
            stats[event.developer] = stats.get(event.developer, 0) + 1
        return stats
