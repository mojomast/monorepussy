"""CLI interface for Petrichor — configuration drift detection through soil memory."""

import argparse
import json
import os
import sys
from pathlib import Path

from .db import SoilDB
from .export import Exporter
from .gauge import RainGauge
from .groundwater import GroundwaterDetector
from .hash import file_hash, string_hash
from .profile import SoilProfiler
from .scent import ScentDetector
from .soil import SoilMemory


def _get_db(args) -> SoilDB:
    """Get a SoilDB instance from CLI args."""
    root = getattr(args, "root", None) or os.getcwd()
    db = SoilDB(root)
    db.initialize()
    return db


def cmd_init(args):
    """Initialize soil memory for a directory."""
    target = args.path
    root = getattr(args, "root", None) or os.getcwd()

    db = SoilDB(root)
    db_path = db.initialize()

    # Add the target path(s) to tracking
    target_abs = os.path.abspath(target)
    source = args.desired_state or ""
    db.add_tracked_path(target_abs, source)

    print(f"Petrichor initialized: {db_path}")
    print(f"Tracking: {target_abs}")
    if source:
        print(f"Desired state source: {source}")


def cmd_snapshot(args):
    """Record current state as a soil layer."""
    db = _get_db(args)
    soil = SoilMemory(db)
    target = os.path.abspath(args.path)

    if os.path.isfile(target):
        paths = [target]
    elif os.path.isdir(target):
        paths = []
        for root_dir, dirs, files in os.walk(target):
            for f in files:
                paths.append(os.path.join(root_dir, f))
    else:
        print(f"Path not found: {target}", file=sys.stderr)
        return 1

    actor = args.actor or ""
    context = args.context or ""

    for p in paths:
        try:
            layer = soil.snapshot(p, actor=actor, context=context)
            status = "DRIFT" if layer.is_drift else "OK"
            print(f"  {p}: {status} (hash: {layer.content_hash[:12]}...)")
        except (OSError, PermissionError) as e:
            print(f"  {p}: SKIP ({e})", file=sys.stderr)

    return 0


def _resolve_paths(path: str, db: SoilDB) -> list:
    """Resolve a path argument to a list of file paths.
    If path is a directory, return all tracked files under it, or all files in the dir.
    If path is a file, return just that file.
    """
    if os.path.isfile(path):
        return [path]

    # Directory — find matching tracked paths or walk the directory
    tracked = db.get_tracked_paths()
    if tracked:
        # Find tracked paths that are under this directory
        matching = [t for t in tracked if t.startswith(path + "/") or t.startswith(path + os.sep)]
        if matching:
            return matching

    # Fallback: walk the directory for files
    paths = []
    for root_dir, dirs, files in os.walk(path):
        # Skip .petrichor directory
        dirs[:] = [d for d in dirs if d != ".petrichor"]
        for f in files:
            paths.append(os.path.join(root_dir, f))
    return paths


def cmd_drift(args):
    """Check for drift with full history."""
    db = _get_db(args)
    soil = SoilMemory(db)
    path = os.path.abspath(args.path)

    paths = _resolve_paths(path, db)

    if not paths:
        print(f"No tracked files found under {path}")
        print("  Run 'petrichor init' and 'petrichor snapshot' first.")
        return 0

    any_drift = False
    for p in paths:
        drift_info = soil.detect_drift(p)
        if drift_info is None:
            continue

        if drift_info["is_drift"]:
            any_drift = True
            print(f"DRIFT DETECTED: {p}")
            print(f"  Current hash:  {drift_info['current_hash'][:16]}...")
            print(f"  Desired hash:  {drift_info['desired_hash'][:16]}...")
            if drift_info.get("changed_keys"):
                print(f"  Changed keys:  {', '.join(drift_info['changed_keys'])}")
        else:
            print(f"NO DRIFT: {p} matches desired state")

        # Check for correction pattern
        correction = soil.detect_correction(p)
        if correction:
            print()
            print("⚠️ CORRECTION PATTERN DETECTED:")
            print(f"  The drift to {correction['recurring_hash'][:12]}... has recurred {correction['recurrence_count']} times.")
            print(f"  This may indicate the desired state is wrong.")
            print(f"  Suggestion: {correction['suggestion']}")

    if not any_drift:
        print(f"No drift detected in {len(paths)} tracked file(s)")

    return 0


def cmd_gauge(args):
    """Run the rain gauge (drift frequency analysis)."""
    db = _get_db(args)
    gauge = RainGauge(db)
    days = args.days or 30
    output = gauge.format_gauge(days)
    print(output)
    return 0


def cmd_groundwater(args):
    """Check groundwater (declared vs. effective vs. intended)."""
    db = _get_db(args)
    detector = GroundwaterDetector(db)
    path = getattr(args, "path", None)

    if path:
        path = os.path.abspath(path)
        output = detector.format_groundwater(path)
    else:
        output = detector.format_groundwater()

    print(output)
    return 0


