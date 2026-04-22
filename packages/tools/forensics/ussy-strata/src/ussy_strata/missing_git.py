"""Shared Git forensics helpers — ported from unconformity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Iterator, List, Sequence

from git import Repo


ZERO_SHA = "0" * 40
DEFAULT_BRANCH_NAMES = ("main", "master", "trunk")


@dataclass(frozen=True)
class ReflogEvent:
    refname: str
    oldhexsha: str
    newhexsha: str
    message: str
    timestamp: datetime | None


def local_branch_names(repo: Repo) -> List[str]:
    return [head.name for head in repo.heads]


def default_branch_name(repo: Repo) -> str | None:
    names = local_branch_names(repo)
    for candidate in DEFAULT_BRANCH_NAMES:
        if candidate in names:
            return candidate
    if names:
        return names[0]
    return None


def is_ancestor(repo: Repo, older: str, newer: str) -> bool:
    if older == newer:
        return True
    try:
        repo.git.merge_base("--is-ancestor", older, newer)
        return True
    except Exception:
        return False


def iter_reflog_events(repo: Repo) -> Iterator[ReflogEvent]:
    refs = []
    try:
        refs.append(repo.head.reference)
    except Exception:
        pass
    refs.extend(repo.heads)

    seen = set()
    for ref in refs:
        try:
            entries = ref.log()
        except Exception:
            continue
        for entry in entries:
            oldhexsha = getattr(entry, "oldhexsha", "")
            newhexsha = getattr(entry, "newhexsha", "")
            key = (ref.path, oldhexsha, newhexsha, getattr(entry, "message", ""))
            if key in seen:
                continue
            seen.add(key)
            timestamp = None
            when = getattr(entry, "time", None)
            if when:
                try:
                    timestamp = datetime.fromtimestamp(when, tz=timezone.utc)
                except Exception:
                    timestamp = None
            yield ReflogEvent(
                refname=ref.path,
                oldhexsha=oldhexsha,
                newhexsha=newhexsha,
                message=getattr(entry, "message", ""),
                timestamp=timestamp,
            )


def fsck_unreachable_commits(repo: Repo) -> List[str]:
    try:
        output = repo.git.fsck("--unreachable", "--no-reflogs", "--full")
    except Exception:
        return []

    shas: List[str] = []
    for line in output.splitlines():
        if "unreachable commit" not in line:
            continue
        parts = line.split()
        if not parts:
            continue
        sha = parts[-1]
        if len(sha) == 40:
            shas.append(sha)
    return shas


def unreachable_commit_tips(repo: Repo, shas: Sequence[str]) -> List[str]:
    unreachable = set(shas)
    parents = set()
    for sha in unreachable:
        try:
            commit = repo.commit(sha)
        except Exception:
            continue
        for parent in commit.parents:
            if parent.hexsha in unreachable:
                parents.add(parent.hexsha)
    tips = [sha for sha in unreachable if sha not in parents]
    tips.sort()
    return tips


def collect_unreachable_chain(repo: Repo, tip_sha: str, unreachable: Sequence[str]) -> List[str]:
    reachable = set(unreachable)
    stack = [tip_sha]
    seen = set()
    chain: List[str] = []
    while stack:
        sha = stack.pop()
        if sha in seen:
            continue
        seen.add(sha)
        chain.append(sha)
        try:
            commit = repo.commit(sha)
        except Exception:
            continue
        for parent in commit.parents:
            if parent.hexsha in reachable:
                stack.append(parent.hexsha)
    return chain


def commit_patch_id(repo: Repo, commit_sha: str, parent_sha: str | None = None) -> str | None:
    try:
        if parent_sha is None:
            diff_text = repo.git.show(
                commit_sha,
                "--format=",
                "--no-ext-diff",
                "--no-renames",
                "--unified=0",
            )
        else:
            diff_text = repo.git.diff(
                parent_sha,
                commit_sha,
                "--no-ext-diff",
                "--no-renames",
                "--unified=0",
            )
        if not diff_text.strip():
            return None
        patch_id_output = repo.git.execute(
            ["git", "patch-id", "--stable"],
            istream=BytesIO(diff_text.encode("utf-8")),
        )
    except Exception:
        return None
    if not patch_id_output.strip():
        return None
    return patch_id_output.split()[0]


def range_patch_id(repo: Repo, base_sha: str, tip_sha: str) -> str | None:
    try:
        diff_text = repo.git.diff(
            base_sha,
            tip_sha,
            "--no-ext-diff",
            "--no-renames",
            "--unified=0",
        )
        if not diff_text.strip():
            return None
        patch_id_output = repo.git.execute(
            ["git", "patch-id", "--stable"],
            istream=BytesIO(diff_text.encode("utf-8")),
        )
    except Exception:
        return None
    if not patch_id_output.strip():
        return None
    return patch_id_output.split()[0]


def branch_commit_count(repo: Repo, rev: str) -> int:
    try:
        return sum(1 for _ in repo.iter_commits(rev, max_count=2000))
    except Exception:
        return 0


def business_gap_seconds(start: datetime, end: datetime) -> float:
    if end <= start:
        return 0.0
    total = (end - start).total_seconds()
    weekend_days = 0
    day = start.date()
    final = end.date()
    while day <= final:
        if day.weekday() >= 5:
            weekend_days += 1
        day += timedelta(days=1)
    return max(0.0, total - weekend_days * 86400.0)
