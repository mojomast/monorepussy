"""Mint CLI — Numismatic Package Provenance & Version Classification.

Commands:
  mint grade <package>       Grade a package on the Sheldon scale
  mint hoard <lockfile>      Analyze a lockfile for dependency clusters
  mint authenticate <package> Authenticate a package for counterfeits
  mint debasement <package>  Track debasement curve for a package
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from mint import __version__
from mint.models import (
    MintMark,
    PackageInfo,
    ProvenanceLevel,
    get_grade_label,
    get_grade_category,
)
from mint.sheldon import (
    sheldon_grade,
    grade_package,
    grade_breakdown,
    compute_strike_quality,
    compute_surface_preservation,
    compute_luster,
    compute_eye_appeal,
)
from mint.composition import compute_fineness, compute_composition
from mint.counterfeit import (
    authenticate_package,
    CounterfeitType,
    Severity,
)
from mint.debasement import (
    analyze_debasement,
    format_debasement_report,
    format_debasement_bar,
)
from mint.hoard import (
    analyze_hoard,
    format_hoard_report,
)
from mint.lockfile import parse_package_lock_json, extract_package_names
from mint.provenance import (
    create_provenance_chain,
    determine_provenance_level,
    format_provenance_report,
)


# Known popular packages for typosquat detection
POPULAR_PACKAGES = [
    "express", "lodash", "react", "axios", "moment",
    "underscore", "jquery", "bootstrap", "vue", "angular",
    "webpack", "babel", "eslint", "typescript", "jest",
    "mocha", "chalk", "commander", "inquirer", "dotenv",
    "mongoose", "sequelize", "prisma", "next", "nuxt",
    "gulp", "grunt", "rollup", "vite", "esbuild",
    "socket.io", "passport", "bcrypt", "jsonwebtoken",
    "aws-sdk", "azure", "google-cloud", "firebase",
    "eslint-config", "tslib", "rxjs", "zone.js",
    "npm", "yarn", "pnpm",
]


def _parse_package_spec(spec: str) -> tuple[str, str]:
    """Parse a package spec like 'lodash@4.17.21' into (name, version)."""
    if "@" in spec and not spec.startswith("@"):
        parts = spec.rsplit("@", 1)
        return parts[0], parts[1]
    elif spec.startswith("@") and spec.count("@") > 1:
        # Scoped package like @scope/name@version
        parts = spec.rsplit("@", 1)
        return parts[0], parts[1]
    return spec, "latest"


def _build_sample_package_info(name: str, version: str) -> PackageInfo:
    """Build a sample PackageInfo for demo/CLI grading.

    In a production system, this would fetch real data from registries.
    For the CLI MVP, we simulate based on heuristics.
    """
    pkg = PackageInfo(name=name, version=version)

    # Heuristic scoring based on package characteristics
    # In real implementation, these would come from registry API and source analysis
    is_popular = name in POPULAR_PACKAGES or name.replace("@", "").split("/")[0] in ["react", "angular", "vue"]

    # Strike quality — build integrity
    pkg.strike_quality = compute_strike_quality(
        reproducible_build=is_popular,
        api_surface_match=0.95 if is_popular else 0.7,
        type_coverage=0.8 if is_popular else 0.4,
    )

    # Surface preservation — API maintenance
    pkg.surface_preservation = compute_surface_preservation(
        deprecated_ratio=0.02 if is_popular else 0.15,
        avg_issue_age_days=30 if is_popular else 120,
        pr_merge_latency_days=5 if is_popular else 30,
        changelog_completeness=0.9 if is_popular else 0.5,
    )

    # Luster — documentation
    pkg.luster = compute_luster(
        doc_freshness=0.85 if is_popular else 0.5,
        type_def_coverage=0.9 if is_popular else 0.3,
        example_completeness=0.8 if is_popular else 0.4,
        readme_quality=0.9 if is_popular else 0.5,
    )

    # Eye appeal — developer experience
    pkg.eye_appeal = compute_eye_appeal(
        install_size_efficiency=0.8 if is_popular else 0.6,
        startup_time=0.85 if is_popular else 0.6,
        import_clarity=0.9 if is_popular else 0.7,
        error_message_quality=0.8 if is_popular else 0.5,
    )

    # Composition
    pkg.composition = compute_composition(
        own_loc=5000 if is_popular else 1000,
        vendored_loc=200 if is_popular else 100,
        bundled_loc=0,
        transitive_depth=3 if is_popular else 1,
    )

    # Mint mark
    pkg.mint_mark = MintMark(
        registry="npm",
        publisher=name + "-team" if is_popular else "unknown",
    )

    return pkg


def cmd_grade(args: argparse.Namespace) -> int:
    """Handle the 'grade' command."""
    spec = getattr(args, "package", "")
    if not spec:
        print("Error: package specification required (e.g., lodash@4.17.21)")
        return 1

    name, version = _parse_package_spec(spec)
    pkg = _build_sample_package_info(name, version)
    grade_package(pkg)

    # Get grade breakdown
    bd = grade_breakdown(
        pkg.strike_quality,
        pkg.surface_preservation,
        pkg.luster,
        pkg.eye_appeal,
    )

    # Output
    print(f"{name}@{version}: {pkg.grade_label}")
    print(f"  Strike: {bd['strike_70']}/70  Surface: {bd['surface_70']}/70  "
          f"Luster: {bd['luster_70']}/70  Eye Appeal: {bd['eye_appeal_70']}/70")
    print(f"  Fineness: {pkg.composition.own_code_ratio:.3f}  "
          f"Origin: {pkg.mint_mark.registry}/{pkg.mint_mark.publisher}")

    # Provenance level
    prov_level = determine_provenance_level(pkg.provenance_chain)
    print(f"  Provenance: Level {int(prov_level)}")

    return 0


def cmd_hoard(args: argparse.Namespace) -> int:
    """Handle the 'hoard' command."""
    lockfile_path = getattr(args, "lockfile", "")
    if not lockfile_path:
        print("Error: lockfile path required")
        return 1

    try:
        packages = parse_package_lock_json(lockfile_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    if not packages:
        print("No packages found in lockfile")
        return 0

    hoards = analyze_hoard(packages)
    report = format_hoard_report(hoards, len(packages))
    print(report)

    # Check for counterfeits
    pkg_names = extract_package_names(packages)
    counterfeit_found = False
    for pkg_name in pkg_names:
        findings = authenticate_package(
            pkg_name,
            known_packages=POPULAR_PACKAGES,
        )
        for f in findings:
            if f.counterfeit_type == CounterfeitType.TYPOSQUAT:
                if not counterfeit_found:
                    print()
                print(f'  ⚠️ Potential counterfeit: {f.description}')
                counterfeit_found = True

    return 0


def cmd_authenticate(args: argparse.Namespace) -> int:
    """Handle the 'authenticate' command."""
    spec = getattr(args, "package", "")
    lockfile_path = getattr(args, "lockfile", None)

    if lockfile_path:
        # Authenticate all packages in a lockfile
        try:
            packages = parse_package_lock_json(lockfile_path)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1

        pkg_names = extract_package_names(packages)
        print(f"Scanning {len(pkg_names)} packages...")

        any_findings = False
        for pkg_name in pkg_names:
            findings = authenticate_package(
                pkg_name,
                known_packages=POPULAR_PACKAGES,
            )
            for f in findings:
                if f.severity in (Severity.CRITICAL, Severity.WARNING):
                    icon = "✗" if f.severity == Severity.CRITICAL else "⚠"
                    print(f"  {icon} {f.package} — {f.description}")
                    any_findings = True

        if not any_findings:
            print("  ✓ No counterfeits detected")

    elif spec:
        # Authenticate a single package
        name, version = _parse_package_spec(spec)
        findings = authenticate_package(
            name,
            version=version,
            known_packages=POPULAR_PACKAGES,
        )

        if findings:
            for f in findings:
                icon = "✗" if f.severity == Severity.CRITICAL else "⚠"
                print(f"  {icon} {f.package} — {f.description} (confidence: {f.confidence:.1%})")
        else:
            print(f"  ✓ {name}: No counterfeit indicators detected")
    else:
        print("Error: provide a package name or --lockfile path")
        return 1

    return 0


def cmd_debasement(args: argparse.Namespace) -> int:
    """Handle the 'debasement' command."""
    spec = getattr(args, "package", "")
    if not spec:
        print("Error: package name required")
        return 1

    name = spec.split("@")[0] if "@" in spec and not spec.startswith("@") else spec

    # Generate sample version history for demonstration
    # In production, this would fetch real version history from the registry
    from datetime import timedelta
    base_date = datetime(2020, 1, 1, tzinfo=timezone.utc)

    # Simulate a typical debasement curve
    versions = [
        (f"{name}@4.0.0", 65, base_date),
        (f"{name}@4.5.0", 63, base_date + timedelta(days=180)),
        (f"{name}@4.10.0", 60, base_date + timedelta(days=400)),
        (f"{name}@4.15.0", 58, base_date + timedelta(days=600)),
        (f"{name}@4.17.0", 55, base_date + timedelta(days=800)),
        (f"{name}@4.17.21", 52, base_date + timedelta(days=1000)),
    ]

    curve = analyze_debasement(name, versions)
    report = format_debasement_report(curve)
    print(report)

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the Mint CLI."""
    parser = argparse.ArgumentParser(
        prog="mint",
        description="Mint — Numismatic Package Provenance & Version Classification",
    )
    parser.add_argument(
        "--version", action="version", version=f"mint {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # grade command
    grade_parser = subparsers.add_parser(
        "grade", help="Grade a package on the Sheldon scale"
    )
    grade_parser.add_argument(
        "package", nargs="?", default="",
        help="Package specification (e.g., lodash@4.17.21)"
    )

    # hoard command
    hoard_parser = subparsers.add_parser(
        "hoard", help="Analyze a lockfile for dependency clusters"
    )
    hoard_parser.add_argument(
        "lockfile", nargs="?", default="",
        help="Path to package-lock.json"
    )

    # authenticate command
    auth_parser = subparsers.add_parser(
        "authenticate", help="Authenticate a package for counterfeits"
    )
    auth_parser.add_argument(
        "package", nargs="?", default="",
        help="Package name to authenticate"
    )
    auth_parser.add_argument(
        "--lockfile", dest="lockfile",
        help="Path to lockfile to scan for counterfeits"
    )

    # debasement command
    deb_parser = subparsers.add_parser(
        "debasement", help="Track debasement curve for a package"
    )
    deb_parser.add_argument(
        "package", nargs="?", default="",
        help="Package name to track"
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the Mint CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    command = getattr(args, "command", None)
    if not command:
        parser.print_help()
        return 0

    commands = {
        "grade": cmd_grade,
        "hoard": cmd_hoard,
        "authenticate": cmd_authenticate,
        "debasement": cmd_debasement,
    }

    handler = commands.get(command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
