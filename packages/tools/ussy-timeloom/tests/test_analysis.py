from __future__ import annotations

from ussy_timeloom.analysis import (
    analyze_draft,
    check_selvedge_integrity,
    detect_floats,
    find_coupling_clusters,
    find_pattern_repeats,
)
from ussy_timeloom.weave_engine import WeaveDraft


def _draft():
    return WeaveDraft(
        width=3,
        height=6,
        cells=[
            [1, 0, 1],
            [1, 0, 1],
            [0, 0, 0],
            [1, 0, 1],
            [1, 0, 1],
            [0, 0, 0],
        ],
        thread_colors=["#111111", "#222222", "#333333"],
        row_colors=["#444444"] * 6,
    )


def test_detect_floats():
    floats = detect_floats(_draft(), ["a", "b", "c"], min_float_length=2)
    assert any(info.file == "b" for info in floats)


def test_selvedge_integrity():
    assert 0 <= check_selvedge_integrity(_draft()) <= 1


def test_pattern_repeats():
    repeats = find_pattern_repeats(_draft(), ["a", "b", "c"])
    assert repeats


def test_coupling_clusters():
    clusters = find_coupling_clusters(_draft(), ["a", "b", "c"])
    assert clusters


def test_analyze_draft():
    result = analyze_draft(_draft(), ["a", "b", "c"], min_float_length=2)
    assert result.total_crossings == 8
    assert result.density > 0
