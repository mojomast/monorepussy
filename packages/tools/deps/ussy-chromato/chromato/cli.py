"""CLI interface for Chromato — chromatographic dependency separation tool."""

from __future__ import annotations

import argparse
import sys

from chromato.engine import compute_max_risk, run_diff, run_scan
from chromato.models import Solvent
from chromato.renderer import render_chromatogram, render_diff, render_json


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="chromato",
        description="Chromato — Chromatographic Dependency Separation & Profiling",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan subcommand
    scan_parser = subparsers.add_parser(
        "scan",
        help="Generate full chromatogram from dependency file",
    )
    scan_parser.add_argument(
        "source",
        help="Path to dependency file or directory",
    )
    scan_parser.add_argument(
        "--format",
        choices=["chromatogram", "json"],
        default="chromatogram",
        help="Output format (default: chromatogram)",
    )
    scan_parser.add_argument(
        "--solvent",
        choices=[s.value for s in Solvent],
        default="coupling",
        help="Analysis solvent mode (default: coupling)",
    )
    scan_parser.add_argument(
        "--exit-on-risk",
        type=float,
        default=None,
        help="Exit with code 1 if max risk score exceeds this threshold",
    )

    # diff subcommand
    diff_parser = subparsers.add_parser(
        "diff",
        help="Compare two dependency files (differential chromatography)",
    )
    diff_parser.add_argument(
        "source_a",
        help="Path to original dependency file or directory",
    )
    diff_parser.add_argument(
        "source_b",
        help="Path to new dependency file or directory",
    )
    diff_parser.add_argument(
        "--solvent",
        choices=[s.value for s in Solvent],
        default="coupling",
        help="Analysis solvent mode (default: coupling)",
    )

    # coelute subcommand
    coelute_parser = subparsers.add_parser(
        "coelute",
        help="Detect co-elutions (entangled dependencies)",
    )
    coelute_parser.add_argument(
        "source",
        help="Path to dependency file or directory",
    )
    coelute_parser.add_argument(
        "--threshold",
        type=float,
        default=0.3,
        help="Co-elution overlap threshold (default: 0.3)",
    )
    coelute_parser.add_argument(
        "--solvent",
        choices=[s.value for s in Solvent],
        default="coupling",
        help="Analysis solvent mode (default: coupling)",
    )

    # peaks subcommand
    peaks_parser = subparsers.add_parser(
        "peaks",
        help="Profile peak shapes (dependency health check)",
    )
    peaks_parser.add_argument(
        "source",
        help="Path to dependency file or directory",
    )
    peaks_parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Show detailed diagnosis for each peak",
    )
    peaks_parser.add_argument(
        "--solvent",
        choices=[s.value for s in Solvent],
        default="coupling",
        help="Analysis solvent mode (default: coupling)",
    )

    return parser


def cmd_scan(args: argparse.Namespace) -> int:
    """Handle the 'scan' command."""
    solvent = Solvent(args.solvent)
    result = run_scan(args.source, solvent)

    if args.format == "json":
        output = render_json(result)
    else:
        output = render_chromatogram(result)

    print(output)

    # Check risk threshold
    if args.exit_on_risk is not None:
        max_risk = compute_max_risk(result)
        if max_risk > args.exit_on_risk:
            print(f"\n⚠ Max risk score ({max_risk:.2f}) exceeds threshold ({args.exit_on_risk})", file=sys.stderr)
            return 1

    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    """Handle the 'diff' command."""
    solvent = Solvent(args.solvent)
    result_a, result_b = run_diff(args.source_a, args.source_b, solvent)
    output = render_diff(result_a, result_b)
    print(output)
    return 0


def cmd_coelute(args: argparse.Namespace) -> int:
    """Handle the 'coelute' command."""
    solvent = Solvent(args.solvent)
    result = run_scan(args.source, solvent, args.threshold)

    if result.coelutions:
        print("CO-ELUTION DETECTION RESULTS")
        print("=" * 50)
        for ce in result.coelutions:
            print(
                f"  ⚠ {ce.dep_a.name} + {ce.dep_b.name} "
                f"(overlap={ce.overlap:.2f}, kind={ce.kind.value})"
            )
    else:
        print("No co-elutions detected. Dependencies are well-separated.")

    # Also show full result as JSON for programmatic use
    print()
    print(render_json(result))

    return 0


def cmd_peaks(args: argparse.Namespace) -> int:
    """Handle the 'peaks' command."""
    solvent = Solvent(args.solvent)
    result = run_scan(args.source, solvent)

    print("PEAK SHAPE PROFILING")
    print("=" * 60)

    for peak in result.peaks:
        shape_label = {
            "narrow_tall": "████ focused",
            "wide_short": "██░░░░ bloated",
            "shoulder": "██▓░░ transition",
            "tailing": "██░░▓ dragging",
            "symmetric": "████ normal",
        }.get(peak.shape.value, "████ unknown")

        print(f"  {peak.dep.name:<25} RT={peak.retention_time:<6.1f} "
              f"Area={peak.area:<5.2f} Width={peak.width:<5.2f} "
              f"Shape={shape_label}")

        if args.diagnose:
            if peak.shape.value == "wide_short":
                concerns = peak.dep.concerns
                print(f"    → ⚠ {concerns} concerns detected: dependency is bloated")
            elif peak.shape.value == "shoulder":
                print(f"    → ↗ Major version gap: dependency is in transition")
            elif peak.shape.value == "tailing":
                print(f"    → ⚠ Deprecated APIs: backward compat burden")
            elif peak.shape.value == "narrow_tall":
                print(f"    → ✓ Focused and popular: healthy dependency")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.command == "scan":
            return cmd_scan(args)
        elif args.command == "diff":
            return cmd_diff(args)
        elif args.command == "coelute":
            return cmd_coelute(args)
        elif args.command == "peaks":
            return cmd_peaks(args)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