def cmd_scent(args):
    """Predict future drift based on historical patterns."""
    db = _get_db(args)
    detector = ScentDetector(db)
    days = args.days or 7
    output = detector.format_predictions(days)
    print(output)
    return 0


def cmd_profile(args):
    """Get full soil profile (layered history)."""
    db = _get_db(args)
    profiler = SoilProfiler(db)
    path = os.path.abspath(args.path)
    depth = args.depth or 10

    paths = _resolve_paths(path, db)
    for p in paths:
        output = profiler.profile(p, depth)
        if output.strip():
            print(output)
    return 0


def cmd_export(args):
    """Export drift history."""
    db = _get_db(args)
    exporter = Exporter(db)
    format_type = args.format or "json"
    days = args.days or 90
    path = getattr(args, "path", None)

    if path:
        path = os.path.abspath(path)

    output = exporter.export(format=format_type, days=days, path=path)
    print(output)
    return 0


def cmd_desired(args):
    """Set the desired state for a tracked path."""
    db = _get_db(args)
    path = os.path.abspath(args.path)

    if args.from_file:
        desired_text = Path(args.from_file).read_text(encoding="utf-8")
        desired_hash = string_hash(desired_text)
        source = args.from_file
    elif args.hash:
        desired_hash = args.hash
        desired_text = ""
        source = "manual"
    else:
        print("Specify --from-file or --hash", file=sys.stderr)
        return 1

    db.set_desired_state(path, desired_hash, desired_text, source)
    db.add_tracked_path(path)
    print(f"Desired state set for {path}")
    print(f"  Hash: {desired_hash[:16]}...")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="petrichor",
        description="Configuration drift detection through soil memory",
    )
    parser.add_argument(
        "--root", "-r",
        help="Root directory for .petrichor/ database (default: current dir)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize soil memory for a directory")
    init_parser.add_argument("path", help="Directory or file to track")
    init_parser.add_argument("--desired-state", "-d", help="Source of desired state (e.g., git URL)")
    init_parser.set_defaults(func=cmd_init)

    # snapshot
    snap_parser = subparsers.add_parser("snapshot", help="Record current state as a soil layer")
    snap_parser.add_argument("path", help="File or directory to snapshot")
    snap_parser.add_argument("--actor", "-a", help="Who/what initiated the snapshot")
    snap_parser.add_argument("--context", "-c", help="Additional context for the snapshot")
    snap_parser.set_defaults(func=cmd_snapshot)

    # drift
    drift_parser = subparsers.add_parser("drift", help="Check for drift with full history")
    drift_parser.add_argument("path", help="File path to check for drift")
    drift_parser.set_defaults(func=cmd_drift)

    # gauge
    gauge_parser = subparsers.add_parser("gauge", help="Run the rain gauge (drift frequency)")
    gauge_parser.add_argument("path", nargs="?", help="Directory to analyze")
    gauge_parser.add_argument("--days", "-d", type=int, default=30, help="Analysis window in days")
    gauge_parser.set_defaults(func=cmd_gauge)

    # groundwater
    gw_parser = subparsers.add_parser("groundwater", help="Check groundwater (declared vs. effective vs. intended)")
    gw_parser.add_argument("path", nargs="?", help="Specific file path (default: all tracked)")
    gw_parser.set_defaults(func=cmd_groundwater)

    # scent
    scent_parser = subparsers.add_parser("scent", help="Predict future drift")
    scent_parser.add_argument("--days", "-d", type=int, default=7, help="Prediction window in days")
    scent_parser.set_defaults(func=cmd_scent)

    # profile
    profile_parser = subparsers.add_parser("profile", help="Get full soil profile (layered history)")
    profile_parser.add_argument("path", help="File path for soil profile")
    profile_parser.add_argument("--depth", type=int, default=10, help="Maximum number of layers")
    profile_parser.set_defaults(func=cmd_profile)

    # export
    export_parser = subparsers.add_parser("export", help="Export drift history")
    export_parser.add_argument("--format", "-f", choices=["json", "text"], default="json", help="Output format")
    export_parser.add_argument("--days", "-d", type=int, default=90, help="Export window in days")
    export_parser.add_argument("path", nargs="?", help="Specific file path (default: all)")
    export_parser.set_defaults(func=cmd_export)

    # desired
    desired_parser = subparsers.add_parser("desired", help="Set desired state for a tracked path")
    desired_parser.add_argument("path", help="File path")
    desired_parser.add_argument("--from-file", help="File containing desired state")
    desired_parser.add_argument("--hash", help="Desired state hash (manual)")
    desired_parser.set_defaults(func=cmd_desired)

    return parser


def main():
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    func = getattr(args, "func", None)
    if func:
        result = func(args)
        return result if isinstance(result, int) else 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
