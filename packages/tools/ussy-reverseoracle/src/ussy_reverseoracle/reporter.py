from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from .models import AnalysisReport


def report_to_dict(report: AnalysisReport) -> dict[str, Any]:
    return report.to_dict()


def render_text(report: AnalysisReport) -> str:
    e = report.evaluation
    return "\n".join(
        [
            f"Decision: {report.decision}",
            f"Commit: {report.commit_hash}",
            f"Alternative: {report.alternative}",
            "",
            f"Baseline tests: {e.baseline.passed} passed, {e.baseline.failed} failed, {e.baseline.skipped} skipped",
            f"Counterfactual tests: {e.counterfactual.passed} passed, {e.counterfactual.failed} failed, {e.counterfactual.skipped} skipped",
            f"Baseline metrics: LOC={e.baseline_metrics.loc}, funcs={e.baseline_metrics.function_count}, classes={e.baseline_metrics.class_count}, deps={e.baseline_metrics.dependency_count}",
            f"Counterfactual metrics: LOC={e.counterfactual_metrics.loc}, funcs={e.counterfactual_metrics.function_count}, classes={e.counterfactual_metrics.class_count}, deps={e.counterfactual_metrics.dependency_count}",
            f"Diff: +{e.diff_added} -{e.diff_removed} ~{e.diff_modified}",
            f"Evolution steps: {len(report.evolution)}",
        ]
    )


def render_json(report: AnalysisReport) -> str:
    return json.dumps(report.to_dict(), indent=2)


def render_html(report: AnalysisReport) -> str:
    e = report.evaluation
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><title>ReverseOracle Report</title>
<style>body{{font-family:sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:.5rem;text-align:left}}th{{background:#f5f5f5}}</style>
</head><body>
<h1>ReverseOracle Report</h1>
<p><strong>Decision:</strong> {report.decision}</p>
<p><strong>Commit:</strong> {report.commit_hash}</p>
<p><strong>Alternative:</strong> {report.alternative}</p>
<table>
<tr><th>Metric</th><th>Baseline</th><th>Counterfactual</th></tr>
<tr><td>Tests Passed</td><td>{e.baseline.passed}</td><td>{e.counterfactual.passed}</td></tr>
<tr><td>Tests Failed</td><td>{e.baseline.failed}</td><td>{e.counterfactual.failed}</td></tr>
<tr><td>LOC</td><td>{e.baseline_metrics.loc}</td><td>{e.counterfactual_metrics.loc}</td></tr>
<tr><td>Functions</td><td>{e.baseline_metrics.function_count}</td><td>{e.counterfactual_metrics.function_count}</td></tr>
<tr><td>Classes</td><td>{e.baseline_metrics.class_count}</td><td>{e.counterfactual_metrics.class_count}</td></tr>
<tr><td>Dependencies</td><td>{e.baseline_metrics.dependency_count}</td><td>{e.counterfactual_metrics.dependency_count}</td></tr>
</table>
<h2>Evolution</h2>
<ul>{"".join(f"<li>{step.commit}</li>" for step in report.evolution)}</ul>
</body></html>"""


def save_report(repo_path: str | Path, report: AnalysisReport) -> Path:
    reports_dir = Path(repo_path) / ".reverseoracle" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{report.id}.json"
    path.write_text(render_json(report))
    return path


def load_report(repo_path: str | Path, report_id: str | None = None) -> AnalysisReport:
    reports_dir = Path(repo_path) / ".reverseoracle" / "reports"
    if report_id is None:
        candidates = sorted(reports_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            raise FileNotFoundError("No reports found")
        path = candidates[-1]
    else:
        path = reports_dir / f"{report_id}.json"
    data = json.loads(path.read_text())
    from .models import (
        AnalysisReport,
        DecisionContext,
        EvaluationResult,
        EvaluationStats,
        CodeMetrics,
        EvolutionStep,
    )

    ctx = DecisionContext(**data["context"])
    eval_data = data["evaluation"]
    evaluation = EvaluationResult(
        baseline=EvaluationStats(**eval_data["baseline"]),
        counterfactual=EvaluationStats(**eval_data["counterfactual"]),
        baseline_metrics=CodeMetrics(**eval_data["baseline_metrics"]),
        counterfactual_metrics=CodeMetrics(**eval_data["counterfactual_metrics"]),
        diff_added=eval_data.get("diff_added", 0),
        diff_removed=eval_data.get("diff_removed", 0),
        diff_modified=eval_data.get("diff_modified", 0),
    )
    evolution = [EvolutionStep(**item) for item in data.get("evolution", [])]
    return AnalysisReport(
        id=data["id"],
        decision=data["decision"],
        commit_hash=data["commit_hash"],
        alternative=data["alternative"],
        repo_path=data["repo_path"],
        counterfactual_path=data["counterfactual_path"],
        context=ctx,
        evolution=evolution,
        evaluation=evaluation,
    )
