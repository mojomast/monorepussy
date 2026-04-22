"""Command-line interface for Syntrop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from ussy_syntrop import __version__
from ussy_syntrop.ir import DiffResult, ProbeResult, ScanResult
from ussy_syntrop.probes import PROBE_REGISTRY
from ussy_syntrop.runner import diff_probes, probe_file, run_all_probes, run_probe, scan_directory


def _try_rich() -> bool:
    """Check if Rich is available for pretty output."""
    try:
        import rich  # noqa: F401
        return True
    except ImportError:
        return False


def _format_probe_result(result: ProbeResult, use_rich: bool = False) -> str:
    """Format a single probe result for display."""
    if use_rich:
        return _format_probe_result_rich(result)

    status = "DIVERGED" if result.diverged else "OK"
    severity = f" [{result.severity}]" if result.diverged else ""
    lines = [
        f"  Probe: {result.probe_name}  [{status}]{severity}",
    ]
    if result.diverged:
        lines.append(f"  Type: {result.divergence_type}")
        lines.append(f"  Explanation: {result.explanation}")
        lines.append(f"  Original: {result.original_output!r}")
        lines.append(f"  Probed:   {result.probed_output!r}")
    else:
        lines.append(f"  {result.explanation}")
    return "\n".join(lines)


def _format_probe_result_rich(result: ProbeResult) -> str:
    """Format a probe result using Rich markup."""
    try:
        from rich.text import Text

        if result.diverged:
            status = "[bold red]DIVERGED[/]"
            severity = f" [{result.severity}]"
        else:
            status = "[green]OK[/]"
            severity = ""
        lines = [
            f"  Probe: {result.probe_name}  {status}{severity}",
        ]
        if result.diverged:
            lines.append(f"  Type: [yellow]{result.divergence_type}[/]")
            lines.append(f"  Explanation: {result.explanation}")
            lines.append(f"  Original: {result.original_output!r}")
            lines.append(f"  Probed:   {result.probed_output!r}")
        else:
            lines.append(f"  {result.explanation}")
        return "\n".join(lines)
    except ImportError:
        return _format_probe_result(result, use_rich=False)


def _format_scan_result(result: ScanResult, use_rich: bool = False) -> str:
    """Format a scan result for display."""
    lines = [f"File: {result.path}"]
    if result.assumptions:
        lines.append(f"  Assumptions found: {len(result.assumptions)}")
        for assumption in result.assumptions:
            kind = assumption.get("kind", "unknown")
            desc = assumption.get("description", "")
            line_num = assumption.get("line", "?")
            sev = assumption.get("severity", "info")
            snippet = assumption.get("code_snippet", "")
            lines.append(f"    [{sev}] Line {line_num}: {kind}")
            lines.append(f"      {desc}")
            if snippet:
                lines.append(f"      {snippet}")
    else:
        lines.append("  No assumptions found")

    if result.probe_results:
        lines.append(f"  Probe results: {len(result.probe_results)}")
        for pr in result.probe_results:
            lines.append(_format_probe_result(pr, use_rich))

    lines.append(f"  Summary: {result.summary}")
    return "\n".join(lines)


def _format_diff_result(result: DiffResult, use_rich: bool = False) -> str:
    """Format a diff result for display."""
    lines = [
        f"File: {result.file_path}",
        f"Modes compared: {', '.join(result.modes_compared)}",
    ]
    if result.divergences:
        lines.append(f"Divergences: {len(result.divergences)}")
        for div in result.divergences:
            probe = div.get("probe", "unknown")
            dtype = div.get("type", "unknown")
            explanation = div.get("explanation", "")
            severity = div.get("severity", "info")
            lines.append(f"  [{severity}] {probe}: {dtype}")
            lines.append(f"    {explanation}")
    else:
        lines.append("No divergences found")

    lines.append(f"Consistent: {'Yes' if result.consistent else 'No'}")
    lines.append(f"Summary: {result.summary}")
    return "\n".join(lines)


def cmd_probe(args: argparse.Namespace) -> int:
    """Handle the 'probe' subcommand."""
    filepath = getattr(args, "file", None)
    if not filepath:
        print("Error: --file is required for probe command", file=sys.stderr)
        return 1

    path = Path(filepath)
    if not path.exists():
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        return 1

    source = path.read_text()

    probe_names_str = getattr(args, "probes", None)
    if probe_names_str:
        probe_names = [p.strip() for p in probe_names_str.split(",")]
        # Validate probe names
        for name in probe_names:
            if name not in PROBE_REGISTRY:
                print(
                    f"Error: unknown probe '{name}'. "
                    f"Available: {', '.join(PROBE_REGISTRY.keys())}",
                    file=sys.stderr,
                )
                return 1
    else:
        probe_names = list(PROBE_REGISTRY.keys())

    func_name = getattr(args, "function", "main")
    use_rich = _try_rich()

    print(f"Syntrop: Running probes on {filepath}")
    print(f"Probes: {', '.join(probe_names)}")
    print("=" * 60)

    results = run_all_probes(source, func_name, probe_names)

    n_diverged = 0
    for result in results:
        print(_format_probe_result(result, use_rich))
        print()
        if result.diverged:
            n_diverged += 1

    print("=" * 60)
    if n_diverged:
        print(f"FOUND {n_diverged} divergence(s) across {len(results)} probe(s)")
        return 1
    else:
        print(f"All {len(results)} probe(s) passed — no divergences detected")
        return 0


def cmd_scan(args: argparse.Namespace) -> int:
    """Handle the 'scan' subcommand."""
    directory = getattr(args, "directory", ".")
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Error: directory not found: {directory}", file=sys.stderr)
        return 1

    probe_names_str = getattr(args, "probes", None)
    probe_names = None
    if probe_names_str:
        probe_names = [p.strip() for p in probe_names_str.split(",")]
        for name in probe_names:
            if name not in PROBE_REGISTRY:
                print(
                    f"Error: unknown probe '{name}'. "
                    f"Available: {', '.join(PROBE_REGISTRY.keys())}",
                    file=sys.stderr,
                )
                return 1

    use_rich = _try_rich()

    print(f"Syntrop: Scanning {directory} for behavioral assumptions")
    print("=" * 60)

    results = scan_directory(directory, probe_names)

    if not results:
        print("No Python files found in directory")
        return 0

    total_assumptions = 0
    total_divergences = 0
    for result in results:
        print(_format_scan_result(result, use_rich))
        print()
        total_assumptions += len(result.assumptions)
        total_divergences += sum(1 for r in result.probe_results if r.diverged)

    print("=" * 60)
    print(
        f"Scanned {len(results)} file(s): "
        f"{total_assumptions} assumption(s), "
        f"{total_divergences} divergence(s)"
    )
    return 1 if total_divergences else 0


def cmd_diff(args: argparse.Namespace) -> int:
    """Handle the 'diff' subcommand."""
    filepath = getattr(args, "file", None)
    if not filepath:
        print("Error: --file is required for diff command", file=sys.stderr)
        return 1

    path = Path(filepath)
    if not path.exists():
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        return 1

    source = path.read_text()

    probe_names_str = getattr(args, "probes", None)
    probe_names = None
    if probe_names_str:
        probe_names = [p.strip() for p in probe_names_str.split(",")]
        for name in probe_names:
            if name not in PROBE_REGISTRY:
                print(
                    f"Error: unknown probe '{name}'. "
                    f"Available: {', '.join(PROBE_REGISTRY.keys())}",
                    file=sys.stderr,
                )
                return 1

    func_name = getattr(args, "function", "main")
    use_rich = _try_rich()

    print(f"Syntrop: Comparing behavior across probe modes for {filepath}")
    print("=" * 60)

    result = diff_probes(source, probe_names, func_name)
    print(_format_diff_result(result, use_rich))

    print("=" * 60)
    return 1 if not result.consistent else 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="syntrop",
        description="Syntrop: Cross-language behavioral fuzzing via esolang compilation "
        "and semantic probes",
    )
    parser.add_argument(
        "--version", action="version", version=f"syntrop {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # probe subcommand
    probe_parser = subparsers.add_parser(
        "probe", help="Run semantic probes on a Python file"
    )
    probe_parser.add_argument(
        "--file", "-f", required=True, help="Python file to probe"
    )
    probe_parser.add_argument(
        "--probes",
        "-p",
        help="Comma-separated list of probes to run "
        f"(available: {', '.join(PROBE_REGISTRY.keys())})",
    )
    probe_parser.add_argument(
        "--function",
        "-F",
        default="main",
        help="Function name to test (default: main)",
    )

    # scan subcommand
    scan_parser = subparsers.add_parser(
        "scan", help="Scan a project directory for behavioral assumptions"
    )
    scan_parser.add_argument(
        "--directory",
        "-d",
        default=".",
        help="Directory to scan (default: current directory)",
    )
    scan_parser.add_argument(
        "--probes",
        "-p",
        help="Comma-separated list of probes to run",
    )

    # diff subcommand
    diff_parser = subparsers.add_parser(
        "diff", help="Compare behavior across probe modes"
    )
    diff_parser.add_argument(
        "--file", "-f", required=True, help="Python file to diff"
    )
    diff_parser.add_argument(
        "--probes",
        "-p",
        help="Comma-separated list of probes to compare",
    )
    diff_parser.add_argument(
        "--function",
        "-F",
        default="main",
        help="Function name to test (default: main)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments. If None, uses sys.argv.

    Returns:
        Exit code: 0 for success, 1 for divergences found.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    command = getattr(args, "command", None)
    if command is None:
        parser.print_help()
        return 0

    if command == "probe":
        return cmd_probe(args)
    elif command == "scan":
        return cmd_scan(args)
    elif command == "diff":
        return cmd_diff(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
