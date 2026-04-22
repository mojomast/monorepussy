"""CLI interface for Isobar — meteorological micro-climate analysis."""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional

from isobar import __version__
from isobar.scanner import GitScanner, ScanResult
from isobar.fields import AtmosphericField, compute_fields
from isobar.fronts import detect_fronts, format_fronts_report
from isobar.cyclones import (
    detect_cyclones, detect_anticyclones, generate_storm_warnings,
)
from isobar.forecast import generate_forecast, format_forecast
from isobar.synoptic import (
    render_synoptic_map, render_current_conditions, render_climate_report,
)
from isobar.history import (
    compute_historical_fields, compare_sprints, format_history,
)


def _load_or_scan(args) -> ScanResult:
    """Load a cached scan or perform a fresh scan."""
    scanner = GitScanner(args.path)

    if not scanner.is_git_repo():
        print(f"Error: '{args.path}' is not a git repository.", file=sys.stderr)
        sys.exit(1)

    max_commits = getattr(args, "max_commits", 500)
    result = scanner.scan(max_commits=max_commits)

    if not result.file_histories:
        print("Warning: No file histories found. The repository may be empty or "
              "have no commits.", file=sys.stderr)

    return result


def _compute_atm(scan_result: ScanResult) -> AtmosphericField:
    """Compute atmospheric fields from scan result."""
    return compute_fields(scan_result)


def cmd_survey(args):
    """Scan git history and compute atmospheric fields."""
    print("Scanning repository...")
    scan_result = _load_or_scan(args)
    atm = _compute_atm(scan_result)

    print(f"\nScan complete: {len(atm.profiles)} files analyzed.")
    print(f"  Root: {scan_result.root}")
    print(f"  Time: {atm.computed_at.strftime('%Y-%m-%d %H:%M UTC')}")
    print("")

    # Quick summary
    hot = atm.hot_files()
    cyclones = detect_cyclones(atm)
    fronts = detect_fronts(atm, scan_result.import_graph)

    print(f"  Hot files:     {len(hot)}")
    print(f"  Active fronts: {len(fronts)}")
    print(f"  Cyclones:      {len(cyclones)}")

    if cyclones:
        print("\n  ⚠ Cyclonic activity detected:")
        for c in cyclones[:3]:
            print(f"    {c.eye}: {c.category_label} (ζ={c.vorticity:+.1f})")

    print("\nRun 'isobar map' for the synoptic chart, or 'isobar current' for a summary.")


def cmd_current(args):
    """Show current conditions summary."""
    scan_result = _load_or_scan(args)
    atm = _compute_atm(scan_result)
    print(render_current_conditions(atm))


def cmd_map(args):
    """Display ASCII synoptic weather map."""
    scan_result = _load_or_scan(args)
    atm = _compute_atm(scan_result)
    fronts = detect_fronts(atm, scan_result.import_graph)
    cyclones = detect_cyclones(atm)
    anticyclones = detect_anticyclones(atm)

    fmt = getattr(args, "format", "text")
    module = getattr(args, "module", None)

    if fmt == "json":
        data = _field_to_dict(atm, fronts, cyclones, anticyclones)
        print(json.dumps(data, indent=2, default=str))
    else:
        print(render_synoptic_map(
            atm, fronts=fronts, cyclones=cyclones,
            anticyclones=anticyclones, module_filter=module,
        ))


def cmd_fronts(args):
    """Detect and classify active fronts."""
    scan_result = _load_or_scan(args)
    atm = _compute_atm(scan_result)
    fronts = detect_fronts(atm, scan_result.import_graph)
    print(format_fronts_report(fronts))

    watch = getattr(args, "watch", False)
    if watch:
        print("\nWatching for new fronts... (Ctrl+C to stop)")
        try:
            while True:
                time.sleep(30)
                scan_result = _load_or_scan(args)
                atm = _compute_atm(scan_result)
                new_fronts = detect_fronts(atm, scan_result.import_graph)
                new_count = len(new_fronts)
                if new_count != len(fronts):
                    print(f"\n[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] "
                          f"Front count changed: {len(fronts)} → {new_count}")
                    print(format_fronts_report(new_fronts))
                    fronts = new_fronts
        except KeyboardInterrupt:
            print("\nStopped watching.")


def cmd_forecast(args):
    """Generate weather forecast."""
    scan_result = _load_or_scan(args)
    atm = _compute_atm(scan_result)

    ahead = getattr(args, "ahead", 5)
    file_filter = getattr(args, "file", None)

    forecast = generate_forecast(atm, num_sprints=ahead, file_filter=file_filter)
    print(format_forecast(forecast))


def cmd_warn(args):
    """Show current storm warnings."""
    scan_result = _load_or_scan(args)
    atm = _compute_atm(scan_result)
    cyclones = detect_cyclones(atm)

    threshold = getattr(args, "threshold", "watch")
    warnings = generate_storm_warnings(cyclones, threshold=threshold)

    if not warnings:
        print("No active storm warnings. Conditions are calm.")
    else:
        print("STORM WARNINGS")
        print("=" * 50)
        for w in warnings:
            print(f"\n  {w}")

    # Also check for severe fronts
    fronts = detect_fronts(atm, scan_result.import_graph)
    severe_fronts = [f for f in fronts if f.is_severe]
    if severe_fronts:
        print("\nSEVERE FRONTS:")
        for f in severe_fronts:
            print(f"  {f.risk_label}: {f.description}")


