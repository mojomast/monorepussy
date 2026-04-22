"""Core repository scanner — ported from unconformity."""

from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import List, Sequence

from git import InvalidGitRepositoryError, NoSuchPathError, Repo

from .missing_detectors import (
    detect_angular,
    detect_buttress,
    detect_disconformity,
    detect_nonconformity,
    detect_paraconformity,
)
from .missing_models import ScanResult, Severity, UnconformityEvent, UnconformityType


_SEVERITY_ORDER = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _branch_commits(repo: Repo, branch: str | None) -> int:
    try:
        if branch:
            return sum(1 for _ in repo.iter_commits(branch, max_count=2000))
        return sum(1 for _ in repo.iter_commits(all=True, max_count=2000))
    except Exception:
        return 0


def scan_repository(
    repo_path: str,
    types: Sequence[str] | None = None,
    min_severity: str | None = None,
    since: str | None = None,
    until: str | None = None,
    branch: str | None = None,
) -> ScanResult:
    """Scan a repository for unconformities."""
    started = perf_counter()
    repo = Repo(repo_path)
    detectors = [
        (UnconformityType.ANGULAR, detect_angular(repo)),
        (UnconformityType.DISCONFORMITY, detect_disconformity(repo)),
        (UnconformityType.NONCONFORMITY, detect_nonconformity(repo)),
        (UnconformityType.PARACONFORMITY, detect_paraconformity(repo)),
        (UnconformityType.BUTTRESS, detect_buttress(repo)),
    ]
    findings: List[UnconformityEvent] = []
    since_dt = _parse_dt(since)
    until_dt = _parse_dt(until)
    min_level = _SEVERITY_ORDER.get(Severity(min_severity), 0) if min_severity else 0
    allowed_types = {t.strip().lower() for t in types} if types else None
    for _, items in detectors:
        for event in items:
            if allowed_types and event.type.value not in allowed_types:
                continue
            if _SEVERITY_ORDER[event.severity] < min_level:
                continue
            if since_dt and event.detected_at < since_dt:
                continue
            if until_dt and event.detected_at > until_dt:
                continue
            findings.append(event)
    duration = perf_counter() - started
    return ScanResult(
        repo_path=repo_path,
        unconformities=findings,
        scan_time=datetime.now(timezone.utc),
        duration_seconds=duration,
        total_commits_scanned=_branch_commits(repo, branch),
    )


def open_repo(repo_path: str) -> Repo:
    try:
        return Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError):
        raise ValueError(f"Not a git repository: {repo_path}")
