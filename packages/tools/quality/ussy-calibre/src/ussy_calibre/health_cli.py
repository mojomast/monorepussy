"""Levain CLI — Fermentation Science for Test Suite Health.

Usage:
    levain health                     # Full culture health report
    levain hooch                      # Find stale tests
    levain rise                       # Check if tests are alive
    levain contamination              # Track flaky test spread
    levain feeding                    # Check feeding schedule adherence
    levain build [--time-limit 5]     # Build essential test subset
    levain thermal                    # Profile environment sensitivity
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional

from ussy_calibre import __version__
from ussy_calibre.models import TestOutcomeLevain as TestOutcome, TestResultLevain as TestResult
from ussy_calibre.parser import parse_junit_xml, run_pytest_with_junit
from ussy_calibre.formatter import output_report
from ussy_calibre.health import compute_health
from ussy_calibre.instruments.hooch import HoochDetector, HoochDetectorWithHistory
from ussy_calibre.instruments.rise import RiseMeter
from ussy_calibre.instruments.contamination import ContaminationTracker
from ussy_calibre.instruments.feeding import FeedingSchedule
from ussy_calibre.instruments.build import LevainBuild
from ussy_calibre.instruments.thermal import ThermalProfiler
from ussy_calibre.analyzer import analyze_assertion_quality, check_skip_staleness


def _create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="levain",
        description="🍞 Levain — Fermentation Science for Test Suite Health",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # health
    health_parser = subparsers.add_parser(
        "health", help="Full culture health report"
    )
    health_parser.add_argument(
        "--junit-xml", help="Path to JUnit XML results file"
    )
    health_parser.add_argument(
        "--test-path", default=".", help="Path to test directory"
    )

    # hooch
    hooch_parser = subparsers.add_parser(
        "hooch", help="Find stale/trivial tests (hooch)"
    )
    hooch_parser.add_argument(
        "--threshold", type=int, default=180,
        help="Days without failure to consider dead hooch (default: 180)"
    )
    hooch_parser.add_argument(
        "--module", help="Analyze specific module only"
    )
    hooch_parser.add_argument(
        "--junit-xml", help="Path to JUnit XML results file"
    )
    hooch_parser.add_argument(
        "--test-path", default=".", help="Path to test directory"
    )

    # rise
    rise_parser = subparsers.add_parser(
        "rise", help="Check if tests are alive (fermentation activity)"
    )
    rise_parser.add_argument(
        "--window", type=int, default=90,
        help="Analysis window in days (default: 90)"
    )
    rise_parser.add_argument(
        "--module", help="Analyze specific module only"
    )
    rise_parser.add_argument(
        "--junit-xml", help="Path to JUnit XML results file"
    )
    rise_parser.add_argument(
        "--test-path", default=".", help="Path to test directory"
    )

    # contamination
    cont_parser = subparsers.add_parser(
        "contamination", help="Track flaky test spread (epidemiology)"
    )
    cont_parser.add_argument(
        "--junit-xml", help="Path to JUnit XML results file"
    )
    cont_parser.add_argument(
        "--test-path", default=".", help="Path to test directory"
    )

    # feeding
    feed_parser = subparsers.add_parser(
        "feeding", help="Check feeding schedule adherence"
    )
    feed_parser.add_argument(
        "--module", help="Analyze specific module only"
    )
    feed_parser.add_argument(
        "--junit-xml", help="Path to JUnit XML results file"
    )
    feed_parser.add_argument(
        "--test-path", default=".", help="Path to test directory"
    )

    # build
    build_parser = subparsers.add_parser(
        "build", help="Build essential test subset (preferment)"
    )
    build_parser.add_argument(
        "--time-limit", type=float, default=5.0,
        help="Time limit in minutes (default: 5)"
    )
    build_parser.add_argument(
        "--change-scope", help="Module/path to focus on"
    )
    build_parser.add_argument(
        "--junit-xml", help="Path to JUnit XML results file"
    )
    build_parser.add_argument(
        "--test-path", default=".", help="Path to test directory"
    )

    # thermal
    thermal_parser = subparsers.add_parser(
        "thermal", help="Profile environment sensitivity"
    )
    thermal_parser.add_argument(
        "--junit-xml", help="Path to JUnit XML results file"
    )
    thermal_parser.add_argument(
        "--test-path", default=".", help="Path to test directory"
    )

    return parser


def _load_test_results(args) -> list[TestResult]:
    """Load test results from JUnit XML or by running pytest."""
    junit_xml = getattr(args, "junit_xml", None)
    test_path = getattr(args, "test_path", ".")

    if junit_xml and os.path.exists(junit_xml):
        return parse_junit_xml(junit_xml)

    # Try to run pytest
    results = run_pytest_with_junit(test_path)
    return results


def _cmd_health(args, json_output: bool) -> None:
    """Run full health report."""
    results = _load_test_results(args)
    if not results:
        print("No test results found. Provide --junit-xml or --test-path.", file=sys.stderr)
        sys.exit(1)

    report = compute_health(results)
    output_report(report.to_dict(), "health", json_output)


def _cmd_hooch(args, json_output: bool) -> None:
    """Run hooch detection."""
    results = _load_test_results(args)
    if not results:
        print("No test results found. Provide --junit-xml or --test-path.", file=sys.stderr)
        sys.exit(1)

    # Filter by module if specified
    module = getattr(args, "module", None)
    if module:
        results = [r for r in results if module in r.module]

    # Load source map if possible
    source_map = _build_source_map(results)

    detector = HoochDetector(dead_threshold_days=args.threshold)
    report = detector.detect(results, source_map)
    output_report(report.to_dict(), "hooch", json_output)


def _cmd_rise(args, json_output: bool) -> None:
    """Run rise meter."""
    results = _load_test_results(args)
    if not results:
        print("No test results found. Provide --junit-xml or --test-path.", file=sys.stderr)
        sys.exit(1)

    module = getattr(args, "module", None)
    if module:
        results = [r for r in results if module in r.module]

    meter = RiseMeter(window_days=args.window)
    report = meter.measure(results)
    output_report(report.to_dict(), "rise", json_output)


def _cmd_contamination(args, json_output: bool) -> None:
    """Run contamination tracking."""
    results = _load_test_results(args)
    if not results:
        print("No test results found. Provide --junit-xml or --test-path.", file=sys.stderr)
        sys.exit(1)

    # For contamination, we need multiple runs
    # If we only have one run, use it as a single data point
    tracker = ContaminationTracker()
    report = tracker.track([results])
    output_report(report.to_dict(), "contamination", json_output)


def _cmd_feeding(args, json_output: bool) -> None:
    """Run feeding schedule analysis."""
    results = _load_test_results(args)
    if not results:
        print("No test results found. Provide --junit-xml or --test-path.", file=sys.stderr)
        sys.exit(1)

    module = getattr(args, "module", None)
    if module:
        results = [r for r in results if module in r.module]

    schedule = FeedingSchedule()
    report = schedule.audit(results)
    output_report(report.to_dict(), "feeding", json_output)


def _cmd_build(args, json_output: bool) -> None:
    """Run levain build (preferment selection)."""
    results = _load_test_results(args)
    if not results:
        print("No test results found. Provide --junit-xml or --test-path.", file=sys.stderr)
        sys.exit(1)

    builder = LevainBuild(
        time_limit_minutes=args.time_limit,
    )
    change_scope = getattr(args, "change_scope", None)
    report = builder.build(results, change_scope=change_scope)
    output_report(report.to_dict(), "build", json_output)


def _cmd_thermal(args, json_output: bool) -> None:
    """Run thermal profiling."""
    results = _load_test_results(args)
    if not results:
        print("No test results found. Provide --junit-xml or --test-path.", file=sys.stderr)
        sys.exit(1)

    profiler = ThermalProfiler()
    report = profiler.profile(results)
    output_report(report.to_dict(), "thermal", json_output)


def _build_source_map(results: list[TestResult]) -> dict[str, str]:
    """Try to load source files for assertion analysis."""
    source_map = {}
    for tr in results:
        if tr.filepath and os.path.exists(tr.filepath):
            try:
                with open(tr.filepath, "r") as f:
                    source_map[tr.filepath] = f.read()
            except (OSError, UnicodeDecodeError):
                pass
    return source_map


def main(argv: Optional[list[str]] = None) -> None:
    """Main entry point for the Levain CLI."""
    parser = _create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    json_output = getattr(args, "json", False)

    commands = {
        "health": _cmd_health,
        "hooch": _cmd_hooch,
        "rise": _cmd_rise,
        "contamination": _cmd_contamination,
        "feeding": _cmd_feeding,
        "build": _cmd_build,
        "thermal": _cmd_thermal,
    }

    cmd = commands.get(args.command)
    if cmd:
        cmd(args, json_output)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
