"""Command-line interface for ChurnMap."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from .communities import detect_communities, summarize_communities
from .cochange import build_cochange_graph
from .layout import build_layout
from .mining import mine_repository
from .render import render_map


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="churnmap", description="Render a git co-change territory map"
    )
    parser.add_argument("repo_path", type=Path)
    parser.add_argument("--since")
    parser.add_argument("--until")
    parser.add_argument("--max-commits", type=int, default=1000)
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--min-cochanges", type=int, default=3)
    parser.add_argument("--format", choices=("ascii", "svg"), default="ascii")
    parser.add_argument("--output")
    parser.add_argument("--width", type=int, default=80)
    parser.add_argument("--height", type=int, default=40)
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Program entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)
    console = Console()

    try:
        progress = None
        if args.verbose:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("{task.description}"),
                TimeElapsedColumn(),
                console=console,
            )
            progress.start()
        try:
            mining_task = (
                progress.add_task("Mining repository", total=None) if progress else None
            )
            commits = mine_repository(
                args.repo_path,
                since=args.since,
                until=args.until,
                max_commits=args.max_commits,
                depth=args.depth,
            )
            if progress and mining_task is not None:
                progress.update(mining_task, completed=1, total=1)

            if not commits:
                raise ValueError("No commits found in the requested range")

            graph_task = (
                progress.add_task("Building co-change graph", total=None)
                if progress
                else None
            )
            graph = build_cochange_graph(commits, min_cochanges=args.min_cochanges)
            if progress and graph_task is not None:
                progress.update(graph_task, completed=1, total=1)

            if graph.number_of_edges() == 0:
                console.print(
                    "No significant co-change patterns found. Try lowering --min-cochanges."
                )
                return 0

            communities_task = (
                progress.add_task("Detecting communities", total=None)
                if progress
                else None
            )
            communities = detect_communities(graph)
            territory_summaries, module_summaries = summarize_communities(
                graph, communities
            )
            if progress and communities_task is not None:
                progress.update(communities_task, completed=1, total=1)

            layout_task = (
                progress.add_task("Computing layout", total=None) if progress else None
            )
            layout = build_layout(
                graph, territory_summaries, width=args.width, height=args.height
            )
            if progress and layout_task is not None:
                progress.update(layout_task, completed=1, total=1)

            output = render_map(
                layout,
                territory_summaries,
                module_summaries,
                format=args.format,
                output=args.output,
                no_color=args.no_color,
            )
        finally:
            if progress:
                progress.stop()
        if args.format == "ascii" and args.output is None:
            console.print(output)
        elif isinstance(output, Path) and args.verbose:
            console.print(f"Wrote {output}")
        return 0
    except Exception as exc:
        console.print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
