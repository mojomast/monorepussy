"""CLI interface for Telegrapha — Signal Corps Telegraphy for Data Pipeline Fidelity Analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .models import Hop, PrecedenceClass, Route
from .topology import load_topology, parse_route_string
from .attenuation import (
    analyze_attenuation,
    format_attenuation_report,
    attenuation_to_dict,
    DEFAULT_FIDELITY_THRESHOLD,
)
from .relay_chain import (
    analyze_relay_chain,
    format_relay_chain_report,
    relay_chain_to_dict,
)
from .capacity import (
    analyze_capacity,
    format_capacity_report,
    capacity_to_dict,
)
from .precedence import (
    analyze_precedence,
    format_precedence_report,
    precedence_to_dict,
    PRECEDENCE_LABELS,
)
from .hamming import (
    analyze_hamming,
    format_hamming_report,
    hamming_to_dict,
)
from .dlo import (
    analyze_dlo,
    format_dlo_report,
    dlo_to_dict,
    load_dlq_entries,
)
from .dashboard import (
    generate_dashboard,
    format_dashboard_report,
)


def _output_json(data: dict) -> None:
    """Output data as JSON to stdout."""
    print(json.dumps(data, indent=2))


def _load_route_from_args(route_str: str, topology_path: str | None = None) -> Route:
    """Load a route from a route string or topology file."""
    if topology_path:
        topology = load_topology(topology_path)
        # Try to find matching route
        for route in topology.routes:
            if route.name == route_str:
                return route
        # If no match, parse the route string
        return parse_route_string(route_str)
    return parse_route_string(route_str)


def cmd_attenuation(args: argparse.Namespace) -> int:
    """Run attenuation budget analysis."""
    route = _load_route_from_args(args.route, args.topology)

    # Apply degradation factors if provided
    if args.degradations:
        degradations = [float(d) for d in args.degradations.split(",")]
        for i, deg in enumerate(degradations):
            if i < len(route.hops):
                route.hops[i].degradation = deg

    # Apply details if provided
    if args.details:
        details = args.details.split(",")
        for i, detail in enumerate(details):
            if i < len(route.hops):
                route.hops[i].details = detail.strip()

    result = analyze_attenuation(route, threshold=args.threshold)

    if args.json:
        _output_json(attenuation_to_dict(result))
    else:
        print(format_attenuation_report(result))

    return 0


def cmd_relay_chain(args: argparse.Namespace) -> int:
    """Run relay chain reliability analysis."""
    route = _load_route_from_args(args.route, args.topology)

    # Apply reliability factors if provided
    if args.reliabilities:
        rels = [float(r) for r in args.reliabilities.split(",")]
        for i, rel in enumerate(rels):
            if i < len(route.hops):
                route.hops[i].reliability = rel

    sla = args.sla / 100.0  # Convert percentage to decimal

    result = analyze_relay_chain(route, target_sla=sla)

    if args.json:
        _output_json(relay_chain_to_dict(result))
    else:
        print(format_relay_chain_report(result))

    return 0


def cmd_capacity(args: argparse.Namespace) -> int:
    """Run Shannon-Hartley capacity analysis."""
    result = analyze_capacity(
        bandwidth=args.bandwidth,
        signal_rate=args.signal,
        noise_rate=args.noise,
        num_workers=args.workers,
        avg_worker_utilization=args.utilization,
    )

    if args.json:
        _output_json(capacity_to_dict(result))
    else:
        print(format_capacity_report(result))

    return 0


def cmd_precedence(args: argparse.Namespace) -> int:
    """Run precedence analysis."""
    classes = []

    if args.config:
        # Load from JSON config
        config_path = Path(args.config)
        if not config_path.exists():
            if args.json:
                _output_json({"error": f"Config file not found: {args.config}"})
            else:
                print(f"Error: Config file not found: {args.config}", file=sys.stderr)
            return 1

        data = json.loads(config_path.read_text(encoding="utf-8"))
        for item in data.get("classes", []):
            label = item.get("label", "ROUTINE")
            classes.append(PrecedenceClass(
                name=item.get("name", "unknown"),
                label=label,
                arrival_rate=float(item.get("arrival_rate", 0.0)),
                service_time=float(item.get("service_time", 0.0)),
                preemption_overhead=float(item.get("preemption_overhead", 0.0)),
            ))
    else:
        # Use default example classes
        classes = [
            PrecedenceClass(
                name="circuit-breaker signals",
                label="FLASH",
                arrival_rate=0.5 / 60.0,  # per second
                service_time=0.050,
                preemption_overhead=0.003,
            ),
            PrecedenceClass(
                name="payment processing",
                label="IMMEDIATE",
                arrival_rate=120.0 / 60.0,
                service_time=0.200,
            ),
            PrecedenceClass(
                name="user-facing requests",
                label="PRIORITY",
                arrival_rate=600.0 / 60.0,
                service_time=0.100,
            ),
            PrecedenceClass(
                name="batch analytics",
                label="ROUTINE",
                arrival_rate=30.0 / 60.0,
                service_time=5.0,
            ),
        ]

    if not classes:
        if args.json:
            _output_json({"error": "No priority classes defined"})
        else:
            print("Error: No priority classes defined", file=sys.stderr)
        return 1

    result = analyze_precedence(classes)

    if args.json:
        _output_json(precedence_to_dict(result))
    else:
        print(format_precedence_report(result))

    return 0


def cmd_hamming(args: argparse.Namespace) -> int:
    """Run Hamming FEC vs ARQ analysis."""
    pipeline_length = args.hops
    if args.topology:
        topology = load_topology(args.topology)
        for route in topology.routes:
            pipeline_length = max(pipeline_length, route.hop_count)
        if pipeline_length == 0:
            pipeline_length = args.hops

    result = analyze_hamming(
        error_rate=args.error_rate,
        pipeline_length=pipeline_length,
        target_reliability=args.target,
        fec_code_n=args.fec_n,
        fec_code_k=args.fec_k,
        schema_drift_distance=args.drift,
    )

    if args.json:
        _output_json(hamming_to_dict(result))
    else:
        print(format_hamming_report(result))

    return 0


def cmd_dlo(args: argparse.Namespace) -> int:
    """Run Dead Letter Office analysis."""
    dlq_path = args.dlq

    if not dlq_path:
        if args.json:
            _output_json({"error": "DLQ file path required (--dlq)"})
        else:
            print("Error: DLQ file path required (--dlq)", file=sys.stderr)
        return 1

    dlq_file = Path(dlq_path)
    if not dlq_file.exists():
        if args.json:
            _output_json({"error": f"DLQ file not found: {dlq_path}"})
        else:
            print(f"Error: DLQ file not found: {dlq_path}", file=sys.stderr)
        return 1

    try:
        entries = load_dlq_entries(dlq_path)
    except (json.JSONDecodeError, ValueError) as e:
        if args.json:
            _output_json({"error": f"Invalid DLQ file: {e}"})
        else:
            print(f"Error: Invalid DLQ file: {e}", file=sys.stderr)
        return 1

    result = analyze_dlo(
        entries,
        accumulation_rate=args.accumulation,
        resolution_rate=args.resolution,
    )

    if args.json:
        _output_json(dlo_to_dict(result))
    else:
        print(format_dlo_report(result))

    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Run comprehensive dashboard analysis."""
    topology = load_topology(args.topology)

    dashboard = generate_dashboard(
        topology=topology,
        target_sla=args.sla / 100.0,
        bandwidth=args.bandwidth,
        signal_rate=args.signal,
        noise_rate=args.noise,
        error_rate=args.error_rate,
        dlq_path=args.dlq,
        dlq_accumulation_rate=args.dlq_accumulation,
        dlq_resolution_rate=args.dlq_resolution,
    )

    if args.json:
        _output_json(dashboard)
    else:
        print(format_dashboard_report(dashboard))

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="telegrapha",
        description="Telegrapha — Signal Corps Telegraphy for Data Pipeline Fidelity Analysis",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # attenuation
    att_parser = subparsers.add_parser(
        "attenuation",
        help="Attenuation budget — cumulative fidelity decay analysis",
    )
    att_parser.add_argument(
        "route",
        help="Route string (e.g., 'order-service→payment→fraud-check→ledger')",
    )
    att_parser.add_argument(
        "--topology", "-t",
        help="Path to topology YAML/JSON file",
    )
    att_parser.add_argument(
        "--degradations", "-d",
        help="Comma-separated degradation factors (e.g., '0.005,0.03,0.02,0.04')",
    )
    att_parser.add_argument(
        "--details",
        help="Comma-separated hop details",
    )
    att_parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_FIDELITY_THRESHOLD,
        help=f"Fidelity threshold (default: {DEFAULT_FIDELITY_THRESHOLD})",
    )
    att_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )
    att_parser.set_defaults(func=cmd_attenuation)

    # relay-chain
    rc_parser = subparsers.add_parser(
        "relay-chain",
        help="Relay chain reliability — service mesh hop budget",
    )
    rc_parser.add_argument(
        "route",
        help="Route string (e.g., 'api-gateway→auth→user-service→db')",
    )
    rc_parser.add_argument(
        "--topology", "-t",
        help="Path to topology YAML/JSON file",
    )
    rc_parser.add_argument(
        "--reliabilities", "-r",
        help="Comma-separated reliability values (e.g., '0.9999,0.9995,0.9998')",
    )
    rc_parser.add_argument(
        "--sla",
        type=float,
        default=99.9,
        help="Target SLA percentage (default: 99.9)",
    )
    rc_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )
    rc_parser.set_defaults(func=cmd_relay_chain)

    # capacity
    cap_parser = subparsers.add_parser(
        "capacity",
        help="Shannon-Hartley capacity — theoretical throughput ceiling",
    )
    cap_parser.add_argument(
        "--bandwidth", "-b",
        type=float,
        default=500.0,
        help="Max concurrent operations (default: 500)",
    )
    cap_parser.add_argument(
        "--signal", "-s",
        type=float,
        default=420.0,
        help="Useful throughput rate (default: 420)",
    )
    cap_parser.add_argument(
        "--noise", "-n",
        type=float,
        default=80.0,
        help="Noise rate: retries + health checks + duplicates (default: 80)",
    )
    cap_parser.add_argument(
        "--workers", "-w",
        type=int,
        default=1,
        help="Number of processing workers (default: 1)",
    )
    cap_parser.add_argument(
        "--utilization", "-u",
        type=float,
        default=None,
        help="Average worker utilization (0.0–1.0)",
    )
    cap_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )
    cap_parser.set_defaults(func=cmd_capacity)

    # precedence
    prec_parser = subparsers.add_parser(
        "precedence",
        help="Message precedence — priority queue optimization",
    )
    prec_parser.add_argument(
        "--config", "-c",
        help="Path to priority classes JSON config",
    )
    prec_parser.add_argument(
        "--classes",
        type=int,
        default=4,
        help="Number of precedence classes (default: 4)",
    )
    prec_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )
    prec_parser.set_defaults(func=cmd_precedence)

    # hamming
    ham_parser = subparsers.add_parser(
        "hamming",
        help="Hamming analysis — FEC vs ARQ decision framework",
    )
    ham_parser.add_argument(
        "--error-rate", "-e",
        type=float,
        default=0.03,
        help="Per-hop error rate (default: 0.03)",
    )
    ham_parser.add_argument(
        "--hops",
        type=int,
        default=6,
        help="Pipeline length in hops (default: 6)",
    )
    ham_parser.add_argument(
        "--topology", "-t",
        help="Path to topology YAML/JSON file (overrides --hops)",
    )
    ham_parser.add_argument(
        "--target",
        type=float,
        default=0.999,
        help="Target reliability (default: 0.999)",
    )
    ham_parser.add_argument(
        "--fec-n",
        type=int,
        default=3,
        help="FEC code N parameter (default: 3)",
    )
    ham_parser.add_argument(
        "--fec-k",
        type=int,
        default=2,
        help="FEC code K parameter (default: 2)",
    )
    ham_parser.add_argument(
        "--drift",
        type=int,
        default=0,
        help="Schema drift distance (default: 0)",
    )
    ham_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )
    ham_parser.set_defaults(func=cmd_hamming)

    # dlo
    dlo_parser = subparsers.add_parser(
        "dlo",
        help="Dead Letter Office — DLQ as analytical instrument",
    )
    dlo_parser.add_argument(
        "--dlq",
        help="Path to DLQ entries JSON file",
    )
    dlo_parser.add_argument(
        "--accumulation", "-a",
        type=float,
        default=None,
        help="DLQ accumulation rate (messages/hour)",
    )
    dlo_parser.add_argument(
        "--resolution", "-r",
        type=float,
        default=None,
        help="DLQ resolution rate (messages/hour)",
    )
    dlo_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )
    dlo_parser.set_defaults(func=cmd_dlo)

    # dashboard
    dash_parser = subparsers.add_parser(
        "dashboard",
        help="Comprehensive dashboard — all analyses combined",
    )
    dash_parser.add_argument(
        "topology",
        help="Path to topology YAML/JSON file",
    )
    dash_parser.add_argument(
        "--sla",
        type=float,
        default=99.9,
        help="Target SLA percentage (default: 99.9)",
    )
    dash_parser.add_argument(
        "--bandwidth", "-b",
        type=float,
        default=500.0,
        help="Pipeline bandwidth (default: 500)",
    )
    dash_parser.add_argument(
        "--signal", "-s",
        type=float,
        default=420.0,
        help="Signal throughput rate (default: 420)",
    )
    dash_parser.add_argument(
        "--noise", "-n",
        type=float,
        default=80.0,
        help="Noise rate (default: 80)",
    )
    dash_parser.add_argument(
        "--error-rate", "-e",
        type=float,
        default=0.03,
        help="Per-hop error rate for Hamming analysis (default: 0.03)",
    )
    dash_parser.add_argument(
        "--dlq",
        help="Path to DLQ entries JSON file",
    )
    dash_parser.add_argument(
        "--dlq-accumulation",
        type=float,
        default=None,
        help="DLQ accumulation rate",
    )
    dash_parser.add_argument(
        "--dlq-resolution",
        type=float,
        default=None,
        help="DLQ resolution rate",
    )
    dash_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )
    dash_parser.set_defaults(func=cmd_dashboard)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


def cli_entry() -> None:
    """Entry point for console_scripts."""
    sys.exit(main())
