"""Tests for the Fossil Score computation."""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from fossilrecord.corpus.loader import EsolangProgram, StressCategory
from fossilrecord.harness.plugins import PluginResult, PluginStatus
from fossilrecord.harness.runner import TestResult, TestSuiteResult
from fossilrecord.scoring.fossil_score import (
    FossilScore,
    FossilScoreBreakdown,
    compute_fossil_score,
    compute_historical_scores,
    DEFAULT_WEIGHTS,
)


def _make_suite(
    parse_rate=1.0,
    crash_resistance=1.0,
    ai_rate=1.0,
    n_programs=3,
):
    """Create a TestSuiteResult with controlled rates."""
    results = []
    plugin_names = ["parser", "linter", "formatter", "ai"]
    for i in range(n_programs):
        prog = EsolangProgram(
            name=f"Prog {i}",
            language="Brainfuck",
            source="+++.",
            expected_behavior="Test",
            categories=[StressCategory.MINIMALISTIC],
            difficulty=1,
        )
        plugin_results = []
        for j, pname in enumerate(plugin_names):
            if pname == "parser":
                status = PluginStatus.SUCCESS if (i / max(n_programs, 1)) < parse_rate else PluginStatus.FAILURE
            elif pname == "ai":
                status = PluginStatus.SUCCESS if (i / max(n_programs, 1)) < ai_rate else PluginStatus.FAILURE
            elif pname == "linter":
                status = PluginStatus.SUCCESS if (i / max(n_programs, 1)) < crash_resistance else PluginStatus.FAILURE
            else:
                status = PluginStatus.SUCCESS
            plugin_results.append(PluginResult(prog.name, pname, status))
        results.append(TestResult(program=prog, plugin_results=plugin_results))
    return TestSuiteResult(results=results, total_time_seconds=1.0)


class TestDefaultWeights:
    """Test that default weights are correct per spec."""

    def test_parse_rate_weight(self):
        assert DEFAULT_WEIGHTS["parse_rate"] == 0.2

    def test_analysis_accuracy_weight(self):
        assert DEFAULT_WEIGHTS["analysis_accuracy"] == 0.3

    def test_crash_resistance_weight(self):
        assert DEFAULT_WEIGHTS["crash_resistance"] == 0.3

    def test_memory_efficiency_weight(self):
        assert DEFAULT_WEIGHTS["memory_efficiency"] == 0.1

    def test_ai_comprehension_weight(self):
        assert DEFAULT_WEIGHTS["ai_comprehension"] == 0.1

    def test_weights_sum_to_one(self):
        assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 0.001


class TestFossilScoreBreakdown:
    """Tests for FossilScoreBreakdown."""

    def test_create_breakdown(self):
        bd = FossilScoreBreakdown(
            overall_score=75.0,
            components={"parse_rate": 0.9},
            category_scores={"minimalistic": 80.0},
        )
        assert bd.overall_score == 75.0

    def test_to_dict(self):
        bd = FossilScoreBreakdown(
            overall_score=80.0,
            components={"parse_rate": 0.95, "crash_resistance": 1.0},
        )
        d = bd.to_dict()
        assert d["overall_score"] == 80.0
        assert "components" in d

    def test_to_json(self):
        bd = FossilScoreBreakdown(overall_score=90.0)
        j = bd.to_json()
        data = json.loads(j)
        assert data["overall_score"] == 90.0


class TestFossilScore:
    """Tests for FossilScore."""

    def test_create_score(self):
        score = FossilScore(tool_name="test-tool", version="1.0")
        assert score.tool_name == "test-tool"

    def test_score_property(self):
        bd = FossilScoreBreakdown(overall_score=85.0)
        score = FossilScore(tool_name="test", breakdown=bd)
        assert score.score == 85.0

    def test_to_dict(self):
        bd = FossilScoreBreakdown(overall_score=75.0)
        score = FossilScore(tool_name="tool", version="2.0", breakdown=bd)
        d = score.to_dict()
        assert d["tool_name"] == "tool"
        assert d["score"] == 75.0

    def test_save_and_load(self, tmp_path):
        bd = FossilScoreBreakdown(overall_score=88.0, components={"parse_rate": 0.9})
        score = FossilScore(tool_name="mytool", version="3.0", breakdown=bd)
        path = tmp_path / "score.json"
        score.save(path)
        loaded = FossilScore.load(path)
        assert loaded.tool_name == "mytool"
        assert abs(loaded.score - 88.0) < 0.01

    def test_from_dict(self):
        d = {
            "tool_name": "test",
            "version": "1.0",
            "score": 75.0,
            "breakdown": {
                "overall_score": 75.0,
                "components": {"parse_rate": 0.8},
                "category_scores": {},
                "weights": {},
            },
            "suite_summary": {},
        }
        score = FossilScore.from_dict(d)
        assert score.tool_name == "test"
        assert score.score == 75.0


