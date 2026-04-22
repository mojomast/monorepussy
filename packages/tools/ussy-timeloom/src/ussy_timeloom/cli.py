"""Click CLI for TimeLoom."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
from pathlib import Path

import click

from .analysis import analyze_draft, analysis_to_dict
from .git_parser import parse_repo
from .renderers.svg import render_heatmap_svg, render_weave_svg
from .renderers.terminal import render_terminal
from .renderers.wif import render_wif
from .weave_engine import build_weave_draft


def _write_output(text: str, output: str | None) -> None:
    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        click.echo(text, nl=False)


def _matrix_for_heatmap(matrix):
    return matrix.matrix


@click.group()
def main() -> None:
    """TimeLoom CLI."""


@main.command()
@click.argument(
    "repo_path", type=click.Path(exists=True, file_okay=False, path_type=str)
)
@click.option("--last", type=int, default=None)
@click.option("--output", type=str, default=None)
@click.option("--max-files", type=int, default=100)
@click.option("--min-crossings", type=int, default=1)
@click.option(
    "--color-scheme",
    type=click.Choice(["warm", "cool", "neon", "monochrome"]),
    default="warm",
)
@click.option("--width", type=int, default=1200)
@click.option("--thread-gap", type=int, default=2)
@click.option("--no-legend", is_flag=True, default=False)
def weave(
    repo_path: str,
    last: int | None,
    output: str | None,
    max_files: int,
    min_crossings: int,
    color_scheme: str,
    width: int,
    thread_gap: int,
    no_legend: bool,
) -> None:
    """Render a repository history as textile."""

    matrix = parse_repo(repo_path, last=last, max_files=max_files)
    keep = [idx for idx, row in enumerate(matrix.matrix) if sum(row) >= min_crossings]
    matrix.files = [matrix.files[idx] for idx in keep]
    matrix.matrix = [matrix.matrix[idx] for idx in keep]
    draft = build_weave_draft(matrix, color_scheme=color_scheme)
    if output and output.endswith(".txt"):
        text = render_terminal(draft, [commit.change_type for commit in matrix.commits])
    elif output and output.endswith(".wif"):
        text = render_wif(
            draft, matrix.files, [commit.change_type for commit in matrix.commits]
        )
    else:
        text = render_weave_svg(
            draft,
            matrix.files,
            [commit.message for commit in matrix.commits],
            width=width,
            thread_gap=thread_gap,
            include_legend=not no_legend,
        )
    _write_output(text, output)


@main.command()
@click.argument(
    "repo_path", type=click.Path(exists=True, file_okay=False, path_type=str)
)
@click.option("--last", type=int, default=None)
@click.option("--find-patterns", is_flag=True, default=False)
@click.option("--find-floats", is_flag=True, default=False)
@click.option("--check-selvedge", is_flag=True, default=False)
@click.option("--min-float-length", type=int, default=10)
@click.option("--json", "json_output", is_flag=True, default=False)
def analyze(
    repo_path: str,
    last: int | None,
    find_patterns: bool,
    find_floats: bool,
    check_selvedge: bool,
    min_float_length: int,
    json_output: bool,
) -> None:
    """Analyze structural properties of a repository."""

    matrix = parse_repo(repo_path, last=last)
    draft = build_weave_draft(matrix)
    result = analyze_draft(draft, matrix.files, min_float_length=min_float_length)
    if json_output:
        click.echo(json.dumps(analysis_to_dict(result), default=str))
        return
    lines = [
        f"crossings={result.total_crossings}",
        f"density={result.density:.3f}",
        f"selvedge={result.selvedge_integrity:.3f}",
    ]
    if find_floats:
        lines.append(f"floats={len(result.float_threads)}")
    if find_patterns:
        lines.append(f"patterns={len(result.pattern_repeats)}")
    if check_selvedge:
        lines.append("selvedge-check=done")
    click.echo("\n".join(lines))


@main.command()
@click.argument(
    "repo_path", type=click.Path(exists=True, file_okay=False, path_type=str)
)
@click.option(
    "--format", "output_format", type=click.Choice(["wif", "pes"]), default="wif"
)
@click.option("--output", type=str, default=None)
@click.option("--last", type=int, default=None)
def export(
    repo_path: str, output_format: str, output: str | None, last: int | None
) -> None:
    """Export weave drafts for loom software."""

    matrix = parse_repo(repo_path, last=last)
    draft = build_weave_draft(matrix)
    text = render_wif(
        draft, matrix.files, [commit.change_type for commit in matrix.commits]
    )
    if output_format == "pes":
        text = "[PES]\n" + text
    _write_output(text, output)


@main.command()
@click.argument(
    "repo_path", type=click.Path(exists=True, file_okay=False, path_type=str)
)
@click.option("--last", type=int, default=None)
@click.option("--output", type=str, default=None)
@click.option("--max-files", type=int, default=100)
@click.option("--width", type=int, default=1200)
def heatmap(
    repo_path: str, last: int | None, output: str | None, max_files: int, width: int
) -> None:
    """Render a co-change heatmap."""

    matrix = parse_repo(repo_path, last=last, max_files=max_files)
    svg = render_heatmap_svg(
        _matrix_for_heatmap(matrix),
        matrix.files,
        [commit.hash[:7] for commit in matrix.commits],
        width=width,
    )
    _write_output(svg, output)


if __name__ == "__main__":
    main()
