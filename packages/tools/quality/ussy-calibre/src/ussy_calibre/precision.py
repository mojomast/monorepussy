"""
Marksman CLI — Archery Precision Grouping for Test Suite Quality Analysis.

Provides command-line access to all 6 instruments.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from ussy_calibre import __version__
from ussy_calibre.ballistic import analyze_bc, predict_e2e_inconsistency
from ussy_calibre.calibration import analyze_calibration
from ussy_calibre.dispersion import analyze_dispersion, is_systematic_bias
from ussy_calibre.grouping import analyze_grouping, analyze_suite, compute_suite_sigma
from ussy_calibre.models import TestExecution, TestOutcomeMarksman as TestOutcome
from ussy_calibre.storage import TestResultDB, load_fixture
from ussy_calibre.tmoa import analyze_tmoa, compare_tmoa
from ussy_calibre.weibull import analyze_maturity, maturity_trend


def parse_runs_arg(runs_str: str) -> list[TestExecution]:
    """Parse a JSON file or directory of JSON files into test executions."""
    path = Path(runs_str)
    if path.is_dir():
        executions = []
        for f in sorted(path.glob("*.json")):
            executions.extend(load_fixture(f))
        return executions
    elif path.is_file():
        return load_fixture(path)
    else:
        print(f"Error: path not found: {runs_str}", file=sys.stderr)
        return []


def cmd_group(args: argparse.Namespace) -> None:
    """Analyze test precision grouping."""
    db = _get_db(args)
    suite = args.suite

    if suite:
        executions = db.get_by_suite(suite)
    else:
        executions = db.get_all()

    if not executions:
        print("No test executions found.")
        return

    if args.test:
        executions = [e for e in executions if e.test_name == args.test]

    if args.test:
        result = analyze_grouping(executions, test_name=args.test)
        _print_grouping(result)
    else:
        results = analyze_suite(executions, suite=suite)
        for r in results:
            _print_grouping(r)
            print("")
        suite_sigma = compute_suite_sigma(results)
        print(f"Suite σ_T (RMS): {suite_sigma:.6f}")
        print(f"Suite CEP_T:     {1.1774 * suite_sigma:.6f}")


def cmd_ellipse(args: argparse.Namespace) -> None:
    """Show dispersion ellipse for a test class."""
    db = _get_db(args)
    test_class = args.test_class

    executions = db.get_by_test(test_class)
    if not executions:
        print(f"No executions found for test: {test_class}")
        return

    result = analyze_dispersion(executions, test_name=test_class)

    print(f"Dispersion Ellipse: {test_class}")
    print(f"  σ_FP:           {result.sigma_fp:.6f}")
    print(f"  σ_FN:           {result.sigma_fn:.6f}")
    print(f"  Covariance:     {result.covariance:.6f}")
    print(f"  Eigenvalue 1:   {result.eigenvalue_1:.6f}")
    print(f"  Eigenvalue 2:   {result.eigenvalue_2:.6f}")
    print(f"  Tilt angle:     {result.tilt_angle_deg:.2f}°")
    print(f"  Shape:          {result.shape.value}")
    print(f"  Aspect ratio:   {result.aspect_ratio:.2f}")
    print(f"  Systematic:     {is_systematic_bias(result)}")


def cmd_tmoa(args: argparse.Namespace) -> None:
    """Compute TMOA for cross-project comparison."""
    db = _get_db(args)
    project = args.project

    executions = db.get_all()
    if not executions:
        print("No test executions found.")
        return

    suites = db.get_suites()
    results = []
    for s in suites:
        suite_execs = db.get_by_suite(s)
        suite_results = analyze_suite(suite_execs, suite=s)
        sigma_t = compute_suite_sigma(suite_results)
        # Count dependencies (unique test names as proxy)
        n_deps = len(set(e.test_name for e in suite_execs))
        r = analyze_tmoa(sigma_t, n_deps, project=s)
        results.append(r)

    if args.compare:
        # Show comparison
        comparisons = compare_tmoa(results)
        print(f"TMOA Comparison (baseline: {args.compare}):")
        print("")
        for c in comparisons:
            marker = " ◄" if c["project"] == args.compare else ""
            print(
                f"  {c['project']:30s}  TMOA: {c['tmoa_deg']:6.3f}°  "
                f"({c['classification']}){marker}"
            )
    else:
        # Show single project
        for r in results:
            if project and r.project != project:
                continue
            print(f"TMOA Analysis: {r.project}")
            print(f"  σ_T:            {r.sigma_t:.6f}")
            print(f"  Dependencies:   {r.n_dependencies}")
            print(f"  TMOA:           {r.tmoa_deg:.4f}°")
            print(f"  Classification: {r.classification.value}")


def cmd_predict_bc(args: argparse.Namespace) -> None:
    """Predict E2E inconsistency from unit test BC."""
    unit_precision = args.unit_precision
    scale = args.scale
    k = args.bc if args.bc else 0.5

    result = analyze_bc(sigma_consistency=unit_precision, k=k)

    print(f"BC Error Propagation Analysis")
    print(f"  Ballistic coefficient (k):  {result.k:.4f}")
    print(f"  Classification:             {result.bc_classification}")
    print(f"  σ_consistency:              {result.sigma_consistency:.6f}")
    print("")
    print(f"  Predicted inconsistency at scale {scale}:")
    prediction = predict_e2e_inconsistency(unit_precision, k, scale, acceptable_cep=0.1)
    print(f"    σ_test:       {prediction['predicted_sigma']:.6f}")
    print(f"    CEP_T:        {prediction['predicted_cep']:.6f}")
    print(f"    Exceeds 0.1:  {prediction['exceeds_threshold']}")

    if args.show_all_scales:
        print("")
        print("  All scales:")
        for s, sig in zip(result.scales, result.predicted_sigmas):
            print(f"    Scale {s:3d}: σ = {sig:.6f}, CEP = {1.1774 * sig:.6f}")


def cmd_maturity(args: argparse.Namespace) -> None:
    """Classify test suite maturity."""
    db = _get_db(args)
    suite = args.suite

    if not suite:
        suites = db.get_suites()
    else:
        suites = [suite]

    for s in suites:
        failure_times = db.get_failure_times(s)
        result = analyze_maturity(failure_times, suite=s)

        print(f"Maturity Analysis: {s}")
        print(f"  Failures:       {result.n_failures}")
        print(f"  β (shape):      {result.beta:.4f}")
        print(f"  η (scale):      {result.eta:.4f}")
        print(f"  Maturity:       {result.maturity.value}")
        print("")


def cmd_calibrate(args: argparse.Namespace) -> None:
    """Calibrate windage/elevation bias."""
    db = _get_db(args)
    suite = args.suite

    executions = db.get_by_suite(suite)
    if not executions:
        print(f"No executions found for suite: {suite}")
        return

    results = analyze_suite(executions, suite=suite)
    suite_sigma = compute_suite_sigma(results)

    # Use the first test's grouping as representative, or compute aggregate
    fp_rate = sum(r.sigma_fp for r in results) / len(results) if results else 0
    fn_rate = sum(r.sigma_fn for r in results) / len(results) if results else 0

    from ussy_calibre.models import GroupingResult

    aggregate = GroupingResult(
        test_name=f"{suite} (aggregate)",
        sigma_fp=fp_rate,
        sigma_fn=fn_rate,
    )

    result = analyze_calibration(aggregate, suite=suite, target_cep=args.target_cep)

    print(f"Calibration Analysis: {suite}")
    print(f"  Current FP rate:  {result.current_fp_rate:.6f}")
    print(f"  Current FN rate:  {result.current_fn_rate:.6f}")
    print(f"  Bias direction:   {result.bias_direction.value}")
    print(f"  Target CEP_T:     {result.target_cep:.4f}")
    print(f"  FP correction:    {result.required_fp_correction:.6f}")
    print(f"  FN correction:    {result.required_fn_correction:.6f}")
    print(f"  Calibration clicks: {len(result.clicks)}")
    for click in result.clicks:
        print(f"    [{click.direction.value}] {click.clicks} clicks: {click.description}")
        print(f"      Expected FP change: {click.expected_fp_change:.6f}")
        print(f"      Expected FN change: {click.expected_fn_change:.6f}")


def _get_db(args: argparse.Namespace) -> TestResultDB:
    """Get database from args, loading data if a path is provided."""
    db_path = getattr(args, "db", ":memory:")
    db = TestResultDB(db_path)

    data_path = getattr(args, "data", None)
    if data_path:
        path = Path(data_path)
        if path.is_dir():
            for f in sorted(path.glob("*.json")):
                executions = load_fixture(f)
                db.insert_many(executions)
        elif path.is_file():
            executions = load_fixture(path)
            db.insert_many(executions)

    return db


def _print_grouping(result: Any) -> None:
    """Print a grouping result."""
    print(f"Test: {result.test_name}")
    print(f"  σ_FP:   {result.sigma_fp:.6f}")
    print(f"  σ_FN:   {result.sigma_fn:.6f}")
    print(f"  σ_T:    {result.sigma_t:.6f}")
    print(f"  CEP_T:  {result.cep_t:.6f}")
    print(f"  Runs:   {result.n_runs}")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="marksman",
        description="Archery Precision Grouping for Test Suite Quality Analysis",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--db", default=":memory:", help="Path to SQLite database")
    parser.add_argument("--data", help="Path to JSON data file or directory")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # group command
    group_parser = subparsers.add_parser("group", help="Analyze test precision grouping")
    group_parser.add_argument("--suite", "-s", help="Test suite name")
    group_parser.add_argument("--test", "-t", help="Specific test name")
    group_parser.add_argument("--runs", "-r", help="Path to runs data (JSON)")
    group_parser.set_defaults(func=cmd_group)

    # ellipse command
    ellipse_parser = subparsers.add_parser("ellipse", help="Show dispersion ellipse")
    ellipse_parser.add_argument("test_class", help="Test class name")
    ellipse_parser.set_defaults(func=cmd_ellipse)

    # tmoa command
    tmoa_parser = subparsers.add_parser("tmoa", help="Compute TMOA")
    tmoa_parser.add_argument("--project", "-p", help="Project name")
    tmoa_parser.add_argument("--compare", "-c", help="Baseline project for comparison")
    tmoa_parser.set_defaults(func=cmd_tmoa)

    # predict-bc command
    bc_parser = subparsers.add_parser("predict-bc", help="Predict E2E inconsistency")
    bc_parser.add_argument(
        "--unit-precision", type=float, required=True, help="Unit test σ_consistency"
    )
    bc_parser.add_argument("--scale", type=float, default=10, help="Target integration scale")
    bc_parser.add_argument("--bc", type=float, help="Ballistic coefficient k")
    bc_parser.add_argument(
        "--show-all-scales", action="store_true", help="Show predictions at all scales"
    )
    bc_parser.set_defaults(func=cmd_predict_bc)

    # maturity command
    maturity_parser = subparsers.add_parser("maturity", help="Classify suite maturity")
    maturity_parser.add_argument("--suite", "-s", help="Test suite name")
    maturity_parser.add_argument("--window", help="Time window (e.g., 90d)")
    maturity_parser.set_defaults(func=cmd_maturity)

    # calibrate command
    cal_parser = subparsers.add_parser("calibrate", help="Calibrate bias")
    cal_parser.add_argument("--suite", "-s", required=True, help="Test suite name")
    cal_parser.add_argument("--target-cep", type=float, default=0.05, help="Target CEP_T")
    cal_parser.set_defaults(func=cmd_calibrate)

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
