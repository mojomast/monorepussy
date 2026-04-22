"""Portmore CLI — Customs & Tariff Classification for Software License Compliance."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from portmore import __version__
from portmore.classifier import classify_licenses
from portmore.compatibility import check_compatibility
from portmore.contagion import assess_contagion
from portmore.formatter import (
    format_compatibility,
    format_contagion,
    format_origin,
    format_quarantine,
    format_resolution,
    format_valuation,
)
from portmore.origin import determine_origin
from portmore.quarantine import generate_quarantine_report
from portmore.scanner import scan_project
from portmore.valuation import compute_valuation_hierarchy


def cmd_classify(args: argparse.Namespace) -> int:
    """Classify a project's licenses using GIRs."""
    project_path = args.project
    info = scan_project(project_path)

    if not info.licenses or info.licenses == ["UNKNOWN"]:
        print("No licenses detected in project.", file=sys.stderr)
        return 1

    resolution = classify_licenses(
        licenses=info.licenses,
        project_license=info.licenses[0] if info.licenses else None,
    )

    fmt = getattr(args, "format", "text")
    print(format_resolution(resolution, fmt=fmt))
    return 0


def cmd_origin(args: argparse.Namespace) -> int:
    """Determine provenance using rules of origin."""
    project_path = args.project
    info = scan_project(project_path)

    threshold = getattr(args, "threshold", 0.40)
    deminimis = getattr(args, "deminimis", 0.05)
    fmt = getattr(args, "format", "text")

    if not info.modules:
        # Use the project as a single module
        det = determine_origin(
            module=info.name,
            third_party_ratio=0.0,
            modification_ratio=0.0,
            original_hs_code="",
            modified_hs_code="",
            threshold=threshold,
            deminimis_threshold=deminimis,
        )
        print(format_origin(det, fmt=fmt))
        return 0

    for module in info.modules[:10]:  # Limit to first 10 modules
        det = determine_origin(
            module=module,
            third_party_ratio=0.0,
            modification_ratio=0.0,
            original_hs_code="",
            modified_hs_code="",
            threshold=threshold,
            deminimis_threshold=deminimis,
        )
        print(format_origin(det, fmt=fmt))
        print()

    return 0


def cmd_compatibility(args: argparse.Namespace) -> int:
    """Check license compatibility with PTA-style exceptions."""
    from_license = getattr(args, "from_license", "")
    to_license = getattr(args, "to_license", "")
    usage_type = getattr(args, "usage_type", "static")
    fmt = getattr(args, "format", "text")

    if not from_license or not to_license:
        print("Both --from and --to license identifiers are required.", file=sys.stderr)
        return 1

    result = check_compatibility(from_license, to_license, usage_type=usage_type)
    print(format_compatibility(result, fmt=fmt))
    return 0


def cmd_value(args: argparse.Namespace) -> int:
    """Assess compliance cost using customs valuation methods."""
    project_path = getattr(args, "project", "")
    fmt = getattr(args, "format", "text")

    if project_path:
        info = scan_project(project_path)
        license_id = info.licenses[0] if info.licenses else "UNKNOWN"
    else:
        license_id = getattr(args, "license", "MIT")

    project_value = getattr(args, "project_value", 0.0)
    development_cost = getattr(args, "development_cost", 0.0)

    hierarchy = compute_valuation_hierarchy(
        license_id=license_id,
        project_value=project_value,
        development_cost=development_cost,
    )

    print(format_valuation(hierarchy, fmt=fmt))
    return 0


def cmd_contagion(args: argparse.Namespace) -> int:
    """Assess copyleft contagion using anti-dumping framework."""
    copyleft_license = getattr(args, "copyleft", "GPL-3.0")
    copyleft_ratio = getattr(args, "ratio", 0.0)
    linkage = getattr(args, "linkage", "static")
    fmt = getattr(args, "format", "text")

    assessment = assess_contagion(
        license_id=copyleft_license,
        copyleft_ratio=copyleft_ratio,
        linkage_type=linkage,
    )

    print(format_contagion(assessment, fmt=fmt))
    return 0