class TestComputeFossilScore:
    """Tests for compute_fossil_score function."""

    def test_perfect_score(self):
        suite = _make_suite(parse_rate=1.0, crash_resistance=1.0, ai_rate=1.0)
        score = compute_fossil_score(suite, tool_name="perfect")
        # With all rates at 1.0, score should be 100
        assert score.score >= 95.0

    def test_zero_score(self):
        # All plugins fail
        results = []
        prog = EsolangProgram("p", "BF", "+++.", "", [StressCategory.MINIMALISTIC], 1)
        plugin_results = [
            PluginResult("p", "parser", PluginStatus.FAILURE),
            PluginResult("p", "linter", PluginStatus.FAILURE),
            PluginResult("p", "formatter", PluginStatus.FAILURE),
            PluginResult("p", "ai", PluginStatus.FAILURE),
        ]
        results.append(TestResult(program=prog, plugin_results=plugin_results))
        suite = TestSuiteResult(results=results)
        score = compute_fossil_score(suite, tool_name="terrible")
        assert score.score < 50.0

    def test_score_deterministic(self):
        suite = _make_suite()
        score1 = compute_fossil_score(suite, tool_name="test")
        score2 = compute_fossil_score(suite, tool_name="test")
        assert score1.score == score2.score

    def test_score_range(self):
        suite = _make_suite()
        score = compute_fossil_score(suite)
        assert 0.0 <= score.score <= 100.0

    def test_has_component_breakdown(self):
        suite = _make_suite()
        score = compute_fossil_score(suite)
        assert "parse_rate" in score.breakdown.components
        assert "analysis_accuracy" in score.breakdown.components
        assert "crash_resistance" in score.breakdown.components
        assert "memory_efficiency" in score.breakdown.components
        assert "ai_comprehension" in score.breakdown.components

    def test_has_category_scores(self):
        suite = _make_suite()
        score = compute_fossil_score(suite)
        # Should have at least one category
        assert len(score.breakdown.category_scores) >= 1

    def test_custom_weights(self):
        suite = _make_suite()
        custom_weights = {
            "parse_rate": 1.0,
            "analysis_accuracy": 0.0,
            "crash_resistance": 0.0,
            "memory_efficiency": 0.0,
            "ai_comprehension": 0.0,
        }
        score = compute_fossil_score(suite, weights=custom_weights)
        # With parse_rate weight = 1.0, score should just be parse_rate * 100
        assert abs(score.score - suite.parse_rate() * 100) < 0.01

    def test_suite_summary_included(self):
        suite = _make_suite()
        score = compute_fossil_score(suite)
        assert "total_programs" in score.suite_summary


class TestComputeHistoricalScores:
    """Tests for compute_historical_scores."""

    def test_no_scores(self):
        result = compute_historical_scores([])
        assert result["trend"] == "no_data"

    def test_single_score(self):
        score = FossilScore(
            tool_name="tool",
            version="1.0",
            breakdown=FossilScoreBreakdown(overall_score=70.0),
        )
        result = compute_historical_scores([score])
        assert result["trend"] == "baseline"
        assert result["data_points"] == 1

    def test_improving_trend(self):
        scores = [
            FossilScore("tool", "1.0", FossilScoreBreakdown(overall_score=50.0)),
            FossilScore("tool", "2.0", FossilScoreBreakdown(overall_score=60.0)),
            FossilScore("tool", "3.0", FossilScoreBreakdown(overall_score=70.0)),
        ]
        result = compute_historical_scores(scores)
        assert result["trend"] == "improving"
        assert result["improvement"] == 20.0

    def test_declining_trend(self):
        scores = [
            FossilScore("tool", "1.0", FossilScoreBreakdown(overall_score=80.0)),
            FossilScore("tool", "2.0", FossilScoreBreakdown(overall_score=70.0)),
            FossilScore("tool", "3.0", FossilScoreBreakdown(overall_score=60.0)),
        ]
        result = compute_historical_scores(scores)
        assert result["trend"] == "declining"

    def test_stable_trend(self):
        scores = [
            FossilScore("tool", "1.0", FossilScoreBreakdown(overall_score=70.0)),
            FossilScore("tool", "2.0", FossilScoreBreakdown(overall_score=71.0)),
        ]
        result = compute_historical_scores(scores)
        assert result["trend"] == "stable"

    def test_best_and_worst(self):
        scores = [
            FossilScore("tool", "1.0", FossilScoreBreakdown(overall_score=50.0)),
            FossilScore("tool", "2.0", FossilScoreBreakdown(overall_score=90.0)),
            FossilScore("tool", "3.0", FossilScoreBreakdown(overall_score=70.0)),
        ]
        result = compute_historical_scores(scores)
        assert result["best_score"] == 90.0
        assert result["worst_score"] == 50.0
