"""Strata CLI — Geological Semver for Codebase Archeology."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from ussy_stratax.models import (
    BedrockReport,
    DiffResult,
    ErosionReport,
    FaultLine,
    Probe,
    ProbeResult,
    ScanResult,
    StratigraphicColumn,
    VersionProbeResult,
)
from ussy_stratax.scanner.lockfile import LockfileParser
from ussy_stratax.scanner.scanner import ProjectScanner
from ussy_stratax.analysis.stratigraphic import StratigraphicAnalyzer
from ussy_stratax.diff import VersionDiffer
from ussy_stratax.render.ascii import ASCIIRenderer
from ussy_stratax.probes.generator import ProbeGenerator
from ussy_stratax.probes.runner import ProbeRunner, SimulatedProbeRunner
from ussy_stratax.probes.loader import ProbeLoader
from ussy_stratax.registry.local import LocalRegistry
from ussy_stratax.registry.remote import RemoteRegistry


def cmd_scan(args: argparse.Namespace) -> int:
    """Scan a lockfile for seismic hazards."""
    renderer = ASCIIRenderer(use_color=not args.no_color)
    parser = LockfileParser()

    try:
        dependencies = parser.parse(args.lockfile)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not dependencies:
        print("No dependencies found in lockfile.")
        return 0

    print(f"Found {len(dependencies)} dependencies in {args.lockfile}")

    # If version data is provided, use it for analysis
    version_data = {}
    if args.data:
        try:
            with open(args.data, "r") as f:
                version_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load data file: {e}", file=sys.stderr)

    scanner = ProjectScanner(version_data=version_data)
    result = scanner.scan_dependencies(dependencies, args.lockfile)

    output = renderer.render_scan_result(result)
    print(output)

    if args.json:
        _print_json(result)

    return 0 if not result.has_hazards else 2


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze a package's behavioral stability."""
    renderer = ASCIIRenderer(use_color=not args.no_color)
    analyzer = StratigraphicAnalyzer()

    # Load version data
    version_data = {}
    if args.data:
        try:
            with open(args.data, "r") as f:
                version_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error: Could not load data file: {e}", file=sys.stderr)
            return 1

    if args.package not in version_data:
        print(f"No probe data available for package: {args.package}")
        print("Use 'strata probe' to generate probes, then run them against versions.")
        return 1

    column = analyzer.analyze(args.package, version_data[args.package])

    output = renderer.render_column(column)
    print(output)

    if args.json:
        _print_json(column)

    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    """Compare behavioral profiles between two versions."""
    renderer = ASCIIRenderer(use_color=not args.no_color)
    differ = VersionDiffer()

    # Load version data
    version_data = {}
    if args.data:
        try:
            with open(args.data, "r") as f:
                version_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error: Could not load data file: {e}", file=sys.stderr)
            return 1

    # Find the two versions in the data
    if args.package not in version_data:
        print(f"No data for package: {args.package}")
        return 1

    func_data = version_data[args.package]
    # Build version results from the first function's data
    first_func = next(iter(func_data.values()), [])

    result_a = None
    result_b = None
    for vr in first_func:
        if vr.version == args.version_a:
            result_a = vr
        if vr.version == args.version_b:
            result_b = vr

    if result_a is None:
        print(f"Version {args.version_a} not found in data")
        return 1
    if result_b is None:
        print(f"Version {args.version_b} not found in data")
        return 1

    diff_result = differ.diff(args.package, args.version_a, args.version_b, result_a, result_b)

    output = renderer.render_diff_result(diff_result)
    print(output)

    if args.json:
        _print_json(diff_result)

    return 0 if not diff_result.has_quakes else 2


