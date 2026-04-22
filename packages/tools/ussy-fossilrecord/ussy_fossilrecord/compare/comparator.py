"""Tool comparator: compare robustness across tool versions or different tools."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ussy_fossilrecord.scoring.fossil_score import FossilScore, compute_historical_scores
from ussy_fossilrecord.harness.runner import TestSuiteResult


@dataclass
class ComparisonResult:
    """Result of comparing two tools/versions."""
    tool_a_name: str
    tool_b_name: str
    score_a: float
    score_b: float
    winner: str  # "a", "b", or "tie"
    score_diff: float
    component_diffs: dict[str, float] = field(default_factory=dict)
    category_diffs: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_a": self.tool_a_name,
            "tool_b": self.tool_b_name,
            "score_a": round(self.score_a, 2),
            "score_b": round(self.score_b, 2),
            "winner": self.winner,
            "score_diff": round(self.score_diff, 2),
            "component_diffs": {k: round(v, 4) for k, v in self.component_diffs.items()},
            "category_diffs": {k: round(v, 2) for k, v in self.category_diffs.items()},
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class ToolComparator:
    """Compare robustness of two tools or versions."""

    @staticmethod
    def compare(
        score_a: FossilScore,
        score_b: FossilScore,
    ) -> ComparisonResult:
        """Compare two Fossil Scores.

        Args:
            score_a: First tool's score.
            score_b: Second tool's score.

        Returns:
            ComparisonResult with detailed comparison.
        """
        diff = score_a.score - score_b.score

        if abs(diff) < 1.0:
            winner = "tie"
        elif diff > 0:
            winner = "a"
        else:
            winner = "b"

        # Component-level diffs
        component_diffs = {}
        all_components = set(score_a.breakdown.components.keys()) | set(
            score_b.breakdown.components.keys()
        )
        for comp in all_components:
            a_val = score_a.breakdown.components.get(comp, 0.0)
            b_val = score_b.breakdown.components.get(comp, 0.0)
            component_diffs[comp] = a_val - b_val

        # Category-level diffs
        category_diffs = {}
        all_categories = set(score_a.breakdown.category_scores.keys()) | set(
            score_b.breakdown.category_scores.keys()
        )
        for cat in all_categories:
            a_val = score_a.breakdown.category_scores.get(cat, 0.0)
            b_val = score_b.breakdown.category_scores.get(cat, 0.0)
            category_diffs[cat] = a_val - b_val

        return ComparisonResult(
            tool_a_name=score_a.tool_name,
            tool_b_name=score_b.tool_name,
            score_a=score_a.score,
            score_b=score_b.score,
            winner=winner,
            score_diff=diff,
            component_diffs=component_diffs,
            category_diffs=category_diffs,
        )

    @staticmethod
    def compare_historical(
        scores: list[FossilScore],
    ) -> dict[str, Any]:
        """Compare historical scores to track improvement.

        Args:
            scores: Ordered list of FossilScore instances.

        Returns:
            Historical trend analysis.
        """
        return compute_historical_scores(scores)

    @staticmethod
    def leaderboard(scores: list[FossilScore]) -> list[dict[str, Any]]:
        """Generate a leaderboard from multiple tool scores.

        Args:
            scores: List of FossilScore instances.

        Returns:
            Sorted list of tool scores, highest first.
        """
        entries = []
        for s in scores:
            entries.append({
                "tool_name": s.tool_name,
                "version": s.version,
                "fossil_score": round(s.score, 2),
            })
        entries.sort(key=lambda x: x["fossil_score"], reverse=True)
        return entries
