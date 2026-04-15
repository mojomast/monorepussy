"""CLI interface for Assay — metallurgical code grading."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from assay import __version__
from assay.grade import grade_project, grade_module, compute_trends, grade_label
from assay.compose import compose_function, compose_module, compose_bar
from assay.alloy import detect_alloys, find_pure_functions, analyze_project_alloys
from assay.crucible import build_crucible, crucible_rank_emoji
from assay.slag import detect_slag_in_project, detect_slag_in_source, grade_improvement_estimate
from assay.storage import save_analysis, load_latest_run
from assay.formatter import (
    format_grade_report,
    format_compose_report,
    format_alloy_report,
    format_crucible_report,
    format_slag_report,
)
from assay.scanner import _resolve_paths


def _cmd_grade(args: argparse.Namespace) -> None:
    """Run grade report."""
    path = args.path
    project = grade_project(path)

    if not project.modules:
        print(f"No Python files found in: {path}")
        return

    # Try loading previous run for trends
    path_obj = Path(path)
    project_dir = str(path_obj if path_obj.is_dir() else path_obj.parent)
    previous = load_latest_run(project_dir)
    trends = compute_trends(project, previous)

    print(format_grade_report(project, trends))

    # Save this run
    if project_dir:
        save_analysis(project, project_dir)


def _cmd_compose(args: argparse.Namespace) -> None:
    """Run composition analysis."""
    path = args.path
    paths = _resolve_paths(path)

    if not paths:
        print(f"No Python files found in: {path}")
        return

    for fpath in paths:
        results = compose_module(fpath)
        for r in results:
            print(format_compose_report(r["name"], r["composition"]))
            # Add suggestions if slag detected
            comp = r["composition"]
            slag_info = []
            if "slag" in comp:
                slag_info.append(f"Slag: {comp['slag']['lines']} lines")
            if slag_info:
                print("  " + ", ".join(slag_info))
            print()


def _cmd_alloy(args: argparse.Namespace) -> None:
    """Run alloy detection."""
    path = args.path
    project = grade_project(path)

    if not project.modules:
        print(f"No Python files found in: {path}")
        return

    result = analyze_project_alloys(project)
    print(format_alloy_report(result["alloyed"], result["pure"]))


def _cmd_crucible(args: argparse.Namespace) -> None:
    """Run crucible map."""
    path = args.path
    project = grade_project(path)

    if not project.modules:
        print(f"No Python files found in: {path}")
        return

    crucible = build_crucible(project)
    print(format_crucible_report(crucible))


def _cmd_slag(args: argparse.Namespace) -> None:
    """Run slag report."""
    path = args.path
    report = detect_slag_in_project(path)

    if report.total_lines == 0:
        print("No slag detected.")
        return

    print(format_slag_report(report))

    # Estimate grade improvement
    project = grade_project(path)
    if project.total_lines > 0:
        improved = grade_improvement_estimate(
            project.grade, project.total_lines, report.total_lines
        )
        print(f"Potential grade improvement: {project.grade:.0f}% \u2192 {improved:.0f}% (slag removal only)")


def _cmd_watch(args: argparse.Namespace) -> None:
    """Watch for file changes (basic polling implementation)."""
    import time

    path = args.path
    interval = getattr(args, "interval", 5)

    print(f"Watching {path} for changes (interval: {interval}s)...")
    print("Press Ctrl+C to stop.")

    last_mtime: dict[str, float] = {}

    try:
        while True:
            paths = _resolve_paths(path)
            changed = False
            for fpath in paths:
                try:
                    mtime = fpath.stat().st_mtime
                    key = str(fpath)
                    if key in last_mtime and mtime > last_mtime[key]:
                        print(f"\n[CHANGE] {fpath}")
                        mod = grade_module(fpath)
                        for func in mod.functions:
                            print(
                                f"  {func.name}(): {func.grade:.0f}% grade "
                                f"({func.total_lines} lines)"
                            )
                        changed = True
                    last_mtime[key] = mtime
                except OSError:
                    pass

            if not changed:
                sys.stdout.write(".")
                sys.stdout.flush()

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped watching.")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="assay",
        description="Assay — Metallurgical Code Grading: Separate precious logic from slag",
    )
    parser.add_argument(
        "--version", action="version", version=f"assay {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # grade
    grade_parser = subparsers.add_parser("grade", help="Grade report — measure precious logic percentage")
    grade_parser.add_argument("path", help="File or directory to analyze")

    # compose
    compose_parser = subparsers.add_parser("compose", help="Composition breakdown per function")
    compose_parser.add_argument("path", help="File or directory to analyze")

    # alloy
    alloy_parser = subparsers.add_parser("alloy", help="Detect mixed-concern functions")
    alloy_parser.add_argument("path", help="File or directory to analyze")

    # crucible
    crucible_parser = subparsers.add_parser("crucible", help="Locate most valuable code")
    crucible_parser.add_argument("path", help="File or directory to analyze")

    # slag
    slag_parser = subparsers.add_parser("slag", help="Identify removable waste")
    slag_parser.add_argument("path", help="File or directory to analyze")

    # watch
    watch_parser = subparsers.add_parser("watch", help="Continuous monitoring")
    watch_parser.add_argument("path", help="File or directory to watch")
    watch_parser.add_argument(
        "--interval", type=int, default=5, help="Polling interval in seconds"
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    command = getattr(args, "command", None)
    if command is None:
        parser.print_help()
        return

    dispatch = {
        "grade": _cmd_grade,
        "compose": _cmd_compose,
        "alloy": _cmd_alloy,
        "crucible": _cmd_crucible,
        "slag": _cmd_slag,
        "watch": _cmd_watch,
    }

    handler = dispatch.get(command)
    if handler:
        handler(args)
    else:
        parser.print_help()
