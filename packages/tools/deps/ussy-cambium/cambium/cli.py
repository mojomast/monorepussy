"""CLI — Command-line interface for Cambium."""

from __future__ import annotations

import argparse
import json
import os
import sys

from cambium.alignment import (
    compute_alignment,
    compute_alignment_from_files,
    compute_alignment_from_source,
    format_alignment_heatmap,
)
from cambium.bond import bond_trajectory, compute_bond_strength, format_bond_report
from cambium.callus import (
    compute_adapter_quality,
    compute_callus_dynamics,
    format_callus_report,
)
from cambium.compatibility import (
    compute_compatibility,
    compute_compatibility_from_files,
    compute_compatibility_from_source,
)
from cambium.drift import (
    classify_drift_zone,
    compute_drift_debt,
    drift_forecast,
    format_drift_report,
)
from cambium.dwarfing import DependencyNode, format_dwarfing_report
from cambium.extractor import extract_interface, extract_interface_from_file
from cambium.gci import (
    compute_gci,
    compute_gci_simple,
    format_gci_report,
    gci_trajectory,
)
from cambium.models import (
    AlignmentScore,
    BondStrength,
    CallusDynamics,
    CompatibilityScore,
    DriftDebt,
    GCISnapshot,
)
from cambium.scanner import format_scan_report, scan_project
from cambium.storage import Storage


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="cambium",
        description="Cambium — Horticultural Grafting Science for Dependency Compatibility Analysis",
    )
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output in JSON format"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Full GCI assessment for all dependencies")
    scan_parser.add_argument("project", help="Path to project directory or file")

    # compatibility
    compat_parser = subparsers.add_parser(
        "compatibility", help="Detailed scion/rootstock compatibility"
    )
    compat_parser.add_argument("consumer", help="Consumer module path or name")
    compat_parser.add_argument("provider", help="Provider module path or name")

    # alignment
    align_parser = subparsers.add_parser("alignment", help="Interface cambium alignment score")
    align_parser.add_argument("consumer", help="Consumer module path or name")
    align_parser.add_argument("provider", help="Provider module path or name")

    # drift-forecast
    drift_parser = subparsers.add_parser(
        "drift-forecast", help="Predictive drift breakage timeline"
    )
    drift_parser.add_argument("dep", help="Dependency name")
    drift_parser.add_argument(
        "--delta-behavior", type=float, default=0.02, help="Behavioral drift rate"
    )
    drift_parser.add_argument(
        "--delta-contract", type=float, default=0.01, help="Contract drift rate"
    )
    drift_parser.add_argument(
        "--delta-environment", type=float, default=0.005, help="Environment drift rate"
    )
    drift_parser.add_argument(
        "--lambda-s", type=float, default=6.0, help="Dissipation timescale (months)"
    )
    drift_parser.add_argument(
        "--d-critical", type=float, default=1.0, help="Critical drift threshold"
    )

    # bond-traj
    bond_parser = subparsers.add_parser(
        "bond-traj", help="Integration bond strength trajectory"
    )
    bond_parser.add_argument("dep", help="Dependency name")
    bond_parser.add_argument("--b-max", type=float, default=1.0, help="Maximum bond strength")
    bond_parser.add_argument("--k-b", type=float, default=0.3, help="Maturation rate")
    bond_parser.add_argument("--t50", type=float, default=5.0, help="Half-strength time (months)")

    # dwarfing
    dwarf_parser = subparsers.add_parser("dwarfing", help="Find dwarfing dependencies")
    dwarf_parser.add_argument("project", help="Path to project directory")

    # gci-history
    gci_parser = subparsers.add_parser("gci-history", help="GCI trend over time")
    gci_parser.add_argument("dep", help="Dependency name")
    gci_parser.add_argument("--db", default="", help="Path to Cambium database")
    gci_parser.add_argument("--limit", type=int, default=20, help="Number of records")

    return parser


def cmd_scan(args: argparse.Namespace) -> int:
    """Execute scan command."""
    project_path = args.project
    if not os.path.exists(project_path):
        print(f"Error: path not found: {project_path}", file=sys.stderr)
        return 1

    results = scan_project(project_path)

    if getattr(args, "json_output", False):
        print(json.dumps(results, indent=2))
    else:
        print(format_scan_report(results))

    return 0


def cmd_compatibility(args: argparse.Namespace) -> int:
    """Execute compatibility command."""
    consumer_path = args.consumer
    provider_path = args.provider

    # Check if paths are files
    if os.path.isfile(consumer_path) and os.path.isfile(provider_path):
        score = compute_compatibility_from_files(consumer_path, provider_path)
    else:
        # Use synthetic/demo analysis
        consumer_src = f"class {consumer_path}:\n    pass\n"
        provider_src = f"class {provider_path}:\n    pass\n"
        score = compute_compatibility_from_source(
            consumer_src, provider_src, consumer_path, provider_path
        )

    if getattr(args, "json_output", False):
        print(json.dumps({
            "type_similarity": round(score.type_similarity, 4),
            "precondition_satisfaction": round(score.precondition_satisfaction, 4),
            "version_overlap": round(score.version_overlap, 4),
            "composite": round(score.composite, 4),
        }, indent=2))
    else:
        print(f"Scion/Rootstock Compatibility: {args.consumer} → {args.provider}")
        print(f"  Type Similarity (Φ):          {score.type_similarity:.4f}")
        print(f"  Precondition Satisfaction (β): {score.precondition_satisfaction:.4f}")
        print(f"  Version Overlap (ψ):           {score.version_overlap:.4f}")
        print(f"  Composite C(a,b):              {score.composite:.4f}")

    return 0


