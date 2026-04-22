from __future__ import annotations

from datetime import datetime

from ussy_timeloom.git_parser import CoChangeMatrix, CommitInfo
from ussy_timeloom.renderers.svg import render_heatmap_svg, render_weave_svg
from ussy_timeloom.renderers.terminal import render_terminal
from ussy_timeloom.renderers.wif import render_wif
from ussy_timeloom.weave_engine import build_weave_draft


def _draft():
    commits = [
        CommitInfo("a", "feat: one", "x", datetime.now(), "feature"),
        CommitInfo("b", "fix: two", "x", datetime.now(), "fix"),
    ]
    matrix = CoChangeMatrix(
        files=["a.py", "b.py"], commits=commits, matrix=[[1, 0], [0, 1]]
    )
    return build_weave_draft(matrix), matrix


def test_render_weave_svg():
    draft, matrix = _draft()
    svg = render_weave_svg(draft, matrix.files, [c.message for c in matrix.commits])
    assert svg.startswith("<svg")
    assert "Legend" in svg


def test_render_terminal():
    draft, matrix = _draft()
    text = render_terminal(draft, [c.change_type for c in matrix.commits])
    assert "\x1b[" in text
    assert "█" in text or "▓" in text


def test_render_wif():
    draft, matrix = _draft()
    text = render_wif(draft, matrix.files, [c.change_type for c in matrix.commits])
    assert "[WIF]" in text
    assert "[Pattern]" in text


def test_render_heatmap_svg():
    svg = render_heatmap_svg([[1, 0], [0, 1]], ["a.py", "b.py"], ["c1", "c2"])
    assert svg.startswith("<svg")
