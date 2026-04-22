from __future__ import annotations

from datetime import datetime

from ussy_timeloom.git_parser import CoChangeMatrix, CommitInfo
from ussy_timeloom.weave_engine import build_weave_draft, crossing_density


def _matrix():
    commits = [
        CommitInfo("a", "feat: one", "x", datetime.now(), "feature"),
        CommitInfo("b", "fix: two", "x", datetime.now(), "fix"),
    ]
    return CoChangeMatrix(
        files=["src/a.py", "src/b.py"], commits=commits, matrix=[[1, 0], [1, 1]]
    )


def test_build_weave_draft_assigns_colors():
    draft = build_weave_draft(_matrix())
    assert draft.width == 2
    assert draft.height == 2
    assert len(draft.thread_colors) == 2
    assert len(draft.row_colors) == 2


def test_crossing_density():
    draft = build_weave_draft(_matrix())
    assert crossing_density(draft) == 0.75
