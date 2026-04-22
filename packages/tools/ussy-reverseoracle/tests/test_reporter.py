from __future__ import annotations

from ussy_reverseoracle.models import (
    AnalysisReport,
    CodeMetrics,
    DecisionContext,
    EvaluationResult,
    EvaluationStats,
    EvolutionStep,
)
from ussy_reverseoracle.reporter import render_html, render_json, render_text


def test_renderers():
    report = AnalysisReport(
        id="1",
        decision="Redis vs Memcached",
        commit_hash="abc",
        alternative="Memcached",
        repo_path="/repo",
        counterfactual_path="/cf",
        context=DecisionContext(
            commit_hash="abc", description="Redis", alternative="Memcached"
        ),
        evolution=[
            EvolutionStep(commit="c1", diff="diff", prompt="prompt", applied=True)
        ],
        evaluation=EvaluationResult(
            baseline=EvaluationStats(passed=1),
            counterfactual=EvaluationStats(passed=2),
            baseline_metrics=CodeMetrics(loc=1),
            counterfactual_metrics=CodeMetrics(loc=2),
        ),
    )
    assert "Redis vs Memcached" in render_text(report)
    assert render_json(report).startswith("{")
    assert "<!doctype html>" in render_html(report)
