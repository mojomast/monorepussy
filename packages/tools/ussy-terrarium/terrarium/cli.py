"""CLI interface for Terrarium."""

import argparse
import os
import sys
from typing import List, Optional

from . import __version__
from .metrics.engine import MetricsEngine
from .ecosystem.model import build_ecosystem, Ecosystem
from .ecosystem.diagnosis import diagnose, Diagnosis
from .adapters import load_adapters, merge_health_states
from .renderers.terminal import (
    render_terrarium,
    render_microscope,
    render_health_summary,
)
from .renderers.static_export import export_snapshot, render_text_snapshot
from .renderers.seasons import (
    render_seasons_view,
    render_seasons_from_project,
    get_git_history,
)


def _add_adapter_args(parser: argparse.ArgumentParser) -> None:
    """Add optional external data source flags to a subparser."""
    parser.add_argument(
        "--fatigue-data",
        default=None,
        help="Path to fatigueussy JSON output",
    )
    parser.add_argument(
        "--endemic-data",
        default=None,
        help="Path to endemicussy JSON output",
    )
    parser.add_argument(
        "--sentinel-data",
        default=None,
        help="Path to sentinelussy JSON output",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="terrarium",
        description="🌿 Terrarium — Your codebase is a living ecosystem",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # watch command
    watch_parser = subparsers.add_parser(
        "watch",
        help="Open live terrarium in terminal",
    )
    watch_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the project directory (default: current directory)",
    )
    _add_adapter_args(watch_parser)

    # diagnose command
    diagnose_parser = subparsers.add_parser(
        "diagnose",
        help="Check a specific module's health",
    )
    diagnose_parser.add_argument(
        "path",
        help="Path to the module file to diagnose",
    )
    _add_adapter_args(diagnose_parser)

    # snapshot command
    snapshot_parser = subparsers.add_parser(
        "snapshot",
        help="Generate terrarium snapshot for CI",
    )
    snapshot_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the project directory (default: current directory)",
    )
    snapshot_parser.add_argument(
        "--format",
        choices=["text", "svg"],
        default="text",
        help="Output format (default: text)",
    )
    snapshot_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path (default: stdout)",
    )
    _add_adapter_args(snapshot_parser)

    # seasons command
    seasons_parser = subparsers.add_parser(
        "seasons",
        help="See ecosystem evolve over time",
    )
    seasons_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the project directory (default: current directory)",
    )
    seasons_parser.add_argument(
        "--since",
        default=None,
        help='Time period (e.g. "6 months ago")',
    )
    _add_adapter_args(seasons_parser)

    # health command
    health_parser = subparsers.add_parser(
        "health",
        help="Get health report",
    )
    health_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the project directory (default: current directory)",
    )
    health_parser.add_argument(
        "--since",
        default=None,
        help='Time period (e.g. "6 months ago")',
    )
    _add_adapter_args(health_parser)

    return parser


def _load_health_states(args: argparse.Namespace) -> dict:
    """Load and merge health states from external adapters."""
    adapters = load_adapters(
        fatigue_data=getattr(args, "fatigue_data", None),
        endemic_data=getattr(args, "endemic_data", None),
        sentinel_data=getattr(args, "sentinel_data", None),
    )
    return merge_health_states(adapters)


def cmd_watch(args: argparse.Namespace) -> int:
    """Execute the 'watch' command — live terrarium view."""
    path = os.path.abspath(getattr(args, "path", "."))
    if not os.path.isdir(path):
        print(f"Error: {path} is not a directory", file=sys.stderr)
        return 1

    engine = MetricsEngine(path, getattr(args, "since", None))
    project = engine.scan()
    health_states = _load_health_states(args)
    ecosystem = build_ecosystem(project, health_states)

    print(render_terrarium(ecosystem))
    return 0


def cmd_diagnose(args: argparse.Namespace) -> int:
    """Execute the 'diagnose' command — module health report."""
    path = os.path.abspath(getattr(args, "path", "."))
    if not os.path.isfile(path):
        print(f"Error: {path} is not a file", file=sys.stderr)
        return 1

    # Find project root (directory containing the file)
    root = os.path.dirname(path)
    engine = MetricsEngine(root)
    metrics = engine.analyze_file(path)
    health_states = _load_health_states(args)
    organism = build_ecosystem(
        type(
            "Project",
            (),
            {"root_path": root, "modules": {metrics.path: metrics}, "avg_churn": 0},
        )(),
        health_states,
    ).organisms.get(metrics.path)

    if organism is None:
        print(f"Error: Could not analyze {path}", file=sys.stderr)
        return 1

    diagnosis = diagnose(organism)
    print(diagnosis.format_report())
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    """Execute the 'snapshot' command — generate a static snapshot."""
    path = os.path.abspath(getattr(args, "path", "."))
    if not os.path.isdir(path):
        print(f"Error: {path} is not a directory", file=sys.stderr)
        return 1

    engine = MetricsEngine(path, getattr(args, "since", None))
    project = engine.scan()
    health_states = _load_health_states(args)
    ecosystem = build_ecosystem(project, health_states)

    output = getattr(args, "output", None)
    fmt = getattr(args, "format", "text")

    if output:
        export_snapshot(ecosystem, output, format=fmt)
        print(f"Snapshot exported to {output}")
    else:
        if fmt == "svg":
            from .renderers.static_export import render_svg_snapshot

            print(render_svg_snapshot(ecosystem))
        else:
            print(render_text_snapshot(ecosystem))

    return 0


def cmd_seasons(args: argparse.Namespace) -> int:
    """Execute the 'seasons' command — seasonal timeline view."""
    path = os.path.abspath(getattr(args, "path", "."))
    if not os.path.isdir(path):
        print(f"Error: {path} is not a directory", file=sys.stderr)
        return 1

    since = getattr(args, "since", None)
    output = render_seasons_from_project(path, since)
    print(output)
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    """Execute the 'health' command — compact health report."""
    path = os.path.abspath(getattr(args, "path", "."))
    if not os.path.isdir(path):
        print(f"Error: {path} is not a directory", file=sys.stderr)
        return 1

    engine = MetricsEngine(path, getattr(args, "since", None))
    project = engine.scan()
    health_states = _load_health_states(args)
    ecosystem = build_ecosystem(project, health_states)

    print(render_health_summary(ecosystem))

    most_critical = ecosystem.most_critical()
    healthiest = ecosystem.healthiest()

    if most_critical:
        print(
            f"  Most critical: {most_critical.path} (health: {most_critical.health:.0f}/100)"
        )
    if healthiest:
        print(f"  Healthiest: {healthiest.path} (health: {healthiest.health:.0f}/100)")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    command = getattr(args, "command", None)
    if command is None:
        parser.print_help()
        return 0

    commands = {
        "watch": cmd_watch,
        "diagnose": cmd_diagnose,
        "snapshot": cmd_snapshot,
        "seasons": cmd_seasons,
        "health": cmd_health,
    }

    handler = commands.get(command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
