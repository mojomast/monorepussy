"""Force-push detector — ported from unconformity."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from git import Repo

from ..missing_git import (
    DEFAULT_BRANCH_NAMES,
    default_branch_name,
    is_ancestor,
    iter_reflog_events,
)
from ..missing_models import Severity, UnconformityEvent, UnconformityType


def detect_angular(repo: Repo) -> List[UnconformityEvent]:
    """Scan all reflog entries for non-fast-forward updates (force-pushes)."""
    events: List[UnconformityEvent] = []
    default_branch = default_branch_name(repo)
    seen: set[tuple[str, str, str]] = set()

    for event in iter_reflog_events(repo):
        old = event.oldhexsha
        new = event.newhexsha

        # Skip empty / initial-commit entries
        if not old or not new:
            continue
        if old == "0" * 40 or new == "0" * 40:
            continue
        if old == new:
            continue

        # Fast-forward = new is a descendant of old → not a force-push
        if is_ancestor(repo, old, new):
            continue

        dedup_key = (event.refname, old, new)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Determine severity: critical on protected/default branches
        branch_short = event.refname.split("/")[-1]
        is_default = (
            default_branch and branch_short == default_branch
        ) or branch_short in DEFAULT_BRANCH_NAMES
        severity = Severity.CRITICAL if is_default else Severity.HIGH

        events.append(
            UnconformityEvent(
                type=UnconformityType.ANGULAR,
                severity=severity,
                description=(
                    f"Force-push detected on '{event.refname}': "
                    f"{old[:8]}…  was replaced by {new[:8]}…"
                ),
                affected_commits=[old, new],
                detected_at=event.timestamp or datetime.now(timezone.utc),
                forensic_details={
                    "ref": event.refname,
                    "oldhexsha": old,
                    "newhexsha": new,
                    "reflog_message": event.message,
                    "fast_forward": False,
                    "is_default_branch": is_default,
                },
                geological_metaphor=(
                    "Older tilted strata were eroded and replaced by "
                    "a flat new sequence — evidence of violent resurfacing."
                ),
            )
        )
    return events
