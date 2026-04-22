"""CLI interface for Sentinel.

Commands:
    init       Initialize a Sentinel project
    train      Build self-profile from source code
    generate   Generate detector population using negative selection
    check      Check code for anomalies
    feedback   Provide feedback on detections
    profile    Show learned self-profile
    export     Export detector population to JSON
    import     Import detector population from JSON
    watch      Watch mode (stub)
    diff       Compare two codebases (stub)
"""

import argparse
import json
import os
import sys

from . import __version__
from .checker import (
    AnomalyReport,
    check_directory,
    check_file,
    check_patterns,
    format_report,
)
from .db import SentinelDB
from .detectors import DetectorPopulation, apply_feedback, generate_detectors
from .profile import SelfProfile, build_profile, profile_file_summary


def get_db(project_dir: str = ".") -> SentinelDB:
    """Get a SentinelDB for the project directory."""
    sentinel_dir = os.path.join(project_dir, ".sentinel")
    os.makedirs(sentinel_dir, exist_ok=True)
    db_path = os.path.join(sentinel_dir, "sentinel.db")
    return SentinelDB(db_path)


def cmd_init(args):
    """Initialize a Sentinel project."""
    project_dir = args.directory or "."
    sentinel_dir = os.path.join(project_dir, ".sentinel")
    os.makedirs(sentinel_dir, exist_ok=True)

    # Create config file
    config = {
        "version": __version__,
        "granularity": "function",
        "matching_threshold": 0.3,
        "num_detectors": 1000,
        "metric": "euclidean",
        "source_path": args.source or ".",
    }
    config_path = os.path.join(sentinel_dir, "config.json")
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    # Initialize database
    db = get_db(project_dir)
    db.close()

    print(f"🛡️  Sentinel initialized in {os.path.abspath(project_dir)}")
    print(f"   Config: {config_path}")
    print(f"   Database: {os.path.join(sentinel_dir, 'sentinel.db')}")
    print("")
    print("Next steps:")
    print("  1. sentinel train <source_path>   # Build self-profile")
    print("  2. sentinel generate              # Generate detectors")
    print("  3. sentinel check <file_or_dir>   # Check for anomalies")


def cmd_train(args):
    """Build self-profile from source code."""
    source_path = args.source
    if not os.path.exists(source_path):
        print(f"Error: Source path does not exist: {source_path}", file=sys.stderr)
        return 1

    granularity = args.granularity or "function"
    name = args.name or os.path.basename(os.path.abspath(source_path))
    history = args.history or ""

    print(f"🧬 Training self-profile from {source_path}...")
    if history:
        print(f"   Including git history: {history}")
    print(f"   Granularity: {granularity}")

    profile = build_profile(source_path, granularity=granularity, history=history, name=name)

    # Save to database
    db = get_db(args.project or ".")
    profile_id = db.save_profile(profile, name=name)
    db.close()

    print(f"   Patterns extracted: {profile.num_patterns}")
    print(f"   Files analyzed: {profile.num_files}")
    print(f"   Profile saved as: {name}")
    print("")
    print(profile_file_summary(profile))

    return 0


def cmd_generate(args):
    """Generate detector population using negative selection."""
    db = get_db(args.project or ".")

    # Load profile
    profile_name = args.profile or "default"
    profile = db.load_profile(profile_name)
    if not profile:
        # Try to find any profile
        profiles = db.list_profiles()
        if profiles:
            profile_name = profiles[0]['name']
            profile = db.load_profile(profile_name)
        else:
            print("Error: No self-profile found. Run 'sentinel train' first.", file=sys.stderr)
            db.close()
            return 1

    num_detectors = args.detectors or 1000
    matching_threshold = args.matching_threshold or 0.3
    coverage = args.coverage or 0.95
    metric = args.metric or "euclidean"
    seed = args.seed

    print(f"🛡️  Generating detectors using negative selection...")
    print(f"   Self-corpus: {profile.num_patterns} patterns")
    print(f"   Target detectors: {num_detectors}")
    print(f"   Matching threshold: {matching_threshold}")
    print(f"   Metric: {metric}")

    self_vectors = profile.pattern_vectors()

    population = generate_detectors(
        self_vectors=self_vectors,
        num_detectors=num_detectors,
        matching_threshold=matching_threshold,
        metric=metric,
        coverage=coverage,
        seed=seed,
    )

    # Save to database
    pop_name = args.name or f"pop_{profile_name}"
    db.save_detectors(population, name=pop_name, profile_name=profile_name)
    db.close()

    print(f"   Detectors generated: {len(population.detectors)}")
    print(f"   Saved as: {pop_name}")

    return 0


