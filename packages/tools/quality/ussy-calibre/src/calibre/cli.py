"""Calibre CLI — Metrological Measurement Science for Test Suite Quality."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

from calibre import __version__
from calibre.db import CalibreDB
from calibre.models import (
    CapabilitySpec,
    DriftObservation,
    TestResult,
    TestRun,
    TraceabilityLink,
)
from calibre.budget import budget_from_test_runs, format_budget
from calibre.capability import capability_analysis, format_capability
from calibre.classifier import classify_test, format_classification
from calibre.drift import analyze_drift, format_drift_result
from calibre.rr import compute_rr_summary, format_rr_summary, runs_to_rr_observations
from calibre.traceability import audit_traceability, format_traceability
from calibre.report import generate_full_report


def _parse_usl(usl_str: str) -> float:
    """Parse a USL value like '5%' or '0.05'."""
    if usl_str.endswith("%"):
        return float(usl_str[:-1]) / 100.0
    return float(usl_str)


def cmd_budget(args: argparse.Namespace) -> None:
    """Compute uncertainty budget for a module."""
    db = CalibreDB(args.db)
    runs = db.get_test_runs(module=args.module)
    if not runs:
        print(f"No test runs found for module: {args.module}")
        return

    budget = budget_from_test_runs(args.module, runs)
    print(format_budget(budget))
    db.close()


def cmd_rr(args: argparse.Namespace) -> None:
    """Perform Gauge R&R study."""
    db = CalibreDB(args.db)
    runs = db.get_test_runs(suite=args.suite)
    if not runs:
        print(f"No test runs found for suite: {args.suite}")
        return

    observations = runs_to_rr_observations(runs)
    summary = compute_rr_summary(args.suite, observations)
    print(format_rr_summary(summary))
    db.close()


def cmd_capability(args: argparse.Namespace) -> None:
    """Compute process capability indices."""
    db = CalibreDB(args.db)
    runs = db.get_test_runs(suite=args.suite)
    if not runs:
        print(f"No test runs found for suite: {args.suite}")
        return

    usl = _parse_usl(args.usl)
    lsl = _parse_usl(args.lsl) if args.lsl else 0.0

    spec = CapabilitySpec(test_name=args.suite, usl=usl, lsl=lsl)
    result = capability_analysis(runs, spec)
    print(format_capability(result))
    db.close()


def cmd_classify(args: argparse.Namespace) -> None:
    """Classify test flakiness as Type A or Type B."""
    db = CalibreDB(args.db)
    runs = db.get_test_runs(test_name=args.test)
    if not runs:
        print(f"No test runs found for test: {args.test}")
        return

    classification = classify_test(runs, args.test)
    print(format_classification(classification))
    db.close()


def cmd_drift(args: argparse.Namespace) -> None:
    """Detect test expectation drift."""
    db = CalibreDB(args.db)
    obs_list = db.get_drift_observations(test_name=args.suite)
    if not obs_list:
        # Try using test runs as drift observations
        runs = db.get_test_runs(suite=args.suite)
        if not runs:
            print(f"No drift data found for: {args.suite}")
            return

        # Convert test runs to drift observations using pass rate over time
        by_date: dict = {}
        for r in runs:
            date_key = r.timestamp.date()
            by_date.setdefault(date_key, []).append(r)

        obs_list = []
        for date, day_runs in sorted(by_date.items()):
            pass_rate = sum(1 for r in day_runs if r.passed) / len(day_runs)
            obs_list.append(
                DriftObservation(
                    test_name=args.suite,
                    timestamp=datetime.combine(date, datetime.min.time(), tzinfo=timezone.utc),
                    observed_value=pass_rate,
                )
            )

    mpe = _parse_usl(args.mpe) if args.mpe else 0.1
    result = analyze_drift(obs_list, mpe=mpe)
    print(format_drift_result(result))
    db.close()


def cmd_trace(args: argparse.Namespace) -> None:
    """Audit traceability chain for a test."""
    db = CalibreDB(args.db)
    links = db.get_traceability_links(test_name=args.test)
    result = audit_traceability(args.test, links)
    print(format_traceability(result))
    db.close()


def cmd_report(args: argparse.Namespace) -> None:
    """Generate full Metrological Characterization Report."""
    db = CalibreDB(args.db)
    runs = db.get_test_runs(suite=args.suite)
    drift_obs = db.get_drift_observations()
    trace_links = db.get_traceability_links()

    mpe = _parse_usl(args.mpe) if args.mpe else 0.1

    report = generate_full_report(
        suite=args.suite,
        runs=runs,
        drift_observations=drift_obs if drift_obs else None,
        traceability_links=trace_links if trace_links else None,
        mpe=mpe,
    )
    print(report)
    db.close()


def cmd_import(args: argparse.Namespace) -> None:
    """Import test results from a JSON file."""
    db = CalibreDB(args.db)
    count = db.import_json_results(args.file)
    print(f"Imported {count} test results from {args.file}")
    db.close()


def cmd_seed(args: argparse.Namespace) -> None:
    """Seed the database with demo data for testing."""
    import random

    random.seed(42)
    db = CalibreDB(args.db)

    # Create demo test runs
    suites = ["auth", "api", "ui"]
    builds = [f"build-{i}" for i in range(1, 11)]
    envs = ["ci-linux", "ci-macos", "staging"]
    tests = [
        ("test_login", "auth"),
        ("test_logout", "auth"),
        ("test_token_refresh", "auth"),
        ("test_get_users", "api"),
        ("test_create_user", "api"),
        ("test_delete_user", "api"),
        ("test_dashboard_loads", "ui"),
        ("test_form_submission", "ui"),
    ]

    runs: List[TestRun] = []
    base_time = datetime.now(timezone.utc) - timedelta(days=30)

    for test_name, suite in tests:
        for build in builds:
            for env in envs:
                # Vary pass rates to create interesting patterns
                base_rate = 0.9
                if test_name == "test_token_refresh":
                    base_rate = 0.7  # flakier
                if env == "staging" and suite == "api":
                    base_rate -= 0.15  # env-dependent

                if random.random() < base_rate:
                    result = TestResult.PASS
                else:
                    result = TestResult.FAIL

                ts = base_time + timedelta(
                    days=random.randint(0, 29),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                )
                duration = random.uniform(0.1, 5.0)

                runs.append(
                    TestRun(
                        test_name=test_name,
                        module=f"tests/{suite}",
                        suite=suite,
                        build_id=build,
                        environment=env,
                        result=result,
                        timestamp=ts,
                        duration=duration,
                    )
                )

    db.insert_test_runs(runs)

    # Create demo drift observations
    drift_obs: List[DriftObservation] = []
    for day in range(30):
        ts = base_time + timedelta(days=day)
        # Simulate drift: pass rate slowly decreases
        value = 0.95 - 0.002 * day + random.uniform(-0.02, 0.02)
        drift_obs.append(
            DriftObservation(
                test_name="test_token_refresh",
                timestamp=ts,
                observed_value=value,
            )
        )
    db.insert_drift_observations(drift_obs)

    # Create demo traceability links
    trace_links: List[TraceabilityLink] = [
        TraceabilityLink(
            test_name="test_login",
            level="stakeholder_need",
            reference="REQ-001: User authentication",
            uncertainty=0.05,
            last_verified=datetime.now(timezone.utc) - timedelta(days=10),
            review_interval_days=90,
        ),
        TraceabilityLink(
            test_name="test_login",
            level="specification",
            reference="SPEC-AUTH-01: Login flow",
            uncertainty=0.03,
            last_verified=datetime.now(timezone.utc) - timedelta(days=10),
            review_interval_days=90,
        ),
        TraceabilityLink(
            test_name="test_login",
            level="acceptance_criteria",
            reference="AC-01: Valid credentials grant access",
            uncertainty=0.02,
            last_verified=datetime.now(timezone.utc) - timedelta(days=200),
            review_interval_days=180,
        ),
        TraceabilityLink(
            test_name="test_login",
            level="test_plan",
            reference="TP-01: Authentication test plan",
            uncertainty=0.01,
            last_verified=datetime.now(timezone.utc) - timedelta(days=10),
            review_interval_days=90,
        ),
        TraceabilityLink(
            test_name="test_login",
            level="assertion",
            reference="assert response.status_code == 200",
            uncertainty=0.01,
            last_verified=datetime.now(timezone.utc) - timedelta(days=10),
            review_interval_days=90,
        ),
        # Orphan test: test_dashboard_loads has no links
    ]
    db.insert_traceability_links(trace_links)

    print(f"Seeded database with {len(runs)} test runs, {len(drift_obs)} drift observations, {len(trace_links)} traceability links")
    db.close()


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="calibre",
        description="Calibre — Metrological Measurement Science for Test Suite Quality Analysis",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--db", default="calibre.db", help="SQLite database path")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # budget
    p_budget = subparsers.add_parser("budget", help="Compute uncertainty budget for a module")
    p_budget.add_argument("module", help="Module name to analyze")
    p_budget.set_defaults(func=cmd_budget)

    # rr
    p_rr = subparsers.add_parser("rr", help="Perform Gauge R&R study")
    p_rr.add_argument("suite", help="Test suite name")
    p_rr.add_argument("--builds", type=int, default=5, help="Minimum number of builds")
    p_rr.add_argument("--envs", type=int, default=3, help="Minimum number of environments")
    p_rr.set_defaults(func=cmd_rr)

    # capability
    p_cap = subparsers.add_parser("capability", help="Compute process capability indices")
    p_cap.add_argument("suite", help="Test suite name")
    p_cap.add_argument("--usl", default="1.0", help="Upper specification limit (e.g., '5%%' or '0.05')")
    p_cap.add_argument("--lsl", default="0.8", help="Lower specification limit")
    p_cap.set_defaults(func=cmd_capability)

    # classify
    p_classify = subparsers.add_parser("classify", help="Classify test flakiness as Type A or Type B")
    p_classify.add_argument("test", help="Test name to classify")
    p_classify.set_defaults(func=cmd_classify)

    # drift
    p_drift = subparsers.add_parser("drift", help="Detect test expectation drift")
    p_drift.add_argument("suite", help="Test suite or test name")
    p_drift.add_argument("--mpe", default="0.1", help="Maximum permissible error (e.g., '10%%' or '0.1')")
    p_drift.set_defaults(func=cmd_drift)

    # trace
    p_trace = subparsers.add_parser("trace", help="Audit traceability chain for a test")
    p_trace.add_argument("test", help="Test name to audit")
    p_trace.set_defaults(func=cmd_trace)

    # report
    p_report = subparsers.add_parser("report", help="Generate full Metrological Characterization Report")
    p_report.add_argument("suite", help="Test suite name")
    p_report.add_argument("--full", action="store_true", help="Include all details")
    p_report.add_argument("--mpe", default="0.1", help="Maximum permissible error")
    p_report.set_defaults(func=cmd_report)

    # import
    p_import = subparsers.add_parser("import", help="Import test results from JSON")
    p_import.add_argument("file", help="Path to JSON results file")
    p_import.set_defaults(func=cmd_import)

    # seed
    p_seed = subparsers.add_parser("seed", help="Seed database with demo data")
    p_seed.set_defaults(func=cmd_seed)

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return

    args.func(args)
