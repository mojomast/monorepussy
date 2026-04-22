"""StrataGit CLI — command-line interface for geological git analysis."""

from __future__ import annotations

import argparse
import sys
import os

from ussy_strata.core.parser import (
    is_git_repo,
    parse_commits,
    assign_branch_names,
    compute_stability,
    classify_intrusions,
)
from ussy_strata.core.survey import survey, format_report
from ussy_strata.core.fossils import excavate_fossils
from ussy_strata.core.unconformity import detect_unconformities
from ussy_strata.core.fault import detect_faults
from ussy_strata.core.carbon_date import carbon_date
from ussy_strata.tui import render_cross_section, render_legend, render_stratum_detail


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ussy-strata",
        description="ussy-strata — Geological metaphor for Git history visualization",
    )
    parser.add_argument(
        "-C",
        "--repo",
        default=".",
        help="Path to the git repository (default: current directory)",
    )
    parser.add_argument(
        "-n",
        "--max-commits",
        type=int,
        default=0,
        help="Maximum number of commits to analyze (0 = all)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # survey
    survey_parser = subparsers.add_parser(
        "survey",
        help="Generate a geological survey report of the repository",
    )
    survey_parser.add_argument(
        "--no-fossils",
        action="store_true",
        help="Skip fossil (deleted code) analysis",
    )
    survey_parser.add_argument(
        "--no-unconformities",
        action="store_true",
        help="Skip unconformity (history gap) detection",
    )
    survey_parser.add_argument(
        "--no-faults",
        action="store_true",
        help="Skip fault line (force push) detection",
    )

    # cross-section
    cs_parser = subparsers.add_parser(
        "cross-section",
        help="Display a geological cross-section view of git history",
    )
    cs_parser.add_argument(
        "-w",
        "--width",
        type=int,
        default=80,
        help="Terminal width for the cross-section (default: 80)",
    )

    # excavate (fossils)
    excavate_parser = subparsers.add_parser(
        "excavate",
        help="Find fossils (deleted code artifacts) in git history",
    )
    excavate_parser.add_argument(
        "-p",
        "--pattern",
        default="",
        help="Regex pattern to filter fossil names",
    )
    excavate_parser.add_argument(
        "-g",
        "--glob",
        default="",
        help="File glob to limit search scope",
    )

    # unconformities
    subparsers.add_parser(
        "unconformities",
        help="Detect unconformities (history gaps) in the repository",
    )

    # faults
    subparsers.add_parser(
        "faults",
        help="Detect fault lines (history rewrites) in the repository",
    )

    # carbon-date
    cd_parser = subparsers.add_parser(
        "carbon-date",
        help="Carbon date a specific line in a file (enhanced blame)",
    )
    cd_parser.add_argument(
        "file",
        help="Path to the file (relative to repo root)",
    )
    cd_parser.add_argument(
        "line",
        type=int,
        help="Line number to carbon date (1-indexed)",
    )

    # legend
    subparsers.add_parser(
        "legend",
        help="Show the mineral color legend",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    repo_path = os.path.abspath(args.repo)
    use_color = not args.no_color

    # Handle no subcommand — default to survey
    if args.command is None:
        args.command = "survey"
        # Add default survey attributes if missing
        if not hasattr(args, "no_fossils"):
            args.no_fossils = False
        if not hasattr(args, "no_unconformities"):
            args.no_unconformities = False
        if not hasattr(args, "no_faults"):
            args.no_faults = False

    # Validate repo path for commands that need it
    needs_repo = args.command not in ("legend",)
    if needs_repo and not is_git_repo(repo_path):
        print(f"Error: {repo_path} is not a git repository", file=sys.stderr)
        return 1

    if args.command == "survey":
        report = survey(
            repo_path,
            max_commits=args.max_commits,
            include_fossils=not getattr(args, "no_fossils", False),
            include_unconformities=not getattr(args, "no_unconformities", False),
            include_faults=not getattr(args, "no_faults", False),
        )
        output = format_report(report)
        if not use_color:
            # Strip ANSI codes
            import re

            output = re.sub(r"\033\[[0-9;]*m", "", output)
        print(output)

    elif args.command == "cross-section":
        strata = parse_commits(repo_path, max_count=args.max_commits)
        if not strata:
            print("No commits found in repository.", file=sys.stderr)
            return 1
        strata = assign_branch_names(strata, repo_path)
        strata = compute_stability(strata)
        output = render_cross_section(strata, width=args.width, use_color=use_color)
        print(output)

    elif args.command == "excavate":
        fossils = excavate_fossils(
            repo_path,
            pattern=args.pattern,
            file_glob=args.glob,
            max_commits=args.max_commits,
        )
        if not fossils:
            print("No fossils found in this repository.")
            return 0
        print(f"FOSSILS ({len(fossils)} found)")
        print("-" * 60)
        for fossil in fossils:
            lifespan = ""
            if fossil.is_extinct and fossil.lifespan_days >= 0:
                lifespan = f" (lived {fossil.lifespan_days:.0f} days)"
            print(f"  {fossil.kind:8s} {fossil.name:30s} in {fossil.file_path}{lifespan}")
            if fossil.content:
                print(f"           {fossil.content[:70]}")

    elif args.command == "unconformities":
        unconformities = detect_unconformities(repo_path, max_commits=args.max_commits)
        if not unconformities:
            print("No unconformities detected.")
            return 0
        print(f"UNCONFORMITIES ({len(unconformities)} found)")
        print("-" * 60)
        for u in unconformities:
            date_str = u.date.isoformat() if u.date else "unknown date"
            print(f"  [{u.unconformity_type.value:12s}] {u.severity:8s} — {u.description[:50]}")
            print(f"    Date: {date_str}  Confidence: {u.confidence:.0%}")

    elif args.command == "faults":
        faults = detect_faults(repo_path)
        if not faults:
            print("No fault lines detected.")
            return 0
        print(f"FAULT LINES ({len(faults)} found)")
        print("-" * 60)
        for f in faults:
            date_str = f.date.isoformat() if f.date else "unknown date"
            print(f"  [{f.severity_label:12s}] {f.description[:50]}")
            print(f"    Ref: {f.ref_name}  Date: {date_str}")

    elif args.command == "carbon-date":
        result = carbon_date(repo_path, args.file, args.line)
        print(f"CARBON DATING: {result['file']}:{result['line_number']}")
        print("-" * 60)
        print(f"  Current content: {result['current_content']}")
        print(f"  Deposited by:    {result['deposited_author']}")
        if result["deposited_date"]:
            print(f"  Deposited on:    {result['deposited_date'].isoformat()}")
        print(f"  Age:             {result['age_days']:.1f} days")
        print(f"  Stability:       {result['stability']}")
        if result["history"]:
            print(f"  History entries: {len(result['history'])}")

    elif args.command == "legend":
        output = render_legend(use_color=use_color)
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
