"""CLI interface for Endemic."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from endemic import __version__
from endemic.models import (
    Compartment,
    Module,
    Pattern,
    PatternType,
)
from endemic.scanner import PatternScanner
from endemic.r0 import compute_r0_for_patterns, determine_status, estimate_r0_from_tree
from endemic.sir_model import simulate_sir, simulate_with_intervention
from endemic.herd_immunity import (
    calculate_herd_immunity,
    generate_vaccination_strategies,
    calculate_combined_effort,
)
from endemic.superspreader import (
    identify_superspreader_modules,
    identify_superspreader_developers,
    identify_superspreader_events,
)
from endemic.zoonotic import detect_zoonotic_jumps, format_zoonotic_alert, infer_domain
from endemic.promote import promote_pattern
from endemic.git_tracer import GitTracer
from endemic.report import (
    format_scan_report,
    format_trace_report,
    format_herd_immunity_report,
    format_simulation_report,
    format_promote_report,
)


def cmd_scan(args):
    """Scan a codebase for propagating patterns."""
    scanner = PatternScanner()
    scan_results = scanner.scan_path(args.path)

    if not scan_results:
        print("No patterns detected in the specified path.")
        return

    # Count total source files
    import os
    from pathlib import Path
    total_files = 0
    p = Path(args.path)
    if p.is_file():
        total_files = 1
    else:
        for root, dirs, files in os.walk(str(p)):
            dirs[:] = [d for d in dirs if not d.startswith(".")
                       and d not in ("node_modules", "__pycache__", ".git", "venv", ".venv")]
            for f in files:
                ext = Path(f).suffix
                if ext in (".py", ".pyw", ".js", ".ts", ".java", ".go", ".rs", ".rb", ".c", ".cpp", ".h"):
                    total_files += 1

    # Build modules and compute stats
    modules = scanner.build_modules(scan_results, total_modules=total_files)
    patterns = scanner.compute_pattern_stats(scan_results, total_modules=total_files)

    # Assign domains to modules
    for m in modules:
        if not m.domain:
            m.domain = infer_domain(m.path)

    # Compute R0
    patterns = compute_r0_for_patterns(patterns)

    # Trace git history if available
    tracer = GitTracer(args.path if Path(args.path).is_dir() else str(Path(args.path).parent))
    trees = {}
    if tracer._git_available:
        since = args.history if hasattr(args, "history") and args.history else None
        for pattern in patterns:
            if pattern.regex_pattern:
                tree = tracer.trace_pattern(pattern.name, pattern.regex_pattern, since=since)
                if tree.events:
                    trees[pattern.name] = tree

    # Identify superspreaders
    ss_modules = []
    ss_devs = []
    ss_events = []
    for tree in trees.values():
        ss_modules.extend(identify_superspreader_modules(tree))
        ss_devs.extend(identify_superspreader_developers(tree))
        ss_events.extend(identify_superspreader_events(tree))

    # Deduplicate
    seen_modules = set()
    unique_ss_modules = []
    for mod, count in ss_modules:
        if mod not in seen_modules:
            seen_modules.add(mod)
            unique_ss_modules.append((mod, count))

    report = format_scan_report(
        patterns=patterns,
        total_modules=total_files,
        superspreader_modules=unique_ss_modules[:3],
        superspreader_devs=ss_devs[:3],
        superspreader_events=ss_events[:2],
    )
    print(report)


def cmd_trace(args):
    """Trace the transmission history of a pattern."""
    scanner = PatternScanner()

    # Find the pattern
    pattern = None
    for p in scanner.patterns:
        if p.name == args.pattern:
            pattern = p
            break

    if pattern is None:
        print(f"Pattern '{args.pattern}' not found. Available patterns:")
        for p in scanner.patterns:
            print(f"  - {p.name}")
        return

    # Trace via git
    repo_path = args.path if args.path else "."
    tracer = GitTracer(repo_path)
    tree = tracer.trace_pattern(pattern.name, pattern.regex_pattern)

    if not tree.events and not tree.index_case:
        print(f"No transmission history found for '{args.pattern}'.")
        print("Make sure you're running from a git repository with history.")
        return

    r0 = estimate_r0_from_tree(tree)
    report = format_trace_report(tree, r0)
    print(report)


def cmd_simulate(args):
    """Simulate pattern spread using SIR model."""
    # Parse parameters
    r0 = args.r0 if args.r0 else 1.0
    n = args.population if args.population else 50

    # Scan to get current prevalence
    scanner = PatternScanner()
    if args.path:
        scan_results = scanner.scan_path(args.path)
        if scan_results:
            n = max(n, len(scan_results))

            # Find pattern-specific prevalence
            if args.pattern:
                infected = sum(
                    1 for file_patterns in scan_results.values()
                    if args.pattern in file_patterns
                )
            else:
                infected = sum(
                    1 for file_patterns in scan_results.values() if file_patterns
                )
        else:
            infected = max(1, n // 5)
    else:
        infected = max(1, n // 5)

    # Parse horizon
    horizon = 26  # default: 6 months in weeks
    if args.horizon:
        horizon = _parse_horizon(args.horizon)

    # Run simulation
    sim = simulate_sir(
        n=n,
        initial_infected=infected,
        initial_recovered=0,
        r0=r0,
        gamma=0.1,
        horizon_steps=horizon,
    )

    # Run with intervention if requested
    with_intervention = None
    if args.intervention_r0 is not None:
        intervention_step = horizon // 4  # Intervene at 25% of horizon
        _, with_intervention = simulate_with_intervention(
            n=n,
            initial_infected=infected,
            initial_recovered=0,
            r0=r0,
            gamma=0.1,
            intervention_step=intervention_step,
            intervention_r0=args.intervention_r0,
            horizon_steps=horizon,
        )

    report = format_simulation_report(
        sim=sim,
        pattern_name=args.pattern or "all patterns",
        with_intervention=with_intervention,
    )
    print(report)


def cmd_herd_immunity(args):
    """Calculate herd immunity threshold for a pattern."""
    # Get pattern info
    scanner = PatternScanner()
    pattern = None
    for p in scanner.patterns:
        if p.name == args.pattern:
            pattern = p
            break

    if pattern is None:
        # Create a pattern with the provided R0
        if args.r0:
            pattern = Pattern(name=args.pattern, r0=args.r0)
        else:
            print(f"Pattern '{args.pattern}' not found. Provide --r0 to analyze.")
            return

    # Scan for current state
    immune_count = 0
    total_modules = 0
    modules = []

    if args.path:
        scan_results = scanner.scan_path(args.path)
        if scan_results:
            total_modules = len(scan_results)
            # Count immune = modules without the pattern but with good patterns
            for file_patterns in scan_results.values():
                if args.pattern not in file_patterns:
                    immune_count += 1
            modules = scanner.build_modules(scan_results, total_modules=total_modules)
            for m in modules:
                if not m.domain:
                    m.domain = infer_domain(m.path)

    if args.r0:
        pattern.r0 = args.r0

    if total_modules == 0:
        total_modules = args.population or 50

    result = calculate_herd_immunity(pattern, immune_count, total_modules)

    # Generate strategies
    strategies = []
    if modules:
        strategies = generate_vaccination_strategies(result, modules)

    combined = None
    if strategies:
        infected_count = sum(1 for m in modules if pattern.name in m.patterns)
        combined = calculate_combined_effort(strategies, infected_count)

    report = format_herd_immunity_report(result, strategies, combined)
    print(report)


def cmd_watch(args):
    """Monitor for zoonotic jumps (cross-domain pattern spills)."""
    scanner = PatternScanner()

    if not args.path:
        print("Please provide a path to scan.")
        return

    scan_results = scanner.scan_path(args.path)
    if not scan_results:
        print("No patterns detected.")
        return

    # Build modules
    import os
    from pathlib import Path
    total_files = 0
    p = Path(args.path)
    if p.is_file():
        total_files = 1
    else:
        for root, dirs, files in os.walk(str(p)):
            dirs[:] = [d for d in dirs if not d.startswith(".")
                       and d not in ("node_modules", "__pycache__", ".git", "venv", ".venv")]
            for f in files:
                ext = Path(f).suffix
                if ext in (".py", ".pyw", ".js", ".ts", ".java", ".go", ".rs", ".rb", ".c", ".cpp", ".h"):
                    total_files += 1

    modules = scanner.build_modules(scan_results, total_modules=total_files)
    patterns = scanner.compute_pattern_stats(scan_results, total_modules=total_files)

    # Assign domains
    for m in modules:
        if not m.domain:
            m.domain = infer_domain(m.path)

    # Detect zoonotic jumps
    jumps = detect_zoonotic_jumps(modules, patterns)

    if not jumps:
        print("No zoonotic jumps detected. All patterns are contained within their domains.")
        return

    # Filter for zoonotic flag
    if args.zoonotic:
        jumps = [j for j in jumps if j.risk == "HIGH"]

    for jump in jumps:
        alert = format_zoonotic_alert(jump)
        print(alert)
        print()


def cmd_promote(args):
    """Analyze promotion strategy for a good pattern."""
    scanner = PatternScanner()

    # Find pattern
    pattern = None
    for p in scanner.patterns:
        if p.name == args.pattern:
            pattern = p
            break

    if pattern is None:
        print(f"Pattern '{args.pattern}' not found. Available good patterns:")
        for p in scanner.patterns:
            if p.pattern_type == PatternType.GOOD:
                print(f"  - {p.name}")
        return

    if pattern.pattern_type != PatternType.GOOD:
        print(f"Pattern '{args.pattern}' is not a good pattern. Use scan to analyze bad patterns.")
        return

    # Scan for current state
    modules = []
    if args.path:
        scan_results = scanner.scan_path(args.path)
        if scan_results:
            modules = scanner.build_modules(scan_results)
            for m in modules:
                if not m.domain:
                    m.domain = infer_domain(m.path)

    # Get R0 if available
    if args.r0:
        pattern.r0 = args.r0

    # Get bad patterns for cross-protection
    bad_patterns = [p for p in scanner.patterns if p.pattern_type == PatternType.BAD]

    # Run promotion analysis
    result = promote_pattern(
        pattern=pattern,
        modules=modules,
        bad_patterns=bad_patterns if modules else None,
        seed_path=args.seed,
    )

    report = format_promote_report(result)
    print(report)


def _parse_horizon(horizon_str: str) -> int:
    """Parse horizon string like '6months' into weeks."""
    horizon_lower = horizon_str.lower()
    if "month" in horizon_lower:
        try:
            months = int(horizon_lower.replace("months", "").replace("month", "").strip())
            return months * 4  # Approximate weeks
        except ValueError:
            return 24
    if "week" in horizon_lower:
        try:
            weeks = int(horizon_lower.replace("weeks", "").replace("week", "").strip())
            return weeks
        except ValueError:
            return 26
    if "day" in horizon_lower:
        try:
            days = int(horizon_lower.replace("days", "").replace("day", "").strip())
            return max(1, days // 7)
        except ValueError:
            return 26
    return 26


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="endemic",
        description="Endemic — Epidemiological Analysis of Code Pattern Propagation",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Scan codebase for propagating patterns")
    scan_parser.add_argument("path", help="Path to scan (file or directory)")
    scan_parser.add_argument("--history", help="Git history depth (e.g., '6months')", default=None)

    # trace
    trace_parser = subparsers.add_parser("trace", help="Trace transmission history of a pattern")
    trace_parser.add_argument("--pattern", required=True, help="Pattern name to trace")
    trace_parser.add_argument("--path", help="Repository path (default: current dir)", default=".")

    # simulate
    sim_parser = subparsers.add_parser("simulate", help="Simulate pattern spread using SIR model")
    sim_parser.add_argument("--pattern", help="Pattern name to simulate", default=None)
    sim_parser.add_argument("--r0", type=float, help="Basic reproduction number", default=None)
    sim_parser.add_argument("--population", type=int, help="Total module population", default=None)
    sim_parser.add_argument("--horizon", help="Simulation horizon (e.g., '6months')", default=None)
    sim_parser.add_argument("--intervention-r0", type=float, help="R0 after intervention", default=None)
    sim_parser.add_argument("--path", help="Path to scan for current state", default=None)

    # herd-immunity
    hi_parser = subparsers.add_parser("herd-immunity", help="Calculate herd immunity threshold")
    hi_parser.add_argument("--pattern", required=True, help="Pattern name")
    hi_parser.add_argument("--r0", type=float, help="R0 value (overrides scan)", default=None)
    hi_parser.add_argument("--population", type=int, help="Total module population", default=None)
    hi_parser.add_argument("--path", help="Path to scan for current state", default=None)

    # watch
    watch_parser = subparsers.add_parser("watch", help="Monitor for zoonotic jumps")
    watch_parser.add_argument("path", help="Path to scan")
    watch_parser.add_argument("--zoonotic", action="store_true", help="Only show high-risk zoonotic jumps")

    # promote
    promote_parser = subparsers.add_parser("promote", help="Promote a good pattern")
    promote_parser.add_argument("--pattern", required=True, help="Pattern name to promote")
    promote_parser.add_argument("--seed", help="Module to seed the pattern from", default=None)
    promote_parser.add_argument("--r0", type=float, help="Override R0 value", default=None)
    promote_parser.add_argument("--path", help="Path to scan for current state", default=None)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "scan": cmd_scan,
        "trace": cmd_trace,
        "simulate": cmd_simulate,
        "herd-immunity": cmd_herd_immunity,
        "watch": cmd_watch,
        "promote": cmd_promote,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
