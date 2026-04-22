"""Click-based CLI interface for Terrarium."""

import os
import sys
from typing import Optional

import click

from . import __version__
from .metrics.engine import MetricsEngine
from .ecosystem.model import build_ecosystem
from .ecosystem.diagnosis import diagnose as diagnose_organism
from .adapters import load_adapters, merge_health_states
from .renderers.terminal import render_terrarium, render_health_summary
from .renderers.static_export import export_snapshot, render_text_snapshot
from .renderers.seasons import render_seasons_from_project
from .engine import TerrariumEngine
from .viz import render_dashboard
from .terminal import live_watch


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="terrarium")
@click.pass_context
def cli(ctx):
    """🌿 Terrarium — Your codebase is a living ecosystem."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Shared adapter options
_adapter_options = [
    click.option(
        "--fatigue-data", default=None, help="Path to fatigueussy JSON output"
    ),
    click.option(
        "--endemic-data", default=None, help="Path to endemicussy JSON output"
    ),
    click.option(
        "--sentinel-data", default=None, help="Path to sentinelussy JSON output"
    ),
    click.option(
        "--kompressi-data", default=None, help="Path to kompressiussy JSON output"
    ),
    click.option("--churnmap-data", default=None, help="Path to churnmap JSON output"),
    click.option("--seral-data", default=None, help="Path to seralussy JSON output"),
    click.option(
        "--proprioception-data",
        default=None,
        help="Path to proprioceptionussy JSON output",
    ),
    click.option(
        "--snapshot-data", default=None, help="Path to snapshotussy JSON output"
    ),
]


def _apply_adapter_options(func):
    """Apply shared adapter CLI options to a command."""
    for option in reversed(_adapter_options):
        func = option(func)
    return func


def _load_health_states(**kwargs) -> dict:
    """Load and merge health states from external adapters."""
    adapters = load_adapters(
        fatigue_data=kwargs.get("fatigue_data"),
        endemic_data=kwargs.get("endemic_data"),
        sentinel_data=kwargs.get("sentinel_data"),
        kompressi_data=kwargs.get("kompressi_data"),
        churnmap_data=kwargs.get("churnmap_data"),
        seral_data=kwargs.get("seral_data"),
        proprioception_data=kwargs.get("proprioception_data"),
        snapshot_data=kwargs.get("snapshot_data"),
    )
    return merge_health_states(adapters)


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--since", default=None, help='Time period (e.g. "6 months ago")')
@_apply_adapter_options
def watch(path, since, **adapter_kwargs):
    """Open live terrarium in terminal."""
    path = os.path.abspath(path)
    engine = MetricsEngine(path, since)
    project = engine.scan()
    health_states = _load_health_states(**adapter_kwargs)
    ecosystem = build_ecosystem(project, health_states)
    click.echo(render_terrarium(ecosystem))


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@_apply_adapter_options
def diagnose(path, **adapter_kwargs):
    """Check a specific module's health."""
    path = os.path.abspath(path)
    root = os.path.dirname(path)
    engine = MetricsEngine(root)
    metrics = engine.analyze_file(path)
    health_states = _load_health_states(**adapter_kwargs)
    organism = build_ecosystem(
        type(
            "Project",
            (),
            {"root_path": root, "modules": {metrics.path: metrics}, "avg_churn": 0},
        )(),
        health_states,
    ).organisms.get(metrics.path)

    if organism is None:
        click.echo(f"Error: Could not analyze {path}", err=True)
        sys.exit(1)

    diagnosis = diagnose_organism(organism)
    click.echo(diagnosis.format_report())


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--format", "fmt", type=click.Choice(["text", "svg"]), default="text")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--since", default=None, help='Time period (e.g. "6 months ago")')
@_apply_adapter_options
def snapshot(path, fmt, output, since, **adapter_kwargs):
    """Generate terrarium snapshot for CI."""
    path = os.path.abspath(path)
    engine = MetricsEngine(path, since)
    project = engine.scan()
    health_states = _load_health_states(**adapter_kwargs)
    ecosystem = build_ecosystem(project, health_states)

    if output:
        export_snapshot(ecosystem, output, format=fmt)
        click.echo(f"Snapshot exported to {output}")
    else:
        if fmt == "svg":
            from .renderers.static_export import render_svg_snapshot

            click.echo(render_svg_snapshot(ecosystem))
        else:
            click.echo(render_text_snapshot(ecosystem))


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--since", default=None, help='Time period (e.g. "6 months ago")')
@_apply_adapter_options
def seasons(path, since, **adapter_kwargs):
    """See ecosystem evolve over time."""
    path = os.path.abspath(path)
    output = render_seasons_from_project(path, since)
    click.echo(output)


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--since", default=None, help='Time period (e.g. "6 months ago")')
@_apply_adapter_options
def health(path, since, **adapter_kwargs):
    """Get health report."""
    path = os.path.abspath(path)
    engine = MetricsEngine(path, since)
    project = engine.scan()
    health_states = _load_health_states(**adapter_kwargs)
    ecosystem = build_ecosystem(project, health_states)

    click.echo(render_health_summary(ecosystem))

    most_critical = ecosystem.most_critical()
    healthiest = ecosystem.healthiest()

    if most_critical:
        click.echo(
            f"  Most critical: {most_critical.path} (health: {most_critical.health:.0f}/100)"
        )
    if healthiest:
        click.echo(
            f"  Healthiest: {healthiest.path} (health: {healthiest.health:.0f}/100)"
        )