def cmd_probe(args: argparse.Namespace) -> int:
    """Generate behavioral probes for a package."""
    generator = ProbeGenerator()

    if args.function:
        probes = generator.generate_for_function(args.package, args.function)
    else:
        probes = generator.generate_for_package(args.package)

    if not probes:
        print(f"Could not generate probes for package: {args.package}")
        print("Make sure the package is installed and importable.")
        return 1

    print(f"Generated {len(probes)} probes for {args.package}:")
    for probe in probes:
        print(f"  • {probe.name}")
        if probe.function:
            print(f"    Function: {probe.function}")
        if probe.returns_type:
            print(f"    Returns: {probe.returns_type}")

    if args.output:
        data = [p.to_dict() for p in probes]
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nProbes saved to {args.output}")

    if args.save:
        registry = LocalRegistry()
        for probe in probes:
            registry.store_probe(probe)
        print(f"\nProbes saved to local registry")

    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Run probes against a package version."""
    # Load probes
    probes = []
    if args.probes_file:
        with open(args.probes_file, "r") as f:
            probe_data = json.load(f)
        for pd in probe_data:
            probes.append(Probe(**pd))
    else:
        # Auto-generate probes
        generator = ProbeGenerator()
        probes = generator.generate_for_package(args.package)

    if not probes:
        print("No probes to run.")
        return 1

    # Run probes
    runner = ProbeRunner(timeout=args.timeout)
    version = args.version or "installed"

    print(f"Running {len(probes)} probes against {args.package}@{version}...")
    results = runner.run_probes(probes, version)

    # Display results
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    print(f"\nResults: {passed} passed, {failed} failed out of {len(results)} probes")

    for result in results:
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {status} — {result.probe_name} ({result.execution_time_ms:.1f}ms)")
        if result.error:
            print(f"         Error: {result.error}")

    if args.output:
        data = [vars(r) for r in results]
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nResults saved to {args.output}")

    return 0 if failed == 0 else 1


def cmd_legend(args: argparse.Namespace) -> int:
    """Display the geological legend for Strata's visualizations."""
    print("Strata Geological Legend")
    print("=" * 50)
    print()
    print("Stability Tiers:")
    print("  █ Bedrock     (90-100) — Rock-solid, never changed")
    print("  ▊ Stable      (65-89)  — Mostly stable, rare quakes")
    print("  ▄ Hazard      (35-64)  — Frequent behavioral changes")
    print("  ▂ Quicksand   (15-34)  — Unstable, avoid relying on this")
    print("  ▁ Deprecated  (0-14)   — Effectively dead")
    print()
    print("Seismic Hazard Levels:")
    print("  ✓ Dormant      (< 0.05 quakes/version)")
    print("  ⚡ Minor        (0.05-0.15)")
    print("  ⚠ Moderate     (0.15-0.35)")
    print("  🔥 Major        (0.35-0.60)")
    print("  💀 Catastrophic (> 0.60)")
    print()
    print("Key Concepts:")
    print("  Bedrock Score  — How consistently has behavior been stable?")
    print("  Seismic Hazard — How frequently does behavior shift?")
    print("  Fault Line     — Boundary between bedrock and unstable API")
    print("  Erosion        — Slow deprecation across versions")
    print("  Quake          — A behavioral change detected by probes")

    return 0


def _print_json(obj) -> None:
    """Print an object as JSON."""
    if hasattr(obj, "to_dict"):
        data = obj.to_dict()
    elif hasattr(obj, "__dataclass_fields__"):
        import dataclasses
        data = dataclasses.asdict(obj)
    else:
        data = vars(obj)
    print(json.dumps(data, indent=2, default=str))


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="strata",
        description="Strata — Geological Semver for Codebase Archeology",
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan
    scan_parser = subparsers.add_parser(
        "scan", help="Scan a lockfile for seismic hazards"
    )
    scan_parser.add_argument("lockfile", help="Path to lockfile")
    scan_parser.add_argument(
        "--data", help="Path to JSON file with probe version data"
    )

    # analyze
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze a package's behavioral stability"
    )
    analyze_parser.add_argument("package", help="Package name to analyze")
    analyze_parser.add_argument(
        "--data", help="Path to JSON file with probe version data"
    )

    # diff
    diff_parser = subparsers.add_parser(
        "diff", help="Compare behavioral profiles between two versions"
    )
    diff_parser.add_argument("package", help="Package name")
    diff_parser.add_argument("version_a", help="First version")
    diff_parser.add_argument("version_b", help="Second version")
    diff_parser.add_argument(
        "--data", help="Path to JSON file with probe version data"
    )

    # probe
    probe_parser = subparsers.add_parser(
        "probe", help="Generate behavioral probes for a package"
    )
    probe_parser.add_argument("package", help="Package name")
    probe_parser.add_argument(
        "--function", "-f", help="Generate probes for a specific function"
    )
    probe_parser.add_argument(
        "--output", "-o", help="Save probes to JSON file"
    )
    probe_parser.add_argument(
        "--save", action="store_true", help="Save probes to local registry"
    )

    # run
    run_parser = subparsers.add_parser(
        "run", help="Run probes against a package version"
    )
    run_parser.add_argument("package", help="Package name")
    run_parser.add_argument(
        "--version", "-v", help="Package version (default: installed)"
    )
    run_parser.add_argument(
        "--probes-file", help="Path to JSON file with probe definitions"
    )
    run_parser.add_argument(
        "--timeout", type=float, default=10.0, help="Probe timeout in seconds"
    )
    run_parser.add_argument(
        "--output", "-o", help="Save results to JSON file"
    )

    # legend
    subparsers.add_parser(
        "legend", help="Display the geological legend"
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "scan": cmd_scan,
        "analyze": cmd_analyze,
        "diff": cmd_diff,
        "probe": cmd_probe,
        "run": cmd_run,
        "legend": cmd_legend,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