def cmd_check(args):
    """Check code for anomalies."""
    target = args.target
    if not os.path.exists(target):
        print(f"Error: Target does not exist: {target}", file=sys.stderr)
        return 1

    db = get_db(args.project or ".")

    # Load detector population
    pop_name = args.population or None
    if pop_name:
        population = db.load_detectors(pop_name)
    else:
        # Try to find any population
        pops = db.list_detector_populations()
        if pops:
            pop_name = pops[0]['name']
            population = db.load_detectors(pop_name)
        else:
            print("Error: No detector population found. Run 'sentinel generate' first.",
                  file=sys.stderr)
            db.close()
            return 1

    # Load profile for context
    profiles = db.list_profiles()
    profile = None
    if profiles:
        profile = db.load_profile(profiles[0]['name'])
    db.close()

    threshold = args.threshold or 0.5
    metric = population.metric
    explain = args.explain or False
    granularity = args.granularity or "function"

    # Check target
    if os.path.isfile(target):
        report = check_file(target, population, granularity, threshold, metric)
        if profile:
            report.self_context = {
                "Self patterns": profile.num_patterns,
                "Self files": profile.num_files,
            }
        print(format_report(report, explain=explain))
        return 1 if report.is_anomalous else 0
    elif os.path.isdir(target):
        reports = check_directory(target, population, granularity, threshold, metric)
        total_anomalous = 0
        for report in reports:
            if profile:
                report.self_context = {
                    "Self patterns": profile.num_patterns,
                    "Self files": profile.num_files,
                }
            print(format_report(report, explain=explain))
            if report.is_anomalous:
                total_anomalous += 1
        print(f"\n{'─' * 50}")
        print(f"Summary: {len(reports)} files checked, {total_anomalous} anomalous")
        return 1 if total_anomalous > 0 else 0
    else:
        print(f"Error: Invalid target: {target}", file=sys.stderr)
        return 1


def cmd_profile(args):
    """Show learned self-profile."""
    db = get_db(args.project or ".")

    profile_name = args.name or None
    if profile_name:
        profile = db.load_profile(profile_name)
    else:
        profiles = db.list_profiles()
        if profiles:
            profile_name = profiles[0]['name']
            profile = db.load_profile(profile_name)
        else:
            print("Error: No profile found. Run 'sentinel train' first.", file=sys.stderr)
            db.close()
            return 1

    db.close()

    if profile:
        print(profile_file_summary(profile))
    else:
        print(f"Error: Profile '{profile_name}' not found.", file=sys.stderr)
        return 1

    return 0


def cmd_feedback(args):
    """Provide feedback on a detection."""
    detector_id = args.detector_id
    is_true_positive = args.true_positive

    db = get_db(args.project or ".")

    # Save feedback
    db.save_feedback(detector_id, is_true_positive, comment=args.comment or "")

    # Apply feedback to any population containing this detector
    pops = db.list_detector_populations()
    updated = False
    for pop_info in pops:
        population = db.load_detectors(pop_info['name'])
        detector = apply_feedback(detector_id, population, is_true_positive)
        if detector:
            db.save_detectors(population, name=pop_info['name'])
            updated = True
            kind = "true positive" if is_true_positive else "false positive"
            new_thresh = detector.threshold
            print(f"  ✓ Detector {detector_id} marked as {kind}")
            print(f"    New threshold: {new_thresh:.3f}")

    if not updated:
        print(f"  ⚠ Detector {detector_id} not found in any population")

    db.close()
    return 0


def cmd_export(args):
    """Export detector population to JSON."""
    db = get_db(args.project or ".")

    pop_name = args.name or None
    if pop_name:
        population = db.load_detectors(pop_name)
    else:
        pops = db.list_detector_populations()
        if pops:
            pop_name = pops[0]['name']
            population = db.load_detectors(pop_name)
        else:
            print("Error: No detector population found.", file=sys.stderr)
            db.close()
            return 1

    db.close()

    output_path = args.output or "detectors.json"
    with open(output_path, 'w') as f:
        json.dump(population.to_dict(), f, indent=2)

    print(f"  ✓ Exported {len(population.detectors)} detectors to {output_path}")
    return 0


def cmd_import(args):
    """Import detector population from JSON."""
    input_path = args.input
    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return 1

    with open(input_path, 'r') as f:
        data = json.load(f)

    population = DetectorPopulation.from_dict(data)

    pop_name = args.name or os.path.basename(input_path).replace('.json', '')
    db = get_db(args.project or ".")
    db.save_detectors(population, name=pop_name)
    db.close()

    print(f"  ✓ Imported {len(population.detectors)} detectors as '{pop_name}'")
    return 0


