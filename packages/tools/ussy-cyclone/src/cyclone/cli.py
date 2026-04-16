"""CLI interface for Cyclone — vorticity-based data pipeline anomaly detection.

Provides subcommands:
    survey      — Discover pipeline topology, compute flow fields
    vorticity   — Show vorticity at each pipeline stage
    detect      — Detect active cyclonic formations
    cisk        — Detect CISK conditions (positive feedback loops)
    stability   — Richardson number at each stage boundary
    pv          — Potential vorticity analysis
    forecast    — Pipeline weather forecast
    category    — Current cyclone categories (Saffir-Simpson analog)
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from cyclone import __version__


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="cyclone",
        description="Cyclone — Vorticity-Based Data Pipeline Anomaly Detection",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── survey ────────────────────────────────────────────────
    survey_parser = subparsers.add_parser(
        "survey",
        help="Discover pipeline topology, compute flow fields",
    )
    survey_parser.add_argument(
        "source",
        help="Path to pipeline config file or directory",
    )

    # ── vorticity ─────────────────────────────────────────────
    vorticity_parser = subparsers.add_parser(
        "vorticity",
        help="Show vorticity at each pipeline stage",
    )
    vorticity_parser.add_argument(
        "source",
        help="Path to pipeline config file or directory",
    )
    vorticity_parser.add_argument(
        "--field",
        choices=["summary", "full"],
        default="summary",
        help="Field display mode (default: summary)",
    )
    vorticity_parser.add_argument(
        "--stage",
        help="Show detailed vorticity for a specific stage",
    )

    # ── detect ────────────────────────────────────────────────
    detect_parser = subparsers.add_parser(
        "detect",
        help="Detect active cyclonic formations",
    )
    detect_parser.add_argument(
        "source",
        help="Path to pipeline config file or directory",
    )
    detect_parser.add_argument(
        "--history",
        help="Look back period (e.g. 24h)",
    )

    # ── track ─────────────────────────────────────────────────
    track_parser = subparsers.add_parser(
        "track",
        help="Track a specific cyclone's path and intensity",
    )
    track_parser.add_argument(
        "source",
        help="Path to pipeline config file or directory",
    )
    track_parser.add_argument(
        "cyclone_id",
        help="Cyclone ID to track",
    )

    # ── cisk ──────────────────────────────────────────────────
    cisk_parser = subparsers.add_parser(
        "cisk",
        help="Detect CISK conditions (positive feedback loops)",
    )
    cisk_parser.add_argument(
        "source",
        help="Path to pipeline config file or directory",
    )
    cisk_parser.add_argument(
        "--graph",
        action="store_true",
        help="Visualize retry/error feedback graph",
    )

    # ── stability ─────────────────────────────────────────────
    stability_parser = subparsers.add_parser(
        "stability",
        help="Richardson number at each stage boundary",
    )
    stability_parser.add_argument(
        "source",
        help="Path to pipeline config file or directory",
    )
    stability_parser.add_argument(
        "--critical",
        action="store_true",
        help="Only show stages with Ri < 0.25",
    )

    # ── pv ────────────────────────────────────────────────────
    pv_parser = subparsers.add_parser(
        "pv",
        help="Potential vorticity analysis",
    )
    pv_parser.add_argument(
        "source",
        help="Path to pipeline config file or directory",
    )
    pv_parser.add_argument(
        "--simulate",
        action="store_true",
        help="Simulate scaling change",
    )
    pv_parser.add_argument(
        "--scale-down",
        type=int,
        metavar="N",
        help="Simulate scaling stage to N consumers",
    )
    pv_parser.add_argument(
        "--stage",
        help="Stage to simulate scaling (required with --simulate)",
    )

    # ── forecast ──────────────────────────────────────────────
    forecast_parser = subparsers.add_parser(
        "forecast",
        help="Pipeline weather forecast",
    )
    forecast_parser.add_argument(
        "source",
        help="Path to pipeline config file or directory",
    )
    forecast_parser.add_argument(
        "--horizon",
        type=int,
        default=4,
        help="Forecast horizon in hours (default: 4)",
    )
    forecast_parser.add_argument(
        "--confidence",
        action="store_true",
        help="Show confidence intervals",
    )

    # ── category ──────────────────────────────────────────────
    category_parser = subparsers.add_parser(
        "category",
        help="Current cyclone categories (Saffir-Simpson analog)",
    )
    category_parser.add_argument(
        "source",
        help="Path to pipeline config file or directory",
    )
    category_parser.add_argument(
        "--all",
        action="store_true",
        dest="show_all",
        help="Show all cyclones including calm stages",
    )

    return parser


def _resolve_source(source: str) -> str:
    """Resolve a source path (file or directory) to an actual file path.

    If source is a directory, auto-discover config file.
    If source is a file, return as-is.
    """
    from cyclone.survey import discover_config

    if os.path.isdir(source):
        config = discover_config(source)
        if config is None:
            print(f"Error: No pipeline configuration found in {source}", file=sys.stderr)
            sys.exit(1)
        return config
    elif os.path.isfile(source):
        return source
    else:
        print(f"Error: Source not found: {source}", file=sys.stderr)
        sys.exit(1)


def cmd_survey(args: argparse.Namespace) -> None:
    """Execute the survey command."""
    from cyclone.survey import survey, format_survey

    result = survey(args.source)
    print(format_survey(result))


def cmd_vorticity(args: argparse.Namespace) -> None:
    """Execute the vorticity command."""
    from cyclone.survey import load_topology
    from cyclone.vorticity import compute_vorticity_field, format_vorticity

    topology = load_topology(args.source)
    readings = compute_vorticity_field(topology)

    if args.stage:
        if args.stage in readings:
            reading = readings[args.stage]
            print(f"Stage: {args.stage}")
            print(f"  Vorticity (ζ): {reading.zeta:+.4f}")
            print(f"  Absolute vorticity (η): {reading.absolute_vorticity:+.4f}")
            print(f"  Divergence: {reading.divergence:+.4f}")
            print(f"  Potential vorticity: {reading.pv:.6f}")
            print(f"  Category: {reading.category.label}")
        else:
            print(f"Stage '{args.stage}' not found. Available: {', '.join(readings.keys())}")
    else:
        print(format_vorticity(readings, mode=args.field))


def cmd_detect(args: argparse.Namespace) -> None:
    """Execute the detect command."""
    from cyclone.survey import load_topology
    from cyclone.cisk import detect_cisk
    from cyclone.detect import detect_cyclones, format_detection

    topology = load_topology(args.source)
    cycles, gains = detect_cisk(topology)
    detections = detect_cyclones(topology, cisk_cycles=cycles, cycle_gains=gains)
    print(format_detection(detections))


def cmd_track(args: argparse.Namespace) -> None:
    """Execute the track command."""
    from cyclone.survey import load_topology
    from cyclone.cisk import detect_cisk
    from cyclone.detect import detect_cyclones, track_cyclone

    topology = load_topology(args.source)
    cycles, gains = detect_cisk(topology)
    detections = detect_cyclones(topology, cisk_cycles=cycles, cycle_gains=gains)

    result = track_cyclone(detections, args.cyclone_id)
    if result:
        print(f"Tracking cyclone: {result.id}")
        print(f"  Center: {result.center_stage}")
        print(f"  Category: {result.severity_label}")
        print(f"  Vorticity: ζ = {result.vorticity:+.2f}")
        print(f"  Stages affected: {', '.join(result.stages_affected)}")
        if result.cisk_cycle:
            print(f"  CISK cycle: {' → '.join(result.cisk_cycle)}")
            print(f"  Cycle gain: {result.cycle_gain:.2f}x")
        if result.dlq_depth > 0:
            print(f"  DLQ depth: {result.dlq_depth:,}")
    else:
        print(f"Cyclone '{args.cyclone_id}' not found in current detections.")
        print("Active cyclones:", ", ".join(d.id for d in detections) if detections else "none")


def cmd_cisk(args: argparse.Namespace) -> None:
    """Execute the cisk command."""
    from cyclone.survey import load_topology
    from cyclone.cisk import detect_cisk, format_cisk

    topology = load_topology(args.source)
    cycles, gains = detect_cisk(topology)
    print(format_cisk(cycles, gains))


def cmd_stability(args: argparse.Namespace) -> None:
    """Execute the stability command."""
    from cyclone.survey import load_topology
    from cyclone.stability import compute_all_stability, format_stability

    topology = load_topology(args.source)
    readings = compute_all_stability(topology)
    print(format_stability(readings, critical_only=args.critical))


def cmd_pv(args: argparse.Namespace) -> None:
    """Execute the pv command."""
    from cyclone.survey import load_topology
    from cyclone.pv import compute_pv, check_pv_conservation, simulate_scale_down, format_pv

    topology = load_topology(args.source)
    pv_map = compute_pv(topology)
    conservation = check_pv_conservation(topology, current_pv=pv_map)
    print(format_pv(pv_map, conservation))

    if args.simulate and args.scale_down is not None:
        stage_name = args.stage
        if not stage_name:
            # Default to the stage with highest vorticity
            max_pv_stage = max(pv_map, key=lambda k: abs(pv_map[k]))
            stage_name = max_pv_stage
            print(f"\n  No --stage specified, using stage with highest PV: {stage_name}")

        try:
            changes = simulate_scale_down(topology, stage_name, args.scale_down)
            print(f"\n  Simulated scaling {stage_name} to {args.scale_down} consumers:")
            for name, change in changes.items():
                if abs(change) > 0.001:
                    direction = "↑" if change > 0 else "↓"
                    print(f"    {name}: ζ {direction} {abs(change):+.3f}")
        except ValueError as e:
            print(f"\n  Error: {e}", file=sys.stderr)


def cmd_forecast(args: argparse.Namespace) -> None:
    """Execute the forecast command."""
    from cyclone.survey import load_topology
    from cyclone.forecast import forecast, format_forecast

    topology = load_topology(args.source)
    steps = forecast(topology, horizon_hours=args.horizon)
    print(format_forecast(steps, with_confidence=args.confidence))


def cmd_category(args: argparse.Namespace) -> None:
    """Execute the category command."""
    from cyclone.survey import load_topology
    from cyclone.cisk import detect_cisk
    from cyclone.detect import detect_cyclones
    from cyclone.category import classify_pipeline, format_category

    topology = load_topology(args.source)
    cycles, gains = detect_cisk(topology)
    detections = detect_cyclones(topology, cisk_cycles=cycles, cycle_gains=gains)
    categories = classify_pipeline(topology, cisk_cycles=cycles)
    print(format_category(categories, detections, show_all=args.show_all))


COMMAND_MAP = {
    "survey": cmd_survey,
    "vorticity": cmd_vorticity,
    "detect": cmd_detect,
    "track": cmd_track,
    "cisk": cmd_cisk,
    "stability": cmd_stability,
    "pv": cmd_pv,
    "forecast": cmd_forecast,
    "category": cmd_category,
}


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point for the Cyclone CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    handler = COMMAND_MAP.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
