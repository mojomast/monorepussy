"""Gridiron CLI — Power Grid Reliability Engineering for Dependency Ecosystem Health."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import List, Optional

from gridiron import __version__
from ussy_gridiron.graph import DependencyGraph
from ussy_gridiron.models import (
    FullReport,
    HealthStatus,
    VersionShock,
)
from ussy_gridiron.parsers.package_json import parse_package_json
from ussy_gridiron.parsers.requirements_txt import parse_requirements_txt
from ussy_gridiron.parsers.pyproject_toml import parse_pyproject_toml
from ussy_gridiron.instruments.contingency import ContingencyAnalyzer
from ussy_gridiron.instruments.frequency import FrequencyMonitor
from ussy_gridiron.instruments.flow_optimizer import FlowOptimizer
from ussy_gridiron.instruments.relay import RelayCoordinator
from ussy_gridiron.instruments.voltage import VoltageAnalyst
from ussy_gridiron.instruments.grid_code import GridCodeInspector
from ussy_gridiron.report import ReportFormatter


def build_graph(project_path: str) -> DependencyGraph:
    """Build a dependency graph by scanning a project directory."""
    graph = DependencyGraph()
    path = os.path.abspath(project_path)

    if os.path.isfile(path):
        _parse_file(path, graph)
    elif os.path.isdir(path):
        # Scan for known manifest files
        manifest_files = [
            "package.json",
            "requirements.txt",
            "pyproject.toml",
        ]
        for manifest in manifest_files:
            manifest_path = os.path.join(path, manifest)
            if os.path.isfile(manifest_path):
                _parse_file(manifest_path, graph)

        # Also check for requirements in subdirs
        req_path = os.path.join(path, "requirements")
        if os.path.isdir(req_path):
            for fname in os.listdir(req_path):
                if fname.endswith(".txt"):
                    _parse_file(os.path.join(req_path, fname), graph)

    return graph


def _parse_file(filepath: str, graph: DependencyGraph) -> None:
    """Parse a manifest file and add results to the graph."""
    basename = os.path.basename(filepath)

    try:
        if basename == "package.json":
            packages, edges = parse_package_json(filepath)
        elif basename == "requirements.txt" or basename.endswith(".txt"):
            packages, edges = parse_requirements_txt(filepath)
        elif basename == "pyproject.toml":
            packages, edges = parse_pyproject_toml(filepath)
        else:
            return

        for pkg in packages.values():
            if pkg.name not in graph.packages:
                graph.add_package(pkg)

        for edge in edges:
            graph.add_edge(edge)

    except Exception as e:
        print(f"Warning: Could not parse {filepath}: {e}", file=sys.stderr)


def determine_overall_status(report: FullReport) -> HealthStatus:
    """Determine overall health status from sub-reports."""
    has_emergency = False
    has_alert = False
    has_warning = False

    # Check N-1
    if report.n1_report:
        if report.n1_report.compliance_score < 50:
            has_emergency = True
        elif report.n1_report.compliance_score < 80:
            has_alert = True
        elif report.n1_report.compliance_score < 95:
            has_warning = True

    # Check voltage
    if report.voltage_report:
        for vr in report.voltage_report.package_results:
            if vr.collapse_proximity_index < 0.1:
                has_emergency = True
            elif vr.collapse_proximity_index < 0.3:
                has_alert = True
            elif vr.is_sagging:
                has_warning = True

    # Check relay
    if report.relay_report:
        if report.relay_report.blind_spots:
            has_warning = True
        for v in report.relay_report.cti_violations:
            if v.violation_severity == "severe":
                has_alert = True

    # Check grid code
    for gc in report.grid_code_reports:
        if gc.overall_compliance.value == "fail":
            has_warning = True

    if has_emergency:
        return HealthStatus.EMERGENCY
    elif has_alert:
        return HealthStatus.ALERT
    elif has_warning:
        return HealthStatus.WARNING
    else:
        return HealthStatus.NORMAL


def cmd_n1(args: argparse.Namespace) -> None:
    """Run N-1 contingency analysis."""
    graph = build_graph(args.project)
    if graph.package_count() == 0:
        print("No packages found. Check project path.", file=sys.stderr)
        sys.exit(1)

    analyzer = ContingencyAnalyzer(graph)
    n1_report = analyzer.analyze()

    full = FullReport(
        project_path=os.path.abspath(args.project),
        n1_report=n1_report,
    )
    full.overall_status = determine_overall_status(full)

    formatter = ReportFormatter()
    fmt = getattr(args, "format", "text")
    output = formatter.format_full_report(full, fmt=fmt)
    print(output)


def cmd_frequency(args: argparse.Namespace) -> None:
    """Run frequency monitoring analysis."""
    graph = build_graph(args.project)
    if graph.package_count() == 0:
        print("No packages found. Check project path.", file=sys.stderr)
        sys.exit(1)

    monitor = FrequencyMonitor(graph)

    if args.shock:
        shock = VersionShock(
            package=args.shock,
            severity=1.0,
            is_breaking=True,
        )
        freq_report = monitor.analyze([shock])
    else:
        freq_report = monitor.analyze()

    full = FullReport(
        project_path=os.path.abspath(args.project),
        frequency_report=freq_report,
    )
    full.overall_status = determine_overall_status(full)

    formatter = ReportFormatter()
    fmt = getattr(args, "format", "text")
    output = formatter.format_full_report(full, fmt=fmt)
    print(output)


def cmd_dispatch(args: argparse.Namespace) -> None:
    """Run optimal dependency dispatch."""
    graph = build_graph(args.project)
    if graph.package_count() == 0:
        print("No packages found. Check project path.", file=sys.stderr)
        sys.exit(1)

    optimizer = FlowOptimizer(graph)
    opf_report = optimizer.optimize()

    full = FullReport(
        project_path=os.path.abspath(args.project),
        opf_report=opf_report,
    )
    full.overall_status = determine_overall_status(full)

    formatter = ReportFormatter()
    fmt = getattr(args, "format", "text")
    output = formatter.format_full_report(full, fmt=fmt)
    print(output)


def cmd_relay(args: argparse.Namespace) -> None:
    """Run protection coordination analysis."""
    graph = build_graph(args.project)
    if graph.package_count() == 0:
        print("No packages found. Check project path.", file=sys.stderr)
        sys.exit(1)

    coordinator = RelayCoordinator(graph)
    relay_report = coordinator.analyze()

    full = FullReport(
        project_path=os.path.abspath(args.project),
        relay_report=relay_report,
    )
    full.overall_status = determine_overall_status(full)

    formatter = ReportFormatter()
    fmt = getattr(args, "format", "text")
    output = formatter.format_full_report(full, fmt=fmt)
    print(output)


def cmd_voltage(args: argparse.Namespace) -> None:
    """Run voltage/capability analysis."""
    graph = build_graph(args.project)
    if graph.package_count() == 0:
        print("No packages found. Check project path.", file=sys.stderr)
        sys.exit(1)

    analyst = VoltageAnalyst(graph)
    voltage_report = analyst.analyze()

    full = FullReport(
        project_path=os.path.abspath(args.project),
        voltage_report=voltage_report,
    )
    full.overall_status = determine_overall_status(full)

    formatter = ReportFormatter()
    fmt = getattr(args, "format", "text")
    output = formatter.format_full_report(full, fmt=fmt)
    print(output)


def cmd_inspect(args: argparse.Namespace) -> None:
    """Run IEEE 1547 interconnection compliance inspection."""
    # Inspect can work on a single package or a project
    graph = build_graph(args.project)
    if graph.package_count() == 0:
        print("No packages found. Check project path.", file=sys.stderr)
        sys.exit(1)

    inspector = GridCodeInspector(graph)

    if args.package:
        reports = [inspector.inspect_package(args.package)]
    else:
        reports = inspector.inspect_all()

    full = FullReport(
        project_path=os.path.abspath(args.project),
        grid_code_reports=reports,
    )
    full.overall_status = determine_overall_status(full)

    formatter = ReportFormatter()
    fmt = getattr(args, "format", "text")
    output = formatter.format_full_report(full, fmt=fmt)
    print(output)


def cmd_report(args: argparse.Namespace) -> None:
    """Generate a full Grid Reliability Assessment."""
    graph = build_graph(args.project)
    if graph.package_count() == 0:
        print("No packages found. Check project path.", file=sys.stderr)
        sys.exit(1)

    # Run all analyses
    n1_report = ContingencyAnalyzer(graph).analyze()
    freq_report = FrequencyMonitor(graph).analyze()
    opf_report = FlowOptimizer(graph).optimize()
    relay_report = RelayCoordinator(graph).analyze()
    voltage_report = VoltageAnalyst(graph).analyze()
    grid_code_reports = GridCodeInspector(graph).inspect_all()

    full = FullReport(
        project_path=os.path.abspath(args.project),
        n1_report=n1_report,
        frequency_report=freq_report,
        opf_report=opf_report,
        relay_report=relay_report,
        voltage_report=voltage_report,
        grid_code_reports=grid_code_reports,
    )
    full.overall_status = determine_overall_status(full)

    formatter = ReportFormatter()
    fmt = getattr(args, "format", "text")
    output = formatter.format_full_report(full, fmt=fmt)
    print(output)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="gridiron",
        description="Gridiron — Power Grid Reliability Engineering for Dependency Ecosystem Health",
    )
    parser.add_argument(
        "--version", action="version", version=f"gridiron {__version__}"
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # n1
    n1_parser = subparsers.add_parser(
        "n1", help="N-1 contingency analysis — single-point-of-failure detection"
    )
    n1_parser.add_argument("project", help="Path to project directory or manifest file")
    n1_parser.set_defaults(func=cmd_n1)

    # frequency
    freq_parser = subparsers.add_parser(
        "frequency", help="Three-tier version shock response analysis"
    )
    freq_parser.add_argument("project", help="Path to project directory or manifest file")
    freq_parser.add_argument("--shock", help="Package causing version shock")
    freq_parser.set_defaults(func=cmd_frequency)

    # dispatch
    dispatch_parser = subparsers.add_parser(
        "dispatch", help="Optimal dependency dispatch (OPF)"
    )
    dispatch_parser.add_argument("project", help="Path to project directory or manifest file")
    dispatch_parser.add_argument(
        "--optimize", action="store_true", help="Run optimization"
    )
    dispatch_parser.set_defaults(func=cmd_dispatch)

    # relay
    relay_parser = subparsers.add_parser(
        "relay", help="Protection coordination across error handling layers"
    )
    relay_parser.add_argument("project", help="Path to project directory or manifest file")
    relay_parser.set_defaults(func=cmd_relay)

    # voltage
    voltage_parser = subparsers.add_parser(
        "voltage", help="Capability margin and collapse proximity analysis"
    )
    voltage_parser.add_argument("project", help="Path to project directory or manifest file")
    voltage_parser.set_defaults(func=cmd_voltage)

    # inspect
    inspect_parser = subparsers.add_parser(
        "inspect", help="IEEE 1547 interconnection compliance inspection"
    )
    inspect_parser.add_argument("project", help="Path to project directory or manifest file")
    inspect_parser.add_argument("--package", help="Inspect a specific package")
    inspect_parser.set_defaults(func=cmd_inspect)

    # report
    report_parser = subparsers.add_parser(
        "report", help="Generate full Grid Reliability Assessment"
    )
    report_parser.add_argument("project", help="Path to project directory or manifest file")
    report_parser.add_argument(
        "--full", action="store_true", help="Include all analyses"
    )
    report_parser.set_defaults(func=cmd_report)

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
