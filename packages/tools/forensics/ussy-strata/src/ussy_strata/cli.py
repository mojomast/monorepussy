"""Unified CLI dispatcher for ussy-strata with subcommands."""

from __future__ import annotations

import argparse
import sys

from ussy_strata.survey_cli import main as survey_main
from ussy_strata.missing import missing_cli
from ussy_strata.timeline import timeline_main


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point for ussy-strata."""
    parser = argparse.ArgumentParser(
        prog="ussy-strata",
        description="ussy-strata — Git forensics with geological metaphors",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # survey subcommand (stratagit)
    survey_parser = subparsers.add_parser(
        "survey",
        help="Generate a geological survey report of the repository",
    )
    survey_parser.add_argument("-C", "--repo", default=".")
    survey_parser.add_argument("-n", "--max-commits", type=int, default=0)
    survey_parser.add_argument("--no-color", action="store_true")
    survey_parser.add_argument("--no-fossils", action="store_true")
    survey_parser.add_argument("--no-unconformities", action="store_true")
    survey_parser.add_argument("--no-faults", action="store_true")

    # missing subcommand (unconformity)
    missing_parser = subparsers.add_parser(
        "missing",
        help="Git forensics for what's MISSING",
    )
    missing_parser.add_argument("repo_path")
    missing_parser.add_argument("--types", "-t", action="append")
    missing_parser.add_argument("--severity", "-s")
    missing_parser.add_argument("--since", "-S")
    missing_parser.add_argument("--until", "-U")
    missing_parser.add_argument("--branch", "-b")
    missing_parser.add_argument("--json", action="store_true")
    missing_parser.add_argument("--verbose", "-v", action="store_true")

    # timeline subcommand (combined)
    timeline_parser = subparsers.add_parser(
        "timeline",
        help="Combined geological + missing-history timeline",
    )
    timeline_parser.add_argument("-C", "--repo", default=".")
    timeline_parser.add_argument("-w", "--width", type=int, default=80)
    timeline_parser.add_argument("--no-color", action="store_true")

    # Handle no subcommand — default to survey
    if not argv or argv[0].startswith("-"):
        argv = ["survey"] + list(argv or [])
    elif argv[0] not in ("survey", "missing", "timeline"):
        argv = ["survey"] + list(argv)

    args = parser.parse_args(argv)

    if args.command == "survey":
        return survey_main(["-C", args.repo, "-n", str(args.max_commits)])
    elif args.command == "missing":
        return missing_cli(["scan", args.repo_path])
    elif args.command == "timeline":
        return timeline_main(["-C", args.repo, "-w", str(args.width)])
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
