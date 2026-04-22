"""CLI interface for Seral."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ussy_seral import __version__
from ussy_seral.config import SeralConfig
from ussy_seral.diff import diff_stages
from ussy_seral.disturbances import DisturbanceDetector
from ussy_seral.models import ModuleMetrics, Stage
from ussy_seral.prescribe import prescribe, governance_diff
from ussy_seral.scanner import Scanner
from ussy_seral.timeline import TimelineAnalyzer

console = Console()


def _find_repo_root(path: str) -> Optional[Path]:
    """Find the git repo root from the given path."""
    from ussy_seral.git_utils import find_repo_root as _find
    return _find(path)


def _display_scan_results(results: list[ModuleMetrics]) -> None:
    """Display scan results in a rich panel."""
    if not results:
        console.print("[yellow]No modules found.[/yellow]")
        return

    lines: list[str] = []
    for m in results:
        if m.stage is None:
            continue
        emoji = m.stage.emoji
        display = m.stage.display_name
        lines.append(f"  {emoji} {m.path:<40} {display}")
        lines.append(
            f"     Age: {_fmt_age(m.age_days)}  |  "
            f"Commits: {m.commit_count}  |  "
            f"Contributors: {m.contributor_count}"
        )
        lines.append(
            f"     Churn: {m.churn_rate:.0f}/week  |  "
            f"Tests: {m.test_coverage:.0%}  |  "
            f"Dependants: {m.dependent_count}"
        )
        lines.append("")

    panel = Panel(
        "\n".join(lines),
        title="Seral — Codebase Successional Analysis",
        border_style="green",
    )
    console.print(panel)


def _fmt_age(days: float) -> str:
    """Format age in days to a human-readable string."""
    if days < 30:
        return f"{days:.0f} days"
    elif days < 365:
        return f"{days / 30:.0f} months"
    else:
        return f"{days / 365:.1f} years"


def _display_prescription(prescription) -> None:
    """Display a governance prescription."""
    stage = prescription.stage
    emoji = stage.emoji
    display = stage.display_name
    path_str = prescription.path or "unknown"

    lines: list[str] = []
    if prescription.mandatory:
        lines.append("  MANDATORY:")
        for r in prescription.mandatory:
            lines.append(f"  • {r.description}")
        lines.append("")

    if prescription.recommended:
        lines.append("  RECOMMENDED:")
        for r in prescription.recommended:
            lines.append(f"  • {r.description}")
        lines.append("")

    if prescription.forbidden:
        lines.append("  FORBIDDEN (in this stage):")
        for r in prescription.forbidden:
            lines.append(f"  • {r.description}")
        lines.append("")

    lines.append(f"  Config: .seral/rules/{stage.value}.yaml")

    panel = Panel(
        "\n".join(lines),
        title=f"{emoji} {display} Governance for {path_str}",
        border_style="blue",
    )
    console.print(panel)


def _display_timeline(entries, projection=None) -> None:
    """Display a succession timeline."""
    if not entries:
        console.print("[yellow]No timeline data available.[/yellow]")
        return

    # Build timeline string
    stages_str = " ───► ".join(
        f"{e.stage.emoji} {e.stage.display_name}" for e in entries
    )
    dates_str = " ───► ".join(e.date for e in entries)

    lines = [f"  {stages_str}", f"  {dates_str}", ""]

    current = entries[-1]
    if current.metrics and current.stage:
        lines.append(
            f"  {' → '.join(e.stage.emoji for e in entries)}    "
            f"Current: {current.stage.display_name}"
        )
        lines.append("")

    if projection:
        lines.append(f"  Trajectory: Approaching {projection.target_stage.display_name} "
                      f"in {projection.estimated_time}")
        if projection.blockers:
            lines.append("  Blockers to next stage:")
            for b in projection.blockers:
                lines.append(f"    • {b}")
        if projection.recommended_actions:
            lines.append("  Recommended actions to accelerate succession:")
            for i, a in enumerate(projection.recommended_actions, 1):
                lines.append(f"    {i}. {a}")

    panel = Panel(
        "\n".join(lines),
        title="Succession Timeline",
        border_style="cyan",
    )
    console.print(panel)


def _display_disturbances(events) -> None:
    """Display disturbance events."""
    if not events:
        console.print("[green]No disturbance events detected.[/green]")
        return

    lines: list[str] = []
    for event in events:
        lines.append(f"  {event.path}")
        lines.append(f"    Event: {event.cause}")
        if event.date:
            lines.append(f"    Date: {event.date}")
        if event.previous_stage and event.current_stage:
            lines.append(
                f"    Previous stage: {event.previous_stage.display_name} → "
                f"Now: {event.current_stage.display_name}"
            )
        if event.governance_shift:
            lines.append(f"    Governance shift: {event.governance_shift}")
        lines.append("")

    panel = Panel(
        "\n".join(lines),
        title="🔥 Disturbance Events",
        border_style="red",
    )
    console.print(panel)


def _display_diff(changes: dict) -> None:
    """Display a governance diff."""
    lines: list[str] = []
    for item in changes.get("added", []):
        lines.append(f"  [green]{item}[/green]")
    for item in changes.get("changed", []):
        lines.append(f"  [yellow]{item}[/yellow]")
    for item in changes.get("removed", []):
        lines.append(f"  [red]{item}[/red]")

    if not lines:
        lines.append("  No governance changes between these stages.")

    console.print(Panel(
        "\n".join(lines),
        title="Governance Changes",
        border_style="magenta",
    ))


@click.group()
@click.version_option(version=__version__)
def main():
    """Seral — Codebase Successional Stage Detection with Governance Prescriptions."""
    pass


@main.command()
@click.argument("path", default=".")
def scan(path: str) -> None:
    """Classify all modules into successional stages."""
    target = Path(path).resolve()

    repo_root = _find_repo_root(str(target))
    if repo_root is None:
        console.print(f"[red]Error: {path} is not inside a git repository.[/red]")
        sys.exit(1)

    scanner = Scanner(repo_root=repo_root)

    if target.is_file():
        console.print("[red]Error: path must be a directory, not a file.[/red]")
        sys.exit(1)

    results = scanner.scan_directory(target)
    _display_scan_results(results)

    # Save results
    config = SeralConfig(repo_root)
    if not config.is_initialized():
        config.init()

    stages = config.load_stages()
    for m in results:
        if m.stage:
            old_stage = stages.get(m.path)
            stages[m.path] = m.stage.value

            # Record transition if stage changed
            if old_stage and old_stage != m.stage.value:
                from ussy_seral.models import StageTransition
                from datetime import datetime, timezone
                transition = StageTransition(
                    path=m.path,
                    from_stage=Stage.from_string(old_stage),
                    to_stage=m.stage,
                    timestamp=datetime.now(timezone.utc),
                    reason="Stage change detected by scan",
                )
                config.append_history(transition)

    config.save_stages(stages)


@main.command()
@click.argument("path", default=".")
def prescribe_cmd(path: str) -> None:
    """Generate governance rules for a module's current stage."""
    target = Path(path).resolve()

    repo_root = _find_repo_root(str(target))
    if repo_root is None:
        console.print(f"[red]Error: {path} is not inside a git repository.[/red]")
        sys.exit(1)

    scanner = Scanner(repo_root=repo_root)
    metrics = scanner.scan_module(target)
    if metrics.stage is None:
        metrics.compute_stage()

    prescription = prescribe(metrics.stage, str(target), metrics)
    _display_prescription(prescription)