# ---------------------------------------------------------------------------
# New engine-based commands
# ---------------------------------------------------------------------------


@cli.command(name="dashboard")
@click.option("--fatigue-data", default=None)
@click.option("--endemic-data", default=None)
@click.option("--sentinel-data", default=None)
@click.option("--kompressi-data", default=None)
@click.option("--churnmap-data", default=None)
@click.option("--seral-data", default=None)
@click.option("--proprioception-data", default=None)
@click.option("--snapshot-data", default=None)
def dashboard(**adapter_kwargs):
    """Print a one-shot Rich dashboard from adapter data."""
    adapters = load_adapters(
        fatigue_data=adapter_kwargs.get("fatigue_data"),
        endemic_data=adapter_kwargs.get("endemic_data"),
        sentinel_data=adapter_kwargs.get("sentinel_data"),
        kompressi_data=adapter_kwargs.get("kompressi_data"),
        churnmap_data=adapter_kwargs.get("churnmap_data"),
        seral_data=adapter_kwargs.get("seral_data"),
        proprioception_data=adapter_kwargs.get("proprioception_data"),
        snapshot_data=adapter_kwargs.get("snapshot_data"),
    )
    engine = TerrariumEngine(adapters)
    engine.collect()
    health = engine.score()
    panel = render_dashboard(health)
    from rich.console import Console

    console = Console()
    console.print(panel)


@cli.command()
@click.option("--interval", default=5, help="Refresh interval in seconds")
@click.option("--fatigue-data", default=None)
@click.option("--endemic-data", default=None)
@click.option("--sentinel-data", default=None)
@click.option("--kompressi-data", default=None)
@click.option("--churnmap-data", default=None)
@click.option("--seral-data", default=None)
@click.option("--proprioception-data", default=None)
@click.option("--snapshot-data", default=None)
def watch_live(interval, **adapter_kwargs):
    """Live watch mode using the new engine and Rich dashboard."""
    adapters = load_adapters(
        fatigue_data=adapter_kwargs.get("fatigue_data"),
        endemic_data=adapter_kwargs.get("endemic_data"),
        sentinel_data=adapter_kwargs.get("sentinel_data"),
        kompressi_data=adapter_kwargs.get("kompressi_data"),
        churnmap_data=adapter_kwargs.get("churnmap_data"),
        seral_data=adapter_kwargs.get("seral_data"),
        proprioception_data=adapter_kwargs.get("proprioception_data"),
        snapshot_data=adapter_kwargs.get("snapshot_data"),
    )
    engine = TerrariumEngine(adapters)
    live_watch(engine, interval=interval)


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["json", "csv"]), default="json")
@click.option("--output", "-o", default="-", help="Output file (default: stdout)")
@click.option("--fatigue-data", default=None)
@click.option("--endemic-data", default=None)
@click.option("--sentinel-data", default=None)
@click.option("--kompressi-data", default=None)
@click.option("--churnmap-data", default=None)
@click.option("--seral-data", default=None)
@click.option("--proprioception-data", default=None)
@click.option("--snapshot-data", default=None)
def export(fmt, output, **adapter_kwargs):
    """Export current metrics to JSON or CSV."""
    adapters = load_adapters(
        fatigue_data=adapter_kwargs.get("fatigue_data"),
        endemic_data=adapter_kwargs.get("endemic_data"),
        sentinel_data=adapter_kwargs.get("sentinel_data"),
        kompressi_data=adapter_kwargs.get("kompressi_data"),
        churnmap_data=adapter_kwargs.get("churnmap_data"),
        seral_data=adapter_kwargs.get("seral_data"),
        proprioception_data=adapter_kwargs.get("proprioception_data"),
        snapshot_data=adapter_kwargs.get("snapshot_data"),
    )
    engine = TerrariumEngine(adapters)
    engine.collect()

    if fmt == "json":
        data = engine.to_json()
    else:
        import csv
        import io

        health = engine.score()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["dimension", "score"])
        for key, value in health.to_dict().items():
            if isinstance(value, float):
                writer.writerow([key, f"{value:.4f}"])
        data = buf.getvalue()

    if output == "-":
        click.echo(data)
    else:
        with open(output, "w", encoding="utf-8") as f:
            f.write(data)
        click.echo(f"Exported to {output}")


def main(argv: Optional[list] = None) -> int:
    """Entry point compatible with the old argparse CLI."""
    try:
        cli(args=argv)
        return 0
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 0
        # Click returns 2 for bad arguments; old CLI returned 1
        return 1 if code == 2 else code
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        return 1