def cmd_climate(args):
    """Show detailed atmospheric profile for a specific file."""
    filepath = args.file
    scan_result = _load_or_scan(args)
    atm = _compute_atm(scan_result)

    # Try exact match first, then partial
    profile = atm.get_profile(filepath)
    if not profile:
        # Try partial match
        matches = [p for fp, p in atm.profiles.items() if filepath in fp]
        if matches:
            profile = matches[0]
        else:
            print(f"File '{filepath}' not found in scan results.")
            print(f"Available files:")
            for fp in sorted(atm.profiles.keys())[:20]:
                print(f"  {fp}")
            if len(atm.profiles) > 20:
                print(f"  ... and {len(atm.profiles) - 20} more")
            sys.exit(1)

    print(render_climate_report(profile))


def cmd_history(args):
    """Show historical weather conditions."""
    scan_result = _load_or_scan(args)

    last_month = getattr(args, "last_month", False)
    compare = getattr(args, "compare", None)

    if compare and len(compare) == 2:
        # Compare two sprints
        atm = _compute_atm(scan_result)
        # For comparison, use the same field (real comparison would need two scans)
        print(compare_sprints(atm, atm, label_a=compare[0], label_b=compare[1]))
    else:
        period = 30 if last_month else 60
        history_data = compute_historical_fields(scan_result, period_days=period)
        print(format_history(history_data))


def _field_to_dict(atm: AtmosphericField, fronts, cyclones, anticyclones) -> dict:
    """Convert atmospheric field to JSON-serializable dict."""
    return {
        "generated_at": atm.computed_at.isoformat(),
        "root": atm.root,
        "profiles": {
            fp: {
                "temperature": p.temperature,
                "pressure": p.pressure,
                "humidity": p.humidity,
                "wind_speed": p.wind_speed,
                "wind_direction": p.wind_direction,
                "dew_point": p.dew_point,
                "bug_vorticity": p.bug_vorticity,
                "barometric_tendency": p.barometric_tendency,
                "internal_energy": p.internal_energy,
                "storm_probability": p.storm_probability,
                "category": p.category_label(),
            }
            for fp, p in atm.profiles.items()
        },
        "fronts": [
            {
                "type": f.front_type.value,
                "intensity": f.intensity.value,
                "hot_side": f.hot_side,
                "cold_side": f.cold_side,
                "gradient": f.temperature_gradient,
                "frontogenesis_rate": f.frontogenesis_rate,
                "is_severe": f.is_severe,
            }
            for f in fronts
        ],
        "cyclones": [
            {
                "eye": c.eye,
                "vorticity": c.vorticity,
                "category": c.category.value,
                "spiral_files": c.spiral_files,
                "probability": c.probability,
                "warning_level": c.warning_level.value,
            }
            for c in cyclones
        ],
        "anticyclones": [
            {
                "center": a.center,
                "stability_index": a.stability_index,
                "protected_files": a.protected_files,
            }
            for a in anticyclones
        ],
    }


def _add_path_arg(p: argparse.ArgumentParser) -> None:
    """Add the --path argument to a subparser."""
    p.add_argument(
        "--path",
        default=".",
        help="Path to git repository (default: current directory)",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="isobar",
        description="Isobar — Meteorological micro-climate analysis for developer workspaces",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # survey
    survey_parser = subparsers.add_parser("survey", help="Scan git history, compute atmospheric fields")
    _add_path_arg(survey_parser)
    survey_parser.add_argument("--max-commits", type=int, default=500, help="Max commits to scan")

    # current
    current_parser = subparsers.add_parser("current", help="Show current conditions summary")
    _add_path_arg(current_parser)

    # map
    map_parser = subparsers.add_parser("map", help="ASCII synoptic weather map")
    _add_path_arg(map_parser)
    map_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    map_parser.add_argument("--module", type=str, default=None, help="Zoom into a specific module")

    # fronts
    fronts_parser = subparsers.add_parser("fronts", help="Detect and classify active fronts")
    _add_path_arg(fronts_parser)
    fronts_parser.add_argument("--watch", action="store_true", help="Continuous monitoring")

    # forecast
    forecast_parser = subparsers.add_parser("forecast", help="Weather forecast")
    _add_path_arg(forecast_parser)
    forecast_parser.add_argument("--ahead", type=int, default=5, help="Number of sprints to forecast")
    forecast_parser.add_argument("--file", type=str, default=None, help="Forecast for specific file")

    # warn
    warn_parser = subparsers.add_parser("warn", help="Current storm warnings")
    _add_path_arg(warn_parser)
    warn_parser.add_argument(
        "--threshold",
        choices=["watch", "warning", "severe", "critical"],
        default="watch",
        help="Minimum warning level",
    )

    # climate
    climate_parser = subparsers.add_parser("climate", help="Micro-climate of a specific file")
    _add_path_arg(climate_parser)
    climate_parser.add_argument("file", type=str, help="File path to analyze")

    # history
    history_parser = subparsers.add_parser("history", help="Historical weather")
    _add_path_arg(history_parser)
    history_parser.add_argument("--last-month", action="store_true", help="Last 30 days")
    history_parser.add_argument("--compare", nargs=2, metavar="SPRINT", help="Compare two sprints")

    return parser


def main():
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Resolve path
    if hasattr(args, "path") and args.path:
        args.path = os.path.abspath(args.path)

    commands = {
        "survey": cmd_survey,
        "current": cmd_current,
        "map": cmd_map,
        "fronts": cmd_fronts,
        "forecast": cmd_forecast,
        "warn": cmd_warn,
        "climate": cmd_climate,
        "history": cmd_history,
    }

    handler = commands.get(args.command)
    if handler:
        try:
            handler(args)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