def cmd_watch(args):
    """Watch mode (stub)."""
    print("⚠️  sentinel watch is not yet implemented.")
    print("   Use 'sentinel check' for on-demand analysis.")
    print("   For pre-commit integration, add to .pre-commit-config.yaml:")
    print("     - repo: local")
    print("       hooks:")
    print("         - id: sentinel-check")
    print("           name: Sentinel Check")
    print("           entry: sentinel check")
    print("           language: system")
    return 0


def cmd_diff(args):
    """Compare two codebases (stub)."""
    print("⚠️  sentinel diff is not yet implemented.")
    print("   Train profiles on both codebases and compare feature statistics manually.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="sentinel",
        description="🛡️  Sentinel — Immunological Code Governance",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init
    p_init = subparsers.add_parser("init", help="Initialize a Sentinel project")
    p_init.add_argument("directory", nargs="?", default=".", help="Project directory")
    p_init.add_argument("--source", default=".", help="Source code path")

    # train
    p_train = subparsers.add_parser("train", help="Build self-profile from source code")
    p_train.add_argument("source", help="Source code directory")
    p_train.add_argument("--history", default="", help="Git history duration (e.g., 6m)")
    p_train.add_argument("--granularity", choices=["function", "class", "module"],
                         default="function", help="Pattern granularity")
    p_train.add_argument("--name", default="", help="Profile name")
    p_train.add_argument("--project", default=".", help="Project directory")

    # generate
    p_gen = subparsers.add_parser("generate", help="Generate detector population")
    p_gen.add_argument("--detectors", type=int, default=1000, help="Number of detectors")
    p_gen.add_argument("--coverage", type=float, default=0.95, help="Target coverage")
    p_gen.add_argument("--matching-threshold", type=float, default=0.3,
                       help="Matching threshold")
    p_gen.add_argument("--metric", choices=["euclidean", "manhattan", "hamming", "cosine"],
                       default="euclidean", help="Distance metric")
    p_gen.add_argument("--profile", default="", help="Profile name")
    p_gen.add_argument("--name", default="", help="Population name")
    p_gen.add_argument("--seed", type=int, default=None, help="Random seed")
    p_gen.add_argument("--project", default=".", help="Project directory")

    # check
    p_check = subparsers.add_parser("check", help="Check code for anomalies")
    p_check.add_argument("target", help="File or directory to check")
    p_check.add_argument("--threshold", type=float, default=0.5, help="Anomaly threshold")
    p_check.add_argument("--explain", action="store_true", help="Show explanations")
    p_check.add_argument("--population", default="", help="Detector population name")
    p_check.add_argument("--granularity", choices=["function", "class", "module"],
                         default="function", help="Pattern granularity")
    p_check.add_argument("--project", default=".", help="Project directory")

    # profile
    p_profile = subparsers.add_parser("profile", help="Show learned self-profile")
    p_profile.add_argument("--name", default="", help="Profile name")
    p_profile.add_argument("--project", default=".", help="Project directory")

    # feedback
    p_feedback = subparsers.add_parser("feedback", help="Provide feedback on detections")
    p_feedback.add_argument("detector_id", help="Detector ID")
    p_feedback.add_argument("--true-positive", action="store_true", help="Mark as true positive")
    p_feedback.add_argument("--false-positive", action="store_true", help="Mark as false positive")
    p_feedback.add_argument("--comment", default="", help="Optional comment")
    p_feedback.add_argument("--project", default=".", help="Project directory")

    # export
    p_export = subparsers.add_parser("export", help="Export detectors to JSON")
    p_export.add_argument("--output", default="detectors.json", help="Output file")
    p_export.add_argument("--name", default="", help="Population name")
    p_export.add_argument("--project", default=".", help="Project directory")

    # import
    p_import = subparsers.add_parser("import", help="Import detectors from JSON")
    p_import.add_argument("input", help="Input JSON file")
    p_import.add_argument("--name", default="", help="Population name")
    p_import.add_argument("--project", default=".", help="Project directory")

    # watch
    p_watch = subparsers.add_parser("watch", help="Watch mode (stub)")
    p_watch.add_argument("--pre-commit", action="store_true", help="Pre-commit mode")
    p_watch.add_argument("--ci", action="store_true", help="CI mode")

    # diff
    p_diff = subparsers.add_parser("diff", help="Compare codebases (stub)")
    p_diff.add_argument("project_a", help="First project")
    p_diff.add_argument("project_b", help="Second project")

    return parser


def main(argv=None):
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    cmd_map = {
        "init": cmd_init,
        "train": cmd_train,
        "generate": cmd_generate,
        "check": cmd_check,
        "profile": cmd_profile,
        "feedback": cmd_feedback,
        "export": cmd_export,
        "import": cmd_import,
        "watch": cmd_watch,
        "diff": cmd_diff,
    }

    handler = cmd_map.get(args.command)
    if handler:
        return handler(args) or 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
