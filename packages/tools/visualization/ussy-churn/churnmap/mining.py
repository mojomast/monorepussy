"""Git mining for ChurnMap."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class MinedCommit:
    """One mined commit record."""

    commit_hash: str
    timestamp: datetime
    modules: tuple[str, ...]
    files: tuple[str, ...]
    author: str


def _parse_date(value: str | datetime | None) -> datetime | None:
    """Parse a CLI date or return the input datetime."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _module_name(relative_path: Path, depth: int) -> str:
    """Group a file path into a module name."""

    parts = relative_path.parts
    if len(parts) <= 1:
        return "root"
    dir_parts = parts[:-1]
    keep = min(max(depth, 1), len(dir_parts))
    return "/".join(dir_parts[:keep]) or "root"


def _from_pydriller(
    repo_path: Path,
    since: datetime | None,
    until: datetime | None,
) -> list[MinedCommit]:
    """Mine commits using PyDriller when available."""

    try:
        from pydriller import Repository  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised in fallback tests
        raise RuntimeError(str(exc)) from exc

    kwargs: dict[str, object] = {}
    if since is not None:
        kwargs["since"] = since
    if until is not None:
        kwargs["to"] = until

    commits: list[MinedCommit] = []
    for commit in Repository(str(repo_path), **kwargs).traverse_commits():
        modifications = getattr(commit, "modifications", None)
        if modifications is None:
            modifications = getattr(commit, "modified_files", [])
        files = tuple(
            sorted(
                {
                    str(
                        Path(
                            getattr(mod, "new_path", None)
                            or getattr(mod, "old_path", None)
                            or getattr(mod, "filename", None)
                            or ""
                        )
                    )
                    for mod in modifications
                    if getattr(mod, "new_path", None)
                    or getattr(mod, "old_path", None)
                    or getattr(mod, "filename", None)
                }
            )
        )
        commits.append(
            MinedCommit(
                commit_hash=commit.hash,
                timestamp=commit.committer_date,
                modules=tuple(),
                files=files,
                author=commit.author.email or commit.author.name,
            )
        )
    return commits


def _from_git_cli(
    repo_path: Path,
    since: datetime | None,
    until: datetime | None,
) -> list[MinedCommit]:
    """Mine commits via git when PyDriller is unavailable."""

    command = [
        "git",
        "-C",
        str(repo_path),
        "log",
        "--reverse",
        "--name-only",
        "--format=%H|%ct|%an",
    ]
    if since is not None:
        command.extend([f"--since={since.isoformat()}"])
    if until is not None:
        command.extend([f"--until={until.isoformat()}"])
    raw = subprocess.run(command, check=True, capture_output=True, text=True).stdout
    commits: list[MinedCommit] = []
    current_header: str | None = None
    current_paths: list[str] = []
    for line in raw.splitlines():
        if not line:
            continue
        if "|" in line and line.count("|") >= 2:
            if current_header is not None:
                commit_hash, timestamp, author = current_header.split("|", 2)
                commits.append(
                    MinedCommit(
                        commit_hash=commit_hash,
                        timestamp=datetime.fromtimestamp(int(timestamp)),
                        modules=tuple(),
                        files=tuple(current_paths),
                        author=author,
                    )
                )
            current_header = line
            current_paths = []
            continue
        current_paths.append(line)
    if current_header is not None:
        commit_hash, timestamp, author = current_header.split("|", 2)
        commits.append(
            MinedCommit(
                commit_hash=commit_hash,
                timestamp=datetime.fromtimestamp(int(timestamp)),
                modules=tuple(),
                files=tuple(current_paths),
                author=author,
            )
        )
    return commits


def mine_repository(
    repo_path: str | Path,
    since: str | datetime | None = None,
    until: str | datetime | None = None,
    max_commits: int = 1000,
    depth: int = 1,
) -> list[MinedCommit]:
    """Mine commit/module data from a git repository."""

    path = Path(repo_path)
    since_dt = _parse_date(since)
    until_dt = _parse_date(until)
    if not path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {path}")
    repo_check = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    if repo_check.returncode != 0:
        raise ValueError(f"Not a git repository: {path}")

    try:
        commits = _from_pydriller(path, since_dt, until_dt)
    except (ImportError, RuntimeError):
        commits = _from_git_cli(path, since_dt, until_dt)

    enriched: list[MinedCommit] = []
    for commit in commits:
        modules = tuple(
            sorted(
                {
                    _module_name(Path(file_path), depth)
                    for file_path in commit.files
                    if file_path
                }
            )
        )
        if modules:
            enriched.append(
                MinedCommit(
                    commit_hash=commit.commit_hash,
                    timestamp=commit.timestamp,
                    modules=modules,
                    files=commit.files,
                    author=commit.author,
                )
            )

    enriched.sort(key=lambda item: item.timestamp)
    if max_commits > 0:
        enriched = enriched[-max_commits:]
    return enriched
