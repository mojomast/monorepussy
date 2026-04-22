"""Rebase detector — ported from unconformity."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from git import Repo

from ..missing_git import default_branch_name, iter_reflog_events
from ..missing_models import Severity, UnconformityEvent, UnconformityType


# Minimum author↔committer delta to consider a rebase signal.
# 6 hours avoids false positives from timezone offsets and slow CI.
_DATE_DELTA_THRESHOLD = 60 * 60 * 6  # 6 hours in seconds


def detect_buttress(repo: Repo) -> List[UnconformityEvent]:
    """Detect rebased history via reflog and author/committer date delta."""
    events: List[UnconformityEvent] = []
    seen_shas: set[str] = set()

    # ------------------------------------------------------------------ #
    # Strategy 1 (PRIMARY): Reflog entries explicitly mentioning rebase   #
    # ------------------------------------------------------------------ #
    reflog_rebase_olds: dict[str, str] = {}  # old_sha -> reflog message
    for evt in iter_reflog_events(repo):
        if "rebase" not in evt.message.lower():
            continue
        old = evt.oldhexsha
        if not old or old == "0" * 40:
            continue
        reflog_rebase_olds[old] = evt.message

    for old_sha, reflog_msg in reflog_rebase_olds.items():
        if old_sha in seen_shas:
            continue
        # Confirm: is the pre-rebase SHA now unreachable from any branch?
        try:
            repo.commit(old_sha)  # still in object store?
        except Exception:
            continue
        reachable = any(_is_ancestor_safe(repo, old_sha, head.commit.hexsha) for head in repo.heads)
        if reachable:
            continue  # The old commit is still reachable — not a real rebase victim
        seen_shas.add(old_sha)
        events.append(
            UnconformityEvent(
                type=UnconformityType.BUTTRESS,
                severity=Severity.MEDIUM,
                description=(
                    f"Reflog confirms rebase: pre-rebase commit {old_sha[:8]} "
                    f"is no longer reachable from any branch."
                ),
                affected_commits=[old_sha],
                detected_at=datetime.now(timezone.utc),
                forensic_details={
                    "pre_rebase_sha": old_sha,
                    "reflog_message": reflog_msg,
                    "signal": "reflog",
                },
                geological_metaphor=(
                    "Older layers were truncated; fresh strata were deposited "
                    "against the cut face, hiding the original sequence."
                ),
            )
        )

    # ------------------------------------------------------------------ #
    # Strategy 2 (SECONDARY): Large author↔committer date delta           #
    # ------------------------------------------------------------------ #
    for head in repo.heads:
        for commit in repo.iter_commits(head.name):
            if commit.hexsha in seen_shas:
                continue
            if len(commit.parents) != 1:
                continue

            delta = abs(commit.committed_date - commit.authored_date)
            if delta < _DATE_DELTA_THRESHOLD:
                continue

            seen_shas.add(commit.hexsha)
            events.append(
                UnconformityEvent(
                    type=UnconformityType.BUTTRESS,
                    severity=Severity.LOW,
                    description=(
                        f"Commit {commit.hexsha[:8]} has a {delta / 3600:.1f}h gap "
                        f"between author and committer dates — possible rebase."
                    ),
                    affected_commits=[commit.hexsha],
                    detected_at=datetime.now(timezone.utc),
                    forensic_details={
                        "author_date": str(commit.authored_datetime),
                        "committer_date": str(commit.committed_datetime),
                        "delta_seconds": delta,
                        "parent": commit.parents[0].hexsha,
                        "message": commit.message.strip()[:200],
                        "signal": "date_delta",
                    },
                    geological_metaphor=(
                        "The rock record shows a discontinuity — the same material "
                        "appears to have been deposited at two different times."
                    ),
                )
            )

    return events


def _is_ancestor_safe(repo: Repo, older: str, newer: str) -> bool:
    try:
        repo.git.merge_base("--is-ancestor", older, newer)
        return True
    except Exception:
        return False
