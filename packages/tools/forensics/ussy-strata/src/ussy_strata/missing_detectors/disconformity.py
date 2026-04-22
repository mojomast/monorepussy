"""Squash-merge detector — ported from unconformity."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from git import Repo

from ..missing_git import (
    collect_unreachable_chain,
    default_branch_name,
    fsck_unreachable_commits,
    unreachable_commit_tips,
)
from ..missing_models import Severity, UnconformityEvent, UnconformityType


# Only use file-count as a secondary signal if changed files exceeds this.
_FILE_COUNT_THRESHOLD = 15


def _diff_file_count(repo: Repo, parent_sha: str, commit_sha: str) -> int:
    """Return number of files changed between two commits."""
    try:
        output = repo.git.diff(parent_sha, commit_sha, "--numstat", "--no-ext-diff")
        return len([ln for ln in output.splitlines() if ln.strip()])
    except Exception:
        return 0


def detect_disconformity(
    repo: Repo,
    use_file_heuristic: bool = False,
) -> List[UnconformityEvent]:
    """Detect squash merges."""
    events: List[UnconformityEvent] = []
    branch = default_branch_name(repo)
    if not branch:
        return events

    unreachable_shas = fsck_unreachable_commits(repo)
    if not unreachable_shas:
        return events

    unreachable_tips = unreachable_commit_tips(repo, unreachable_shas)
    tip_chains: dict[str, List[str]] = {}
    for tip in unreachable_tips:
        chain = collect_unreachable_chain(repo, tip, unreachable_shas)
        tip_chains[tip] = chain

    # Build tree → tip map for fast O(1) lookup
    unreachable_tree_to_tip: dict[str, str] = {}
    for tip, chain in tip_chains.items():
        try:
            unreachable_tree_to_tip[repo.commit(tip).tree.hexsha] = tip
        except Exception:
            pass

    for commit in repo.iter_commits(branch, first_parent=True):
        if len(commit.parents) != 1:
            continue
        parent = commit.parents[0]

        # --- Primary signal: tree match ---
        matched_chain: List[str] = []
        if commit.tree.hexsha in unreachable_tree_to_tip:
            tip = unreachable_tree_to_tip[commit.tree.hexsha]
            matched_chain = tip_chains.get(tip, [])

        # --- Secondary signal: large diff (opt-in) ---
        files_changed = 0
        if not matched_chain and use_file_heuristic:
            files_changed = _diff_file_count(repo, parent.hexsha, commit.hexsha)
            if files_changed < _FILE_COUNT_THRESHOLD:
                continue
        elif not matched_chain:
            # No tree match and heuristic disabled — skip
            continue
        else:
            files_changed = _diff_file_count(repo, parent.hexsha, commit.hexsha)

        hidden = len(matched_chain)
        if hidden > 10:
            severity = Severity.HIGH
        elif hidden > 3:
            severity = Severity.MEDIUM
        else:
            severity = Severity.LOW

        desc = f"Squash merge detected: {files_changed} files changed."
        if matched_chain:
            desc += (
                f" Unreachable chain of {hidden} commit(s) shares the same "
                f"tree — original branch history was compressed away."
            )

        events.append(
            UnconformityEvent(
                type=UnconformityType.DISCONFORMITY,
                severity=severity,
                description=desc,
                affected_commits=[*matched_chain[-5:], commit.hexsha],
                detected_at=datetime.now(timezone.utc),
                forensic_details={
                    "squash_commit": commit.hexsha,
                    "message": commit.message.strip()[:200],
                    "files_changed": files_changed,
                    "hidden_commit_count": hidden,
                    "parent": parent.hexsha,
                    "tree_match": bool(matched_chain),
                },
                geological_metaphor=(
                    "Parallel strata were compressed into one preserved seam — "
                    "the intermediary layers exist but were eroded from the main record."
                ),
            )
        )
    return events
