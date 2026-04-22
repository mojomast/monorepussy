"""Parse git history into a co-change matrix."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import subprocess
from collections import defaultdict
from typing import Sequence


@dataclass(slots=True)
class CommitInfo:
    hash: str
    message: str
    author: str
    timestamp: datetime
    change_type: str


@dataclass(slots=True)
class CoChangeMatrix:
    """Binary files × commits matrix."""

    files: list[str]
    commits: list[CommitInfo]
    matrix: list[list[int]]


KEYWORDS = {
    "fix": ("fix", "bug", "patch", "hotfix", "repair"),
    "feature": ("feature", "feat", "add", "new", "implement"),
    "refactor": ("refactor", "restructure", "reorganize", "clean", "move", "rename"),
    "delete": ("delete", "remove"),
}


def classify_commit_type(message: str) -> str:
    """Classify a commit message into a coarse change type."""

    lower = message.lower()
    for change_type, keywords in KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            return change_type
    return "other"


def _run_git_log(repo_path: str, last: int | None) -> str:
    command = [
        "git",
        "-C",
        repo_path,
        "log",
        "--name-status",
        "--format=%H%x1f%an%x1f%s%x1f%cI%x1e",
    ]
    if last is not None:
        command.insert(5, f"-{last}")
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout


def _parse_status_lines(lines: Sequence[str]) -> set[str]:
    files: set[str] = set()
    for line in lines:
        if not line.strip():
            continue
        parts = line.split()
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            files.add(parts[1])
            files.add(parts[2])
        elif len(parts) >= 2:
            files.add(parts[1])
    return files


def parse_repo(
    repo_path: str, last: int | None = None, max_files: int | None = None
) -> CoChangeMatrix:
    """Parse a repository into a binary co-change matrix."""

    raw = _run_git_log(repo_path, last)
    commits_data: list[tuple[CommitInfo, set[str]]] = []
    file_counts: dict[str, int] = defaultdict(int)

    current_commit: CommitInfo | None = None
    current_files: set[str] = set()

    def flush_current() -> None:
        nonlocal current_commit, current_files
        if current_commit is None:
            return
        commits_data.append((current_commit, set(current_files)))
        for path in current_files:
            file_counts[path] += 1
        current_commit = None
        current_files = set()

    for line in raw.splitlines():
        if not line.strip():
            continue
        if "\x1f" in line:
            flush_current()
            parts = line.split("\x1f")
            if len(parts) != 4:
                continue
            commit_hash, author, message, timestamp = parts
            current_commit = CommitInfo(
                hash=commit_hash,
                message=message,
                author=author,
                timestamp=datetime.fromisoformat(timestamp),
                change_type=classify_commit_type(message),
            )
            continue
        if current_commit is None:
            continue
        current_files.update(_parse_status_lines([line]))

    flush_current()

    commits_data.reverse()

    files = sorted(file_counts, key=lambda path: (-file_counts[path], path))
    if max_files is not None:
        files = files[:max_files]

    index = {path: idx for idx, path in enumerate(files)}
    commits = [commit for commit, _ in commits_data]
    matrix = [[0 for _ in commits] for _ in files]

    for commit_idx, (_, changed_files) in enumerate(commits_data):
        for path in changed_files:
            if path in index:
                matrix[index[path]][commit_idx] = 1

    return CoChangeMatrix(files=files, commits=commits, matrix=matrix)