def cmd_alignment(args: argparse.Namespace) -> int:
    """Execute alignment command."""
    consumer_path = args.consumer
    provider_path = args.provider

    if os.path.isfile(consumer_path) and os.path.isfile(provider_path):
        score = compute_alignment_from_files(consumer_path, provider_path)
        consumer_name = os.path.basename(consumer_path).replace(".py", "")
        provider_name = os.path.basename(provider_path).replace(".py", "")
    else:
        consumer_src = f"class {consumer_path}:\n    pass\n"
        provider_src = f"class {provider_path}:\n    pass\n"
        score = compute_alignment_from_source(
            consumer_src, provider_src, consumer_path, provider_path
        )
        consumer_name = consumer_path
        provider_name = provider_path

    if getattr(args, "json_output", False):
        print(json.dumps({
            "name_match": round(score.name_match, 4),
            "signature_match": round(score.signature_match, 4),
            "semantic_match": round(score.semantic_match, 4),
            "composite": round(score.composite, 4),
            "status": score.status,
        }, indent=2))
    else:
        print(format_alignment_heatmap(consumer_name, provider_name, score))

    return 0


def cmd_drift_forecast(args: argparse.Namespace) -> int:
    """Execute drift-forecast command."""
    drift = compute_drift_debt(
        delta_behavior=args.delta_behavior,
        delta_contract=args.delta_contract,
        delta_environment=args.delta_environment,
        lambda_s=args.lambda_s,
        d_critical=args.d_critical,
    )

    if getattr(args, "json_output", False):
        analysis = classify_drift_zone(drift)
        forecast = drift_forecast(drift)
        print(json.dumps({
            "analysis": analysis,
            "forecast": forecast,
        }, indent=2))
    else:
        print(format_drift_report(drift))

    return 0


def cmd_bond_traj(args: argparse.Namespace) -> int:
    """Execute bond-traj command."""
    bond = compute_bond_strength(
        b_max=args.b_max,
        k_b=args.k_b,
        t50=args.t50,
    )

    if getattr(args, "json_output", False):
        traj = bond_trajectory(bond)
        print(json.dumps({
            "parameters": {
                "b_max": bond.b_max,
                "k_b": bond.k_b,
                "t50": bond.t50,
            },
            "trajectory": traj,
        }, indent=2))
    else:
        print(format_bond_report(bond))

    return 0


def cmd_dwarfing(args: argparse.Namespace) -> int:
    """Execute dwarfing command."""
    project_path = args.project
    if not os.path.exists(project_path):
        print(f"Error: path not found: {project_path}", file=sys.stderr)
        return 1

    from cambium.scanner import _parse_dependencies, _build_dependency_tree

    dependencies = _parse_dependencies(project_path)
    tree = _build_dependency_tree(dependencies)

    if not dependencies:
        # Build a demo tree
        tree = DependencyNode(
            name="project",
            capability=1.0,
            children=[
                DependencyNode(name="fastapi", capability=0.95),
                DependencyNode(name="sync-lib", capability=0.42, children=[
                    DependencyNode(name="blocking-io", capability=0.31),
                ]),
            ],
        )

    if getattr(args, "json_output", False):
        from cambium.dwarfing import analyze_dependency_chain, compute_chain_capability
        analysis = analyze_dependency_chain(tree)
        print(json.dumps({
            "analysis": analysis,
            "chain_capability": round(compute_chain_capability(tree), 4),
        }, indent=2))
    else:
        print(format_dwarfing_report(tree))

    return 0


def cmd_gci_history(args: argparse.Namespace) -> int:
    """Execute gci-history command."""
    db_path = args.db
    storage = Storage(db_path) if db_path else Storage()
    history = storage.get_gci_history(provider=args.dep, limit=args.limit)
    storage.close()

    if getattr(args, "json_output", False):
        print(json.dumps(history, indent=2, default=str))
    else:
        if not history:
            print(f"No GCI history found for '{args.dep}'")
        else:
            print(f"GCI History for '{args.dep}':")
            for record in history:
                print(
                    f"  {record.get('timestamp', 'N/A')}  "
                    f"GCI={record.get('gci', 0):.4f}  "
                    f"C={record.get('compatibility', 0):.3f}  "
                    f"A={record.get('alignment', 0):.3f}"
                )

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "version", False):
        from cambium import __version__
        print(f"cambium {__version__}")
        return 0

    command = getattr(args, "command", None)
    if not command:
        parser.print_help()
        return 0

    commands = {
        "scan": cmd_scan,
        "compatibility": cmd_compatibility,
        "alignment": cmd_alignment,
        "drift-forecast": cmd_drift_forecast,
        "bond-traj": cmd_bond_traj,
        "dwarfing": cmd_dwarfing,
        "gci-history": cmd_gci_history,
    }

    handler = commands.get(command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
