"""Git history parser — extracts change data from git repositories.

Uses subprocess to parse git log output. No external dependencies.
"""

import os
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


@dataclass
class CommitInfo:
    """Parsed information about a single commit."""

    hash: str
    author: str
    date: datetime
    message: str
    files_changed: List[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0
    is_merge: bool = False


@dataclass
class PullRequestInfo:
    """Synthetic PR info derived from merge commits."""

    id: str
    title: str
    created_at: datetime
    merged_at: Optional[datetime]
    files_changed: List[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0
    first_ci_at: Optional[datetime] = None


class GitHistoryParser:
    """Parse git log output to extract commit and change data."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.abspath(repo_path)

    def _run_git(self, args: List[str]) -> str:
        """Run a git command and return stdout."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    def parse_commits(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        author: Optional[str] = None,
        max_count: Optional[int] = None,
    ) -> List[CommitInfo]:
        """Parse git log into CommitInfo objects.

        Args:
            since: Git date spec (e.g., '7d', '2024-01-01')
            until: Git date spec
            author: Filter by author
            max_count: Maximum number of commits
        """
        args = ["log", "--format=%H|%an|%aI|%s", "--numstat", "--no-color"]
        if since:
            args.append(f"--since={since}")
        if until:
            args.append(f"--until={until}")
        if author:
            args.append(f"--author={author}")
        if max_count:
            args.append(f"--max-count={max_count}")

        output = self._run_git(args)
        return self._parse_log_output(output)

    def _parse_log_output(self, output: str) -> List[CommitInfo]:
        """Parse git log output with numstat into CommitInfo objects."""
        commits = []
        current_commit = None

        for line in output.strip().split("\n"):
            if not line.strip():
                continue

            # Commit header line: hash|author|date|message
            if "|" in line and not line.startswith("\t") and not re.match(r"^\d+\t", line):
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commit_hash, author, date_str, message = parts
                    try:
                        date = datetime.fromisoformat(date_str.strip())
                    except (ValueError, TypeError):
                        date = datetime.now()
                    current_commit = CommitInfo(
                        hash=commit_hash.strip(),
                        author=author.strip(),
                        date=date,
                        message=message.strip(),
                    )
                    commits.append(current_commit)
            elif current_commit and line.strip():
                # Numstat line: insertions\tdeletions\tfilename
                parts = line.split("\t")
                if len(parts) == 3:
                    try:
                        ins = int(parts[0]) if parts[0] != "-" else 0
                        dels = int(parts[1]) if parts[1] != "-" else 0
                        filename = parts[2].strip()
                        current_commit.insertions += ins
                        current_commit.deletions += dels
                        current_commit.files_changed.append(filename)
                    except ValueError:
                        pass

        return commits

    def get_merge_commits(self, since: Optional[str] = None) -> List[CommitInfo]:
        """Get only merge commits (proxy for PRs)."""
        # Use -m flag with --first-parent to show diff for merge commits
        args = [
            "log",
            "--merges",
            "--format=%H|%an|%aI|%s",
            "--numstat",
            "-m",
            "--first-parent",
            "--no-color",
        ]
        if since:
            args.append(f"--since={since}")
        output = self._run_git(args)
        return self._parse_log_output(output)

    def synthesize_prs(self, since: Optional[str] = None) -> List[PullRequestInfo]:
        """Synthesize PR-like objects from merge commits.

        For repos without PR metadata, we treat merge commits as PRs.
        """
        merge_commits = self.get_merge_commits(since)
        prs = []
        for i, mc in enumerate(merge_commits):
            # Estimate PR creation as 1-3 days before merge
            # (varies by review speed)
            estimated_created = mc.date - timedelta(days=1.5)
            # Estimate CI start as a few hours after creation
            estimated_ci = estimated_created + timedelta(hours=2)
            prs.append(
                PullRequestInfo(
                    id=f"pr_{mc.hash[:8]}",
                    title=mc.message,
                    created_at=estimated_created,
                    merged_at=mc.date,
                    files_changed=mc.files_changed,
                    insertions=mc.insertions,
                    deletions=mc.deletions,
                    first_ci_at=estimated_ci,
                )
            )
        return prs

    def get_file_module_map(self) -> Dict[str, str]:
        """Map file paths to module names (directory-based grouping)."""
        args = ["ls-files"]
        output = self._run_git(args)
        file_map = {}
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            path = line.strip()
            parts = path.split("/")
            if len(parts) > 1:
                module = "/".join(parts[:2])  # top-two directory levels
            else:
                module = "root"
            file_map[path] = module
        return file_map

    def get_deprecated_lines(self, since: Optional[str] = None) -> Tuple[int, int]:
        """Count deprecated lines (lines with TODO, FIXME, DEPRECATED) removed.

        Returns (deprecated_lines_removed, total_deprecated_lines).
        """
        args = ["log", "--format=%H", "-S", "DEPRECATED", "--no-color"]
        if since:
            args.append(f"--since={since}")
        output = self._run_git(args)
        commits_with_deprecated = [l.strip() for l in output.strip().split("\n") if l.strip()]

        # Count current deprecated lines
        grep_output = self._run_git(["grep", "-c", "DEPRECATED", "--", "."])
        total = 0
        for line in grep_output.strip().split("\n"):
            if ":" in line:
                try:
                    count = int(line.split(":")[-1])
                    total += count
                except ValueError:
                    pass

        removed = len(commits_with_deprecated) * 5  # estimate 5 lines per deprecation removal
        return removed, max(total, 1)

    def get_active_branches(self) -> List[str]:
        """List active branches."""
        output = self._run_git(["branch", "--list"])
        branches = []
        for line in output.strip().split("\n"):
            line = line.strip().lstrip("* ")
            if line:
                branches.append(line)
        return branches
