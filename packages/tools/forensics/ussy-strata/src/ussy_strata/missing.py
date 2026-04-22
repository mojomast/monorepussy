"""Git forensics for what's MISSING — unified entry point."""

from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.table import Table

from .missing_reporter import render_report, write_report
from .missing_scanner import scan_repository
from .missing_timeline import render_timeline
from .missing_watcher import watch_repository


console = Console()


@click.group()
def missing_cli() -> None:
    """ussy-strata missing — Git forensics for what's MISSING."""


@missing_cli.command("scan")
@click.argument("repo_path")
@click.option("--types", "types_", "-t", multiple=True)
@click.option("--severity", "-s")
@click.option("--since", "-S")
@click.option("--until", "-U")
@click.option("--branch", "-b")
@click.option("--json", "as_json", is_flag=True)
@click.option("--verbose", "-v", is_flag=True)
def scan(
    repo_path: str,
    types_: tuple[str, ...],
    severity: str | None,
    since: str | None,
    until: str | None,
    branch: str | None,
    as_json: bool,
    verbose: bool,
) -> None:
    """Scan a repository for unconformities."""
    result = scan_repository(
        repo_path,
        types=types_,
        min_severity=severity,
        since=since,
        until=until,
        branch=branch,
    )
    if as_json:
        click.echo(render_report(result, fmt="json"))
        return
    table = Table(title="ussy-strata missing — Unconformities Detected")
    table.add_column("Type", style="bold")
    table.add_column("Severity")
    table.add_column("Description")
    table.add_column("Affected Commits")
    table.add_column("Detected At")
    for item in result.unconformities:
        severity_color = {
            "critical": "red",
            "high": "orange3",
            "medium": "yellow",
            "low": "dim",
        }.get(item.severity.value, "white")
        table.add_row(
            item.type.value,
            f"[{severity_color}]{item.severity.value.upper()}[/{severity_color}]",
            item.description,
            ", ".join(c[:8] for c in item.affected_commits),
            item.detected_at.strftime("%Y-%m-%d %H:%M"),
        )
        if verbose:
            console.print(f"  [bold dim]{item.geological_metaphor}[/bold dim]")
            console.print(f"  [dim]{item.forensic_details}[/dim]")
    console.print(table)
    total = len(result.unconformities)
    console.print(
        f"\n[bold]Found {total} unconformit{'y' if total == 1 else 'ies'} "
        f"in {result.duration_seconds:.2f}s — "
        f"{result.total_commits_scanned} commits scanned.[/bold]"
    )


@missing_cli.command("report")
@click.argument("repo_path")
@click.option("--output", "-o")
@click.option("--format", "fmt", "-f", default="text")
@click.option("--threshold", "-t")
def report(repo_path: str, output: str | None, fmt: str, threshold: str | None) -> None:
    """Generate a full forensic report."""
    result = scan_repository(repo_path)
    content = render_report(result, fmt=fmt, threshold=threshold)
    write_report(output, content)


@missing_cli.command("timeline")
@click.argument("repo_path")
@click.option("--width", "-w", type=int)
@click.option("--branch", "-b")
@click.option("--color", "-c", default="auto")
def timeline(repo_path: str, width: int | None, branch: str | None, color: str) -> None:
    """Visualize repository history as geological strata."""
    result = scan_repository(repo_path, branch=branch)
    click.echo(render_timeline(result, width=width or 80))


@missing_cli.command("watch")
@click.argument("repo_path")
@click.option("--interval", "-i", type=float, default=30.0)
@click.option("--webhook", "-w")
def watch(repo_path: str, interval: float, webhook: str | None) -> None:
    """Monitor a repository for new unconformities in real-time."""
    for event in watch_repository(repo_path, interval=interval, webhook=webhook, iterations=1):
        click.echo(json.dumps(event, indent=2))


if __name__ == "__main__":
    missing_cli()
