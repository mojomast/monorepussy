"""Tests for the ToolComparator."""
from __future__ import annotations

import pytest

from fossilrecord.scoring.fossil_score import FossilScore, FossilScoreBreakdown
from fossilrecord.compare.comparator import ToolComparator, ComparisonResult


def _make_score(name: str, score_val: float, components=None, categories=None):
    """Create a FossilScore for testing."""
    comps = components or {
        "parse_rate": score_val / 100,
        "analysis_accuracy": score_val / 100,
        "crash_resistance": score_val / 100,
        "memory_efficiency": score_val / 100,
        "ai_comprehension": score_val / 100,
    }
    cats = categories or {"minimalistic": score_val}
    return FossilScore(
        tool_name=name,
        version="1.0",
        breakdown=FossilScoreBreakdown(
            overall_score=score_val,
            components=comps,
            category_scores=cats,
        ),
    )


class TestComparisonResult:
    """Tests for ComparisonResult."""

    def test_create_comparison(self):
        result = ComparisonResult(
            tool_a_name="tool-a",
            tool_b_name="tool-b",
            score_a=80.0,
            score_b=70.0,
            winner="a",
            score_diff=10.0,
        )
        assert result.winner == "a"
        assert result.score_diff == 10.0

    def test_to_dict(self):
        result = ComparisonResult(
            tool_a_name="a",
            tool_b_name="b",
            score_a=90.0,
            score_b=80.0,
            winner="a",
            score_diff=10.0,
            component_diffs={"parse_rate": 0.1},
        )
        d = result.to_dict()
        assert d["winner"] == "a"
        assert d["score_diff"] == 10.0


class TestToolComparator:
    """Tests for ToolComparator."""

    def test_compare_tool_a_wins(self):
        a = _make_score("tool-a", 90.0)
        b = _make_score("tool-b", 70.0)
        result = ToolComparator.compare(a, b)
        assert result.winner == "a"
        assert result.score_diff > 0

    def test_compare_tool_b_wins(self):
        a = _make_score("tool-a", 50.0)
        b = _make_score("tool-b", 80.0)
        result = ToolComparator.compare(a, b)
        assert result.winner == "b"
        assert result.score_diff < 0

    def test_compare_tie(self):
        a = _make_score("tool-a", 75.0)
        b = _make_score("tool-b", 75.5)
        result = ToolComparator.compare(a, b)
        assert result.winner == "tie"

    def test_compare_component_diffs(self):
        a = _make_score("tool-a", 80.0, components={
            "parse_rate": 0.9, "crash_resistance": 0.8
        })
        b = _make_score("tool-b", 70.0, components={
            "parse_rate": 0.5, "crash_resistance": 0.9
        })
        result = ToolComparator.compare(a, b)
        assert result.component_diffs["parse_rate"] > 0  # a better
        assert result.component_diffs["crash_resistance"] < 0  # b better

    def test_compare_category_diffs(self):
        a = _make_score("tool-a", 80.0, categories={"2d": 85.0, "whitespace": 75.0})
        b = _make_score("tool-b", 70.0, categories={"2d": 60.0, "whitespace": 80.0})
        result = ToolComparator.compare(a, b)
        assert result.category_diffs["2d"] > 0
        assert result.category_diffs["whitespace"] < 0

    def test_leaderboard_sorted(self):
        scores = [
            _make_score("tool-a", 70.0),
            _make_score("tool-b", 90.0),
            _make_score("tool-c", 80.0),
        ]
        board = ToolComparator.leaderboard(scores)
        assert board[0]["tool_name"] == "tool-b"
        assert board[1]["tool_name"] == "tool-c"
        assert board[2]["tool_name"] == "tool-a"

    def test_leaderboard_scores_descending(self):
        scores = [
            _make_score("a", 50.0),
            _make_score("b", 90.0),
            _make_score("c", 70.0),
        ]
        board = ToolComparator.leaderboard(scores)
        fossil_scores = [e["fossil_score"] for e in board]
        assert fossil_scores == sorted(fossil_scores, reverse=True)

    def test_compare_historical(self):
        scores = [
            _make_score("tool", 50.0),
            _make_score("tool", 60.0),
            _make_score("tool", 70.0),
        ]
        result = ToolComparator.compare_historical(scores)
        assert result["trend"] == "improving"
