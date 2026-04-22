"""Core utilities for Git operations wrapper."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final


class GitError(Exception):
    """Raised when a git command fails or returns unexpected output."""

    def __init__(self, message: str, returncode: int = 0, stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


def find_git_root(start: Path | str | None = None) -> Path | None:
    """Walk upward from *start* to locate the repository root (directory containing ``.git``).

    Args:
        start: Directory to begin searching (default: current working directory).

    Returns:
        Absolute path to the repository root, or ``None`` if not inside a git repo.
    """
    if start is None:
        start = Path.cwd()
    else:
        start = Path(start).resolve()

    for directory in [start, *start.parents]:
        git_dir = directory / ".git"
        if git_dir.exists():
            return directory

    return None


def run_git(
    *args: str,
    cwd: Path | str | None = None,
    timeout: float = 30.0,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a git subcommand safely with a timeout.

    Args:
        *args: Git command arguments (e.g. ``"log", "--oneline"``).
        cwd: Working directory for the subprocess.
        timeout: Seconds to wait before raising ``TimeoutExpired``.
        check: If ``True``, raise :class:`GitError` on non-zero exit.
        capture_output: If ``True``, capture stdout/stderr.

    Returns:
        Completed process object.

    Raises:
        GitError: If *check* is ``True`` and the command exits non-zero.
    """
    cmd = ["git", *args]
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitError(
            f"Git command timed out after {timeout}s: {' '.join(cmd)}",
            returncode=-1,
            stderr=str(exc),
        ) from exc

    if check and result.returncode != 0:
        raise GitError(
            f"Git command failed ({result.returncode}): {' '.join(cmd)}\n{result.stderr}",
            returncode=result.returncode,
            stderr=result.stderr,
        )

    return result


@dataclass(frozen=True, slots=True)
class Commit:
    """Lightweight representation of a git commit."""

    sha: str
    message: str
    author: str
    date: str


class GitRepo:
    """Convenience wrapper around a git repository."""

    _LOG_FORMAT: Final[str] = "%H%x00%an%x00%ad%x00%s"

    def __init__(self, path: Path | str | None = None) -> None:
        """Initialize wrapper for the repository at *path*.

        Args:
            path: Repository root or any path inside it. If ``None``, uses the
                current working directory.

        Raises:
            GitError: If *path* is not inside a git repository.
        """
        if path is None:
            path = Path.cwd()
        else:
            path = Path(path).resolve()

        root = find_git_root(path)
        if root is None:
            raise GitError(f"No git repository found at or above {path}")

        self.root = root

    def run(self, *args: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        """Run a git command inside this repository."""
        return run_git(*args, cwd=self.root, **kwargs)

    def current_branch(self) -> str:
        """Return the name of the current branch, or ``HEAD`` if detached."""
        result = self.run("rev-parse", "--abbrev-ref", "HEAD", check=False)
        return result.stdout.strip()

    def branches(self, remote: bool = False) -> list[str]:
        """Return a list of branch names."""
        cmd = ["branch", "--format=%(refname:short)"]
        if remote:
            cmd.append("-r")
        result = self.run(*cmd)
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def tags(self) -> list[str]:
        """Return a list of tag names."""
        result = self.run("tag", "--list")
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def log(
        self,
        max_count: int | None = None,
        since: str | None = None,
        until: str | None = None,
        paths: Sequence[str] | None = None,
    ) -> list[Commit]:
        """Traverse commit history and return parsed commits.

        Args:
            max_count: Limit the number of commits returned.
            since: ``--since`` argument (e.g. ``"2024-01-01"``).
            until: ``--until`` argument.
            paths: Only include commits touching these paths.
        """
        cmd = ["log", f"--format={self._LOG_FORMAT}"]
        if max_count is not None:
            cmd.extend(["--max-count", str(max_count)])
        if since:
            cmd.extend(["--since", since])
        if until:
            cmd.extend(["--until", until])
        if paths:
            cmd.append("--")
            cmd.extend(paths)

        result = self.run(*cmd)
        commits: list[Commit] = []
        for line in result.stdout.splitlines():
            parts = line.split("\x00")
            if len(parts) == 4:
                commits.append(
                    Commit(
                        sha=parts[0], author=parts[1], date=parts[2], message=parts[3]
                    )
                )
        return commits

    def reflog(self, ref: str = "HEAD") -> list[dict[str, str]]:
        """Parse the reflog for *ref* and return a list of entries.

        Each entry contains ``sha``, ``orig_sha``, ``author``, ``date``, and
        ``message`` keys.
        """
        result = self.run("reflog", ref, "--format=%H%x00%h%x00%an%x00%ad%x00%gs")
        entries: list[dict[str, str]] = []
        for line in result.stdout.splitlines():
            parts = line.split("\x00")
            if len(parts) == 5:
                entries.append(
                    {
                        "sha": parts[0],
                        "orig_sha": parts[1],
                        "author": parts[2],
                        "date": parts[3],
                        "message": parts[4],
                    }
                )
        return entries
