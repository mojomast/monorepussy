from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import json

import click

from .config import load_config
from .context import reconstruct_context
from .evaluator import evaluate
from .evolution import evolve_counterfactual
from .generator import generate_counterfactual
from .marks import add_mark, load_marks, lookup_mark
from .models import AnalysisReport
from .reporter import load_report, render_html, render_json, render_text, save_report


@click.group()
def main() -> None:
    """ReverseOracle CLI."""


@main.command()
@click.argument("repo")
@click.argument("commit")
@click.option("--description", required=True)
@click.option("--alternative", default="")
@click.option("--module-path", default=None)
def mark(
    repo: str, commit: str, description: str, alternative: str, module_path: str | None
) -> None:
    mark = add_mark(repo, commit, description, alternative, module_path)
    click.echo(json.dumps(mark.to_dict(), indent=2))


@main.command(name="list-marks")
@click.argument("repo")
def list_marks(repo: str) -> None:
    marks = load_marks(repo)
    for mark in marks:
        click.echo(
            f"{mark.id}\t{mark.commit}\t{mark.description}\t{mark.alternative}\t{mark.created_at}"
        )


def _make_report(
    repo: str,
    decision: str,
    commit_hash: str,
    alternative: str,
    module_path: str | None,
    format: str,
) -> AnalysisReport:
    config = load_config(repo)
    context = reconstruct_context(repo, commit_hash, decision, alternative, module_path)
    artifact = generate_counterfactual(repo, context, config)
    steps = evolve_counterfactual(repo, artifact.path, context, config)
    evaluation = evaluate(repo, artifact.path, config.analysis.test_timeout)
    report = AnalysisReport(
        id=str(uuid4()),
        decision=decision,
        commit_hash=commit_hash,
        alternative=alternative,
        repo_path=repo,
        counterfactual_path=artifact.path,
        context=context,
        evolution=steps,
        evaluation=evaluation,
    )
    save_report(repo, report)
    return report


@main.command()
@click.argument("repo")
@click.option("--decision")
@click.option("--at-commit")
@click.option("--mark-id", default=None)
@click.option("--module-path", default=None)
@click.option("--format", "output_format", default="text")
def analyze(
    repo: str,
    decision: str | None,
    at_commit: str | None,
    mark_id: str | None,
    module_path: str | None,
    output_format: str,
) -> None:
    if mark_id:
        mark = lookup_mark(repo, mark_id=mark_id)
        if mark is None:
            raise click.ClickException(f"Mark not found: {mark_id}")
        decision = mark.description
        at_commit = mark.commit
        module_path = mark.module_path or module_path
        alternative = mark.alternative
    else:
        if decision is None or at_commit is None:
            raise click.ClickException(
                "--decision and --at-commit are required without --mark-id"
            )
        alternative = ""
    report = _make_report(
        repo, decision, at_commit, alternative, module_path, output_format
    )
    click.echo(_render_report(report, output_format))


@main.command()
@click.option("--counterfactual", required=True, type=click.Path(path_type=Path))
@click.option("--baseline", required=True, type=click.Path(path_type=Path))
@click.option("--format", "output_format", default="text")
def compare(counterfactual: Path, baseline: Path, output_format: str) -> None:
    config = load_config(baseline)
    evaluation = evaluate(baseline, counterfactual, config.analysis.test_timeout)
    report = AnalysisReport(
        id=str(uuid4()),
        decision="comparison",
        commit_hash="",
        alternative="",
        repo_path=str(baseline),
        counterfactual_path=str(counterfactual),
        context=reconstruct_context(baseline, "HEAD", "comparison", "", None),
        evolution=[],
        evaluation=evaluation,
    )
    click.echo(_render_report(report, output_format))


@main.command()
@click.argument("repo")
@click.option("--report-id", default=None)
@click.option("--format", "output_format", default="text")
@click.option("--output", type=click.Path(path_type=Path), default=None)
def report(
    repo: str, report_id: str | None, output_format: str, output: Path | None
) -> None:
    loaded = load_report(repo, report_id)
    rendered = _render_report(loaded, output_format)
    if output is not None:
        output.write_text(rendered)
    else:
        click.echo(rendered)


def _render_report(report: AnalysisReport, output_format: str) -> str:
    if output_format == "json":
        return render_json(report)
    if output_format == "html":
        return render_html(report)
    return render_text(report)


if __name__ == "__main__":
    main()
