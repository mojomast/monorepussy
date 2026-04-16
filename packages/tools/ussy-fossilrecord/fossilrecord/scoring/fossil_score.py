"""Fossil Score computation — a robustness score (0-100) for developer tools.

Score formula:
    fossil_score = weighted_sum(
        parse_rate * 0.2,
        analysis_accuracy * 0.3,
        crash_resistance * 0.3,
        memory_efficiency * 0.1,
        ai_comprehension * 0.1
    ) * 100

Scores are broken down by esolang category (invisible, 2D, self-modifying, etc.)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fossilrecord.corpus.loader import StressCategory
from fossilrecord.harness.runner import TestSuiteResult


# Default weights for the Fossil Score components
DEFAULT_WEIGHTS: dict[str, float] = {
    "parse_rate": 0.2,
    "analysis_accuracy": 0.3,
    "crash_resistance": 0.3,
    "memory_efficiency": 0.1,
    "ai_comprehension": 0.1,
}


@dataclass
class FossilScoreBreakdown:
    """Breakdown of a Fossil Score by category and component."""
    overall_score: float = 0.0  # 0-100
    components: dict[str, float] = field(default_factory=dict)
    category_scores: dict[str, float] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 2),
            "components": {k: round(v, 4) for k, v in self.components.items()},
            "category_scores": {k: round(v, 2) for k, v in self.category_scores.items()},
            "weights": self.weights,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


@dataclass
class FossilScore:
    """Complete Fossil Score result."""
    tool_name: str
    version: str = ""
    breakdown: FossilScoreBreakdown = field(default_factory=FossilScoreBreakdown)
    suite_summary: dict[str, Any] = field(default_factory=dict)

    @property
    def score(self) -> float:
        return self.breakdown.overall_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "version": self.version,
            "score": round(self.score, 2),
            "breakdown": self.breakdown.to_dict(),
            "suite_summary": self.suite_summary,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: Path | str) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> FossilScore:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FossilScore:
        bd = data.get("breakdown", {})
        breakdown = FossilScoreBreakdown(
            overall_score=bd.get("overall_score", 0.0),
            components=bd.get("components", {}),
            category_scores=bd.get("category_scores", {}),
            weights=bd.get("weights", {}),
        )
        return cls(
            tool_name=data.get("tool_name", ""),
            version=data.get("version", ""),
            breakdown=breakdown,
            suite_summary=data.get("suite_summary", {}),
        )


def compute_fossil_score(
    suite_result: TestSuiteResult,
    tool_name: str = "unknown",
    version: str = "",
    weights: dict[str, float] | None = None,
) -> FossilScore:
    """Compute the Fossil Score for a tool based on test suite results.

    Args:
        suite_result: The test suite result to score.
        tool_name: Name of the tool being scored.
        version: Version of the tool.
        weights: Optional custom weights. Defaults to DEFAULT_WEIGHTS.

    Returns:
        FossilScore with breakdown by component and category.
    """
    w = weights or DEFAULT_WEIGHTS

    # Compute component scores (each 0-1)
    components = {
        "parse_rate": suite_result.parse_rate(),
        "analysis_accuracy": suite_result.analysis_accuracy(),
        "crash_resistance": suite_result.crash_resistance(),
        "memory_efficiency": suite_result.memory_efficiency(),
        "ai_comprehension": suite_result.ai_rate(),
    }

    # Compute weighted overall score (0-100)
    overall = 0.0
    for component_name, score in components.items():
        weight = w.get(component_name, 0.0)
        overall += score * weight
    overall *= 100.0

    # Compute per-category scores
    category_scores: dict[str, float] = {}
    for category in StressCategory:
        cat_suite = suite_result.by_category(category)
        if cat_suite.results:
            cat_score = _compute_category_score(cat_suite, w)
            category_scores[category.value] = cat_score

    breakdown = FossilScoreBreakdown(
        overall_score=overall,
        components=components,
        category_scores=category_scores,
        weights=w,
    )

    return FossilScore(
        tool_name=tool_name,
        version=version,
        breakdown=breakdown,
        suite_summary=suite_result.summary(),
    )


def _compute_category_score(
    suite: TestSuiteResult,
    weights: dict[str, float],
) -> float:
    """Compute the Fossil Score for a category-filtered test suite."""
    components = {
        "parse_rate": suite.parse_rate(),
        "analysis_accuracy": suite.analysis_accuracy(),
        "crash_resistance": suite.crash_resistance(),
        "memory_efficiency": suite.memory_efficiency(),
        "ai_comprehension": suite.ai_rate(),
    }
    score = 0.0
    for name, val in components.items():
        weight = weights.get(name, 0.0)
        score += val * weight
    return round(score * 100.0, 2)


def compute_historical_scores(
    scores: list[FossilScore],
) -> dict[str, Any]:
    """Analyze historical Fossil Scores to track improvement over time.

    Args:
        scores: List of FossilScore instances, ordered by version/date.

    Returns:
        Dictionary with trend analysis.
    """
    if not scores:
        return {"trend": "no_data", "data_points": 0}

    score_values = [s.score for s in scores]

    # Trend analysis
    if len(score_values) == 1:
        trend = "baseline"
        improvement = 0.0
    else:
        first = score_values[0]
        last = score_values[-1]
        improvement = last - first
        if improvement > 5:
            trend = "improving"
        elif improvement < -5:
            trend = "declining"
        else:
            trend = "stable"

    return {
        "trend": trend,
        "data_points": len(scores),
        "first_score": score_values[0],
        "latest_score": score_values[-1],
        "improvement": round(improvement, 2),
        "scores": [round(s, 2) for s in score_values],
        "versions": [s.version for s in scores],
        "best_score": max(score_values),
        "worst_score": min(score_values),
    }