def cmd_quarantine(args: argparse.Namespace) -> int:
    """Check dependency quarantine status."""
    project_path = getattr(args, "project", "")
    fmt = getattr(args, "format", "text")
    check = getattr(args, "check", False)

    if not project_path:
        print("Project path is required for quarantine check.", file=sys.stderr)
        return 1

    info = scan_project(project_path)

    # Build dependency list
    dependencies: list[dict] = []
    for dep in info.dependencies:
        dependencies.append({
            "name": dep,
            "is_dev_only": False,
            "license_id": "",
        })
    for dep in info.dev_dependencies:
        dependencies.append({
            "name": dep,
            "is_dev_only": True,
            "license_id": "",
        })

    if not dependencies:
        print("No dependencies detected in project.", file=sys.stderr)
        return 1

    report = generate_quarantine_report(dependencies)
    print(format_quarantine(report, fmt=fmt))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="portmore",
        description="Portmore — Customs & Tariff Classification for Software License Compliance",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # classify
    classify_parser = subparsers.add_parser("classify", help="Classify licenses using GIRs")
    classify_parser.add_argument("project", help="Path to project directory")
    classify_parser.add_argument("--format", choices=["text", "json"], default="text",
                                help="Output format")

    # origin
    origin_parser = subparsers.add_parser("origin", help="Determine provenance")
    origin_parser.add_argument("project", help="Path to project directory")
    origin_parser.add_argument("--threshold", type=float, default=0.40,
                              help="Value-added threshold (default: 0.40)")
    origin_parser.add_argument("--deminimis", type=float, default=0.05,
                              help="De minimis threshold (default: 0.05)")
    origin_parser.add_argument("--format", choices=["text", "json"], default="text",
                              help="Output format")

    # compatibility
    compat_parser = subparsers.add_parser("compatibility", help="Check license compatibility")
    compat_parser.add_argument("--from", dest="from_license", required=True,
                              help="Source license SPDX ID")
    compat_parser.add_argument("--to", dest="to_license", required=True,
                              help="Target license SPDX ID")
    compat_parser.add_argument("--usage-type", default="static",
                              choices=["static", "dynamic", "socket", "api",
                                       "microservice", "plugin"],
                              help="Usage/linkage type")
    compat_parser.add_argument("--format", choices=["text", "json"], default="text",
                              help="Output format")

    # value
    value_parser = subparsers.add_parser("value", help="Assess compliance cost")
    value_parser.add_argument("--project", default="", help="Path to project directory")
    value_parser.add_argument("--license", default="MIT", help="License SPDX ID")
    value_parser.add_argument("--project-value", type=float, default=0.0,
                             help="Estimated project value")
    value_parser.add_argument("--development-cost", type=float, default=0.0,
                             help="Development cost")
    value_parser.add_argument("--format", choices=["text", "json"], default="text",
                             help="Output format")

    # contagion
    contagion_parser = subparsers.add_parser("contagion", help="Assess copyleft contagion")
    contagion_parser.add_argument("--copyleft", default="GPL-3.0",
                                 help="Copyleft license SPDX ID")
    contagion_parser.add_argument("--ratio", type=float, default=0.0,
                                 help="Copyleft code ratio (0.0-1.0)")
    contagion_parser.add_argument("--linkage", default="static",
                                 choices=["static", "dynamic", "socket", "api",
                                          "microservice", "plugin"],
                                 help="Linkage type")
    contagion_parser.add_argument("--format", choices=["text", "json"], default="text",
                                 help="Output format")

    # quarantine
    quarantine_parser = subparsers.add_parser("quarantine", help="Check dependency quarantine")
    quarantine_parser.add_argument("project", help="Path to project directory")
    quarantine_parser.add_argument("--check", action="store_true",
                                  help="Perform boundary violation check")
    quarantine_parser.add_argument("--format", choices=["text", "json"], default="text",
                                  help="Output format")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the Portmore CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    command = getattr(args, "command", None)
    if not command:
        parser.print_help()
        return 0

    commands = {
        "classify": cmd_classify,
        "origin": cmd_origin,
        "compatibility": cmd_compatibility,
        "value": cmd_value,
        "contagion": cmd_contagion,
        "quarantine": cmd_quarantine,
    }

    handler = commands.get(command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
