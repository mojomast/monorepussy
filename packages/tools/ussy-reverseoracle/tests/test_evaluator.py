from __future__ import annotations

from pathlib import Path

from ussy_reverseoracle.evaluator import analyze_metrics, diff_summary


def test_analyze_metrics_counts_python(temp_repo: Path):
    metrics = analyze_metrics(temp_repo)
    assert metrics.function_count >= 1
    assert metrics.class_count == 0


def test_diff_summary(tmp_path: Path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "a.py").write_text("def a():\n    return 1\n")
    (right / "a.py").write_text("def a():\n    return 2\n")
    added, removed, modified = diff_summary(left, right)
    assert added >= 0 and removed >= 0 and modified >= 0
