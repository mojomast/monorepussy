"""Triage CLI — Error Logs as Crime Scenes.

Usage:
    # Pipe any command's output through triage
    cargo build 2>&1 | triage

    # Analyze a saved log file
    triage analyze build-log.txt

    # Quick mode — just the fix
    npm run build 2>&1 | triage --quick

    # Teaching mode — extended explanations
    triage analyze error.log --teach

    # JSON output
    triage analyze error.log --json

    # Add a project-specific error pattern
    triage pattern add --regex "CustomError: (.*)" --cause "Our custom error" --fix "Check the config"

    # List known patterns
    triage pattern list [--language python]

    # Show version
    triage --version
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Optional

from . import __version__
from .extractor import ErrorExtractor, IsolatedError
from .patterns import PatternMatcher
from .enricher import ContextEnricher
from .renderer import DiagnosisRenderer
from .models import EnrichedError, Diagnosis


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="triage",
        description="Triage — Error Logs as Crime Scenes. "
                    "Analyzes build failures, stack traces, and error logs "
                    "using forensic methodology to produce detective-style diagnostic reports.",
    )
    parser.add_argument(
        "--version", action="version", version=f"triage {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze command (default when piping)
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze an error log file or stdin"
    )
    analyze_parser.add_argument(
        "file", nargs="?", help="Log file to analyze (reads stdin if not specified)"
    )
    analyze_parser.add_argument(
        "--quick", "-q", action="store_true",
        help="Minimal output — just the fix suggestion"
    )
    analyze_parser.add_argument(
        "--json", "-j", action="store_true",
        help="Output as structured JSON"
    )
    analyze_parser.add_argument(
        "--teach", "-t", action="store_true",
        help="Teaching mode — extended explanations for learning"
    )
    analyze_parser.add_argument(
        "--project", "-p", type=str, default=".",
        help="Project directory for git context (default: current directory)"
    )

    # pattern command
    pattern_parser = subparsers.add_parser(
        "pattern", help="Manage error patterns"
    )
    pattern_sub = pattern_parser.add_subparsers(dest="pattern_command")

    # pattern add
    add_parser = pattern_sub.add_parser("add", help="Add a custom error pattern")
    add_parser.add_argument("--regex", "-r", required=True, help="Regex pattern to match")
    add_parser.add_argument("--cause", "-c", required=True, help="Root cause description")
    add_parser.add_argument("--fix", "-f", required=True, help="Fix template")
    add_parser.add_argument("--type", "-t", default="custom", help="Error type (default: custom)")
    add_parser.add_argument("--language", "-l", default=None, help="Programming language")
    add_parser.add_argument("--confidence", type=float, default=0.7, help="Confidence score 0-1")

    # pattern list
    list_parser = pattern_sub.add_parser("list", help="List known error patterns")
    list_parser.add_argument("--language", "-l", default=None, help="Filter by language")
    list_parser.add_argument("--type", "-t", default=None, help="Filter by error type")
    list_parser.add_argument("--count", action="store_true", help="Show pattern count only")

    # pattern remove
    remove_parser = pattern_sub.add_parser("remove", help="Remove a custom pattern")
    remove_parser.add_argument("id", type=int, help="Pattern ID to remove")

    return parser


def read_input(file_path: Optional[str] = None) -> str:
    """Read input from a file or stdin."""
    if file_path:
        path = Path(file_path)
        if not path.exists():
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        return path.read_text(encoding="utf-8", errors="replace")
    else:
        # Read from stdin (pipe)
        try:
            if sys.stdin.isatty():
                print("Error: No input provided. Pipe output or specify a file.", file=sys.stderr)
                print("Usage: cargo build 2>&1 | triage", file=sys.stderr)
                print("       triage analyze build-log.txt", file=sys.stderr)
                sys.exit(1)
            return sys.stdin.read()
        except OSError:
            sys.exit(1)


def get_output_format(args) -> str:
    """Determine the output format from CLI args."""
    if getattr(args, 'json', False):
        return "json"
    elif getattr(args, 'quick', False):
        return "minimal"
    elif getattr(args, 'teach', False):
        return "teaching"
    return "detective"


def cmd_analyze(args) -> int:
    """Handle the analyze command."""
    text = read_input(args.file)
    if not text.strip():
        print("No input to analyze.", file=sys.stderr)
        return 1

    # Set up the pipeline
    extractor = ErrorExtractor()
    matcher = PatternMatcher()
    enricher = ContextEnricher(
        project_dir=args.project,
        pattern_matcher=matcher,
    )
    renderer = DiagnosisRenderer()

    # Run the pipeline
    errors = extractor.extract_from_text(text)
    if not errors:
        print(f"🔍 No errors found — the scene is clean.")
        return 0

    # Deduplicate
    errors = extractor.deduplicate(errors)

    # Enrich
    enriched = enricher.enrich_all(errors)

    # Diagnose
    diagnoses = renderer.diagnose_all(enriched)

    # Render
    output_format = get_output_format(args)
    output = renderer.render_all(diagnoses, format=output_format)
    print(output)

    return 1 if errors else 0  # Exit 1 if errors found, 0 if clean


def cmd_pattern(args) -> int:
    """Handle the pattern command."""
    matcher = PatternMatcher()

    if args.pattern_command == "add":
        try:
            pid = matcher.add_pattern(
                pattern_type=args.type,
                language=args.language,
                regex=args.regex,
                root_cause=args.cause,
                fix_template=args.fix,
                confidence=args.confidence,
            )
            print(f"✅ Pattern added with ID: {pid}")
            return 0
        except ValueError as e:
            print(f"❌ Error: {e}", file=sys.stderr)
            return 1

    elif args.pattern_command == "list":
        if args.count:
            total = matcher.pattern_count()
            print(f"Total patterns: {total}")
            return 0

        patterns = matcher.list_patterns(
            pattern_type=args.type,
            language=args.language,
        )
        if not patterns:
            print("No patterns found.")
            return 0

        print(f"{'ID':>4}  {'Type':<20} {'Lang':<12} {'Conf':>5}  {'Regex'}")
        print("-" * 80)
        for p in patterns:
            print(f"{p['id']:>4}  {p['pattern_type']:<20} "
                  f"{(p['language'] or '*'):<12} {p['confidence']:>5.2f}  "
                  f"{p['pattern_regex'][:40]}")
        return 0

    elif args.pattern_command == "remove":
        if matcher.remove_pattern(args.id):
            print(f"✅ Pattern {args.id} removed.")
            return 0
        else:
            print(f"❌ Pattern {args.id} not found or not a custom pattern.", file=sys.stderr)
            return 1

    else:
        print("Unknown pattern subcommand. Use: add, list, remove", file=sys.stderr)
        return 1


def main(argv: List[str] = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return cmd_analyze(args)
    elif args.command == "pattern":
        return cmd_pattern(args)
    else:
        # No command specified — if stdin has data, analyze it
        if not sys.stdin.isatty():
            # Create minimal args for stdin analysis
            args.file = None
            args.project = "."
            args.quick = False
            args.json = False
            args.teach = False
            return cmd_analyze(args)
        else:
            parser.print_help()
            return 0


if __name__ == "__main__":
    sys.exit(main())
