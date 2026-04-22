"""
CLI — Command-line interface for Aquifer.

Usage:
    aquifer analyze <topology.json>         — Analyze flow and find bottlenecks
    aquifer contour <topology.json>         — Generate ASCII contour map
    aquifer whatif <topology.json> --drill <service>  — Simulate adding capacity
    aquifer predict <topology.json> --duration <hours>  — Predict time-to-saturation
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Optional, Sequence

from . import __version__
from .topology import load_topology, create_sample_topology, save_topology
from .darcy import analyze_flow, find_bottlenecks, compute_conductivity_map
from .theis import predict_system, compute_time_to_saturation
from .grid import solve_grid
from .contour import generate_contour_report, generate_head_contour, generate_drawdown_map
from .drawdown import compute_cone_of_depression, predict_cascade
from .whatif import drill_well, add_fracture, remove_confining_layer


def cmd_analyze(args: argparse.Namespace) -> int:
    """Run flow analysis on a topology."""
    topo = load_topology(args.topology)

    # Validate
    issues = topo.validate()
    if issues:
        print("Topology validation issues:")
        for issue in issues:
            print(f"  ⚠ {issue}")
        print()

    # Flow analysis
    analysis = analyze_flow(topo)
    print(analysis.summary())

    # Conductivity map
    print("\nConductivity Map (K-values):")
    k_map = compute_conductivity_map(topo)
    for name, K in sorted(k_map.items(), key=lambda x: -x[1]):
        print(f"  {name}: K = {K:.1f} req/s")

    # Cone of depression for the highest-pressure service
    if analysis.max_pressure_service:
        print(f"\nCone of Depression from {analysis.max_pressure_service}:")
        cone = compute_cone_of_depression(
            topo, analysis.max_pressure_service, 0.5, 300.0
        )
        print(cone.summary())

    return 0


def cmd_contour(args: argparse.Namespace) -> int:
    """Generate ASCII contour map."""
    topo = load_topology(args.topology)
    width = getattr(args, "width", 60)
    height = getattr(args, "height", 20)

    report = generate_contour_report(topo, width=width, height=height)
    print(report)
    return 0


def cmd_whatif(args: argparse.Namespace) -> int:
    """Run what-if scenario."""
    topo = load_topology(args.topology)
    drill_service = getattr(args, "drill", None)
    fracture = getattr(args, "fracture", None)
    unconfine = getattr(args, "unconfine", None)

    if drill_service:
        additional_replicas = getattr(args, "replicas", 1)
        additional_K = getattr(args, "add_K", 0.0)
        result = drill_well(topo, drill_service, additional_K, additional_replicas)
        print(result.summary())
    elif fracture:
        parts = fracture.split(",")
        if len(parts) != 2:
            print("Error: --fracture requires source,target format")
            return 1
        source, target = parts[0].strip(), parts[1].strip()
        bandwidth = getattr(args, "bandwidth", 0.0)
        result = add_fracture(topo, source, target, bandwidth)
        print(result.summary())
    elif unconfine:
        result = remove_confining_layer(topo, unconfine)
        print(result.summary())
    else:
        print("Error: specify --drill, --fracture, or --unconfine")
        return 1

    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    """Predict system behavior over time."""
    topo = load_topology(args.topology)
    duration = getattr(args, "duration", 1.0)
    load_mult = getattr(args, "load", 1.0)

    prediction = predict_system(topo, duration, load_mult)
    print(prediction.summary())

    # Also show cone of depression for first saturated service
    if prediction.cascading_failure_services:
        first = prediction.cascading_failure_services[0]
        print(f"\nCone of Depression from {first}:")
        cone = compute_cone_of_depression(topo, first, 0.5, duration * 3600)
        print(cone.summary())

        cascade = predict_cascade(topo, first, 0.5, duration * 3600)
        if cascade:
            print(f"\nCascading failure risk: {' → '.join(cascade)}")

    return 0


def cmd_sample(args: argparse.Namespace) -> int:
    """Generate a sample topology file."""
    topo = create_sample_topology()
    output = getattr(args, "output", "sample_topology.json")
    save_topology(topo, output)
    print(f"Sample topology saved to {output}")
    print(f"Services: {len(topo.services)}, Connections: {len(topo.connections)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="aquifer",
        description="Aquifer — Darcy's Law groundwater flow modeling for data pipeline bottleneck analysis",
    )
    parser.add_argument("--version", action="version", version=f"aquifer {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze flow and find bottlenecks")
    analyze_parser.add_argument("topology", help="Path to topology JSON file")

    # contour
    contour_parser = subparsers.add_parser("contour", help="Generate ASCII contour map")
    contour_parser.add_argument("topology", help="Path to topology JSON file")
    contour_parser.add_argument("--width", type=int, default=60, help="Map width (default: 60)")
    contour_parser.add_argument("--height", type=int, default=20, help="Map height (default: 20)")

    # whatif
    whatif_parser = subparsers.add_parser("whatif", help="What-if scenario analysis")
    whatif_parser.add_argument("topology", help="Path to topology JSON file")
    whatif_parser.add_argument("--drill", metavar="SERVICE", help="Drill a well at SERVICE (add capacity)")
    whatif_parser.add_argument("--replicas", type=int, default=1, help="Number of replicas to add (default: 1)")
    whatif_parser.add_argument("--add-K", type=float, default=0.0, dest="add_K",
                                help="Additional K to add (default: 0)")
    whatif_parser.add_argument("--fracture", metavar="SOURCE,TARGET",
                                help="Add fracture flow between services")
    whatif_parser.add_argument("--bandwidth", type=float, default=0.0,
                                help="Bandwidth limit for fracture (default: 0=unlimited)")
    whatif_parser.add_argument("--unconfine", metavar="SERVICE",
                                help="Remove rate limit at SERVICE")

    # predict
    predict_parser = subparsers.add_parser("predict", help="Predict system behavior over time")
    predict_parser.add_argument("topology", help="Path to topology JSON file")
    predict_parser.add_argument("--duration", type=float, default=1.0,
                                 help="Duration to predict (hours, default: 1)")
    predict_parser.add_argument("--load", type=float, default=1.0,
                                 help="Load multiplier (e.g., 2.0 for 2x load)")

    # sample
    sample_parser = subparsers.add_parser("sample", help="Generate sample topology file")
    sample_parser.add_argument("--output", default="sample_topology.json",
                                help="Output file path (default: sample_topology.json)")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    command = getattr(args, "command", None)
    if command is None:
        parser.print_help()
        return 0

    cmd_map = {
        "analyze": cmd_analyze,
        "contour": cmd_contour,
        "whatif": cmd_whatif,
        "predict": cmd_predict,
        "sample": cmd_sample,
    }

    handler = cmd_map.get(command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in topology file: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
