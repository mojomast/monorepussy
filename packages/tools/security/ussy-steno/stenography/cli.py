"""Stenography CLI — command-line interface for the steganographic code review tool."""

import argparse
import sys

from stenography import __version__
from stenography.engine import ScannerEngine
from stenography.formatters import get_formatter
from stenography.models import ScanResult


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="stenography",
        description="Stenography — Steganographic Code Review Tool. "
                    "Detect invisible attacks hiding in your source code.",
        epilog="Examples:\n"
               "  stenography scan ./src\n"
               "  stenography diff HEAD~1\n"
               "  stenography scan --format json ./src\n"
               "  cat suspicious.py | stenography scan -\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"stenography {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan subcommand
    scan_parser = subparsers.add_parser("scan", help="Scan files/directories for steganographic content")
    scan_parser.add_argument(
        "path", nargs="+", help="File or directory paths to scan (use '-' for stdin)"
    )
    scan_parser.add_argument(
        "--format", "-f", choices=["table", "json", "sarif"], default="table",
        help="Output format (default: table)"
    )
    scan_parser.add_argument(
        "--entropy-threshold", "-e", type=float, default=0.8,
        help="Whitespace entropy threshold (0-1, default: 0.8)"
    )
    scan_parser.add_argument(
        "--no-color", action="store_true",
        help="Disable colored output"
    )

    # diff subcommand
    diff_parser = subparsers.add_parser("diff", help="Scan only changed lines in a git diff")
    diff_parser.add_argument(
        "ref", help="Git diff reference (e.g., HEAD~1, main..feature, abc123)"
    )
    diff_parser.add_argument(
        "--format", "-f", choices=["table", "json", "sarif"], default="table",
        help="Output format (default: table)"
    )
    diff_parser.add_argument(
        "--entropy-threshold", "-e", type=float, default=0.8,
        help="Whitespace entropy threshold (0-1, default: 0.8)"
    )
    diff_parser.add_argument(
        "--no-color", action="store_true",
        help="Disable colored output"
    )

    return parser


def main(argv=None):
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    engine = ScannerEngine(entropy_threshold=getattr(args, "entropy_threshold", 0.8))

    if args.command == "scan":
        result = ScanResult()
        for path in args.path:
            if path == "-":
                result.merge(engine.scan_stdin())
            else:
                result.merge(engine.scan_path(path))

        fmt = get_formatter(args.format)
        if args.format == "table":
            output = fmt.format(result)
            if args.no_color:
                # Strip ANSI codes
                import re
                output = re.sub(r"\033\[[0-9;]*m", "", output)
        else:
            output = fmt.format(result)

        print(output)
        return 1 if result.total_findings > 0 else 0

    elif args.command == "diff":
        result = engine.scan_diff(args.ref)

        fmt = get_formatter(args.format)
        if args.format == "table":
            output = fmt.format(result)
            if args.no_color:
                import re
                output = re.sub(r"\033\[[0-9;]*m", "", output)
        else:
            output = fmt.format(result)

        print(output)
        return 1 if result.total_findings > 0 else 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