# Register with a different name since 'prescribe' conflicts with the function
prescribe_cmd.name = "prescribe"


@main.command()
@click.argument("path", default=".")
def timeline(path: str) -> None:
    """Show successional trajectory over time."""
    target = Path(path).resolve()

    repo_root = _find_repo_root(str(target))
    if repo_root is None:
        console.print(f"[red]Error: {path} is not inside a git repository.[/red]")
        sys.exit(1)

    analyzer = TimelineAnalyzer(repo_root=repo_root)
    entries = analyzer.build_timeline(target)
    projection = analyzer.project_trajectory(target)

    _display_timeline(entries, projection)


@main.command()
def disturbances() -> None:
    """Detect ecological reset events."""
    repo_root = _find_repo_root(".")
    if repo_root is None:
        console.print("[red]Error: not inside a git repository.[/red]")
        sys.exit(1)

    scanner = Scanner(repo_root=repo_root)
    results = scanner.scan_directory(repo_root)

    # Filter to only disturbed modules
    disturbed = [m for m in results if m.stage == Stage.DISTURBED]

    detector = DisturbanceDetector(repo_root=repo_root)
    events = detector.detect_all(disturbed)

    _display_disturbances(events)


@main.command(name="diff")
@click.argument("path", default=".")
@click.option("--from", "from_stage", required=True, help="Source stage")
@click.option("--to", "to_stage", required=True, help="Target stage")
def diff_cmd(path: str, from_stage: str, to_stage: str) -> None:
    """Compare governance between stages."""
    try:
        from_s = Stage.from_string(from_stage)
        to_s = Stage.from_string(to_stage)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    changes = diff_stages(from_s, to_s)
    _display_diff(changes)


@main.command()
def init() -> None:
    """Create .seral/ config with default stage thresholds."""
    repo_root = _find_repo_root(".")
    if repo_root is None:
        console.print("[red]Error: not inside a git repository.[/red]")
        sys.exit(1)

    config = SeralConfig(repo_root)
    seral_dir = config.init()
    console.print(f"[green]Created .seral/ configuration at {seral_dir}[/green]")
    console.print(f"  - {config.config_file}")
    console.print(f"  - {config.stages_file}")
    console.print(f"  - {config.history_file}")
    console.print(f"  - {config.rules_dir}/")


@main.command()
def watch() -> None:
    """Continuous monitoring, alert on stage transitions."""
    console.print("[yellow]Watch mode — press Ctrl+C to stop[/yellow]")
    console.print("[dim]Checking for stage transitions...[/dim]")

    repo_root = _find_repo_root(".")
    if repo_root is None:
        console.print("[red]Error: not inside a git repository.[/red]")
        sys.exit(1)

    config = SeralConfig(repo_root)
    if not config.is_initialized():
        config.init()

    previous_stages = config.load_stages()
    scanner = Scanner(repo_root=repo_root)
    results = scanner.scan_directory(repo_root)

    transitions_found = False
    for m in results:
        if m.stage is None:
            continue
        old = previous_stages.get(m.path)
        if old and old != m.stage.value:
            try:
                old_stage = Stage.from_string(old)
            except ValueError:
                old_stage = Stage.PIONEER
            console.print(
                f"[bold yellow]🔄 {m.path}: "
                f"{old_stage.display_name} → {m.stage.display_name}[/bold yellow]"
            )
            transitions_found = True

            from ussy_seral.models import StageTransition
            from datetime import datetime, timezone
            transition = StageTransition(
                path=m.path,
                from_stage=old_stage,
                to_stage=m.stage,
                timestamp=datetime.now(timezone.utc),
                reason="Detected by watch",
            )
            config.append_history(transition)

    if not transitions_found:
        console.print("[green]No stage transitions detected.[/green]")

    # Update saved stages
    stages = {m.path: m.stage.value for m in results if m.stage}
    config.save_stages(stages)


if __name__ == "__main__":
    main()
