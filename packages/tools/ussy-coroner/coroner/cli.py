"""CLI interface for Coroner — Forensic Trace Evidence Analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from coroner import __version__
from coroner.db import ForensicDB
from coroner.scanner import ingest_json, scan_directory
from coroner.traces import analyze_traces, format_traces
from coroner.spatter import analyze_spatter, format_spatter
from coroner.striation import analyze_striations, format_striation
from coroner.luminol import analyze_luminol, format_luminol
from coroner.custody import analyze_custody, format_custody
from coroner.investigate import investigate
from coroner.report import generate_report


def _load_run(run_id: str, db_path: str | None) -> Any:
    """Load a pipeline run from database or scan as directory."""
    from coroner.models import PipelineRun

    if db_path:
        db = ForensicDB(db_path)
        run = db.load_run(run_id)
        db.close()
        if run:
            return run

    # Try as directory
    dir_path = Path(run_id)
    if dir_path.is_dir():
        return scan_directory(dir_path)

    # Try as JSON file
    json_path = Path(run_id)
    if json_path.exists() and json_path.suffix == ".json":
        return ingest_json(json_path)

    # If nothing works, create a minimal run for testing
    print(f"Warning: Could not find run '{run_id}', using empty run.", file=sys.stderr)
    return PipelineRun(run_id=run_id)


def cmd_traces(args: argparse.Namespace) -> None:
    """Run trace evidence analysis."""
    run = _load_run(args.run_id, getattr(args, "db", None))
    bidirectional = getattr(args, "bidirectional", False)
    result = analyze_traces(run, bidirectional=bidirectional)
    print(format_traces(result, bidirectional=bidirectional))


def cmd_spatter(args: argparse.Namespace) -> None:
    """Run error spatter reconstruction."""
    run = _load_run(args.run_id, getattr(args, "db", None))
    result = analyze_spatter(run)
    print(format_spatter(result))


def cmd_striation(args: argparse.Namespace) -> None:
    """Run striation matching."""
    run = _load_run(args.run_id, getattr(args, "db", None))
    compare_last = getattr(args, "compare_last", 0)

    # Try to load comparison runs
    compare_runs: list[Any] = []
    if compare_last > 0 and getattr(args, "db", None):
        db = ForensicDB(args.db)
        run_ids = db.list_runs()
        for rid in run_ids[:compare_last]:
            if rid != args.run_id:
                r = db.load_run(rid)
                if r:
                    compare_runs.append(r)
        db.close()

    matches = analyze_striations(run, compare_runs) if compare_runs else []
    print(format_striation(matches))


def cmd_luminol(args: argparse.Namespace) -> None:
    """Run luminol scan for hidden state detection."""
    run = _load_run(args.run_id, getattr(args, "db", None))
    report = analyze_luminol(run)
    print(format_luminol(report))


def cmd_custody(args: argparse.Namespace) -> None:
    """Run chain of custody analysis."""
    run = _load_run(args.run_id, getattr(args, "db", None))
    compare_id = getattr(args, "compare", None)
    compare_run = None
    if compare_id:
        compare_run = _load_run(compare_id, getattr(args, "db", None))

    chain, comparison = analyze_custody(run, compare_run)
    print(format_custody(chain, comparison))


def cmd_investigate(args: argparse.Namespace) -> None:
    """Run full forensic investigation."""
    run = _load_run(args.run_id, getattr(args, "db", None))

    # Load comparison runs if available
    compare_runs: list[Any] = []
    compare_last = getattr(args, "compare_last", 0)
    if compare_last > 0 and getattr(args, "db", None):
        db = ForensicDB(args.db)
        run_ids = db.list_runs()
        for rid in run_ids[:compare_last]:
            if rid != args.run_id:
                r = db.load_run(rid)
                if r:
                    compare_runs.append(r)
        db.close()

    bidirectional = getattr(args, "bidirectional", True)
    inv = investigate(run, compare_runs=compare_runs or None, bidirectional=bidirectional)
    print(generate_report(inv))


def cmd_report(args: argparse.Namespace) -> None:
    """Generate full autopsy report (same as investigate but with explicit report output)."""
    cmd_investigate(args)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="coroner",
        description="Coroner — Forensic Trace Evidence Analysis for CI/CD Pipeline Failure Diagnosis",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--db", help="Path to SQLite database file")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # investigate
    p_inv = subparsers.add_parser("investigate", help="Full forensic investigation")
    p_inv.add_argument("run_id", help="Pipeline run ID or directory path")
    p_inv.add_argument("--bidirectional", action="store_true", default=True, help="Check reverse traces")
    p_inv.add_argument("--compare-last", type=int, default=0, help="Compare with last N runs")

    # traces
    p_tr = subparsers.add_parser("traces", help="Trace evidence analysis")
    p_tr.add_argument("run_id", help="Pipeline run ID or directory path")
    p_tr.add_argument("--bidirectional", action="store_true", help="Check reverse traces")

    # spatter
    p_sp = subparsers.add_parser("spatter", help="Error origin reconstruction")
    p_sp.add_argument("run_id", help="Pipeline run ID or directory path")

    # striation
    p_st = subparsers.add_parser("striation", help="Cross-build error matching")
    p_st.add_argument("run_id", help="Pipeline run ID or directory path")
    p_st.add_argument("--compare-last", type=int, default=0, help="Compare with last N builds")

    # luminol
    p_lu = subparsers.add_parser("luminol", help="Hidden state detection")
    p_lu.add_argument("run_id", help="Pipeline run ID or directory path")

    # custody
    p_cu = subparsers.add_parser("custody", help="Artifact provenance")
    p_cu.add_argument("run_id", help="Pipeline run ID or directory path")
    p_cu.add_argument("--compare", help="Second run ID for comparison")

    # report
    p_rp = subparsers.add_parser("report", help="Generate full autopsy report")
    p_rp.add_argument("run_id", help="Pipeline run ID or directory path")
    p_rp.add_argument("--compare-last", type=int, default=0, help="Compare with last N runs")

    return parser


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    command = getattr(args, "command", None)
    if not command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "investigate": cmd_investigate,
        "traces": cmd_traces,
        "spatter": cmd_spatter,
        "striation": cmd_striation,
        "luminol": cmd_luminol,
        "custody": cmd_custody,
        "report": cmd_report,
    }

    handler = commands.get(command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
