"""Lehr CLI — Glass Annealing Science for Test Suite Stabilization."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from ussy_calibre.engine import analyze, format_report
from ussy_calibre.models import (
    EnvironmentCondition,
    TestResult,
    SuiteReport,
)


def parse_results_file(path: str) -> List[TestResult]:
    """Parse a JSON results file into TestResult objects.

    Expected format:
    [
      {
        "test_name": "test_foo",
        "passed": true,
        "os": "linux",
        "python_version": "3.11",
        "parallelism": 1,
        "load_level": 0.0,
        "duration_ms": 120.5,
        "retries_used": 0,
        "timeout_used": false
      },
      ...
    ]
    """
    with open(path, "r") as f:
        data = json.load(f)

    results = []
    for entry in data:
        condition = EnvironmentCondition(
            os=entry.get("os", "linux"),
            python_version=entry.get("python_version", "3.11"),
            parallelism=entry.get("parallelism", 1),
            load_level=entry.get("load_level", 0.0),
        )
        results.append(TestResult(
            test_name=entry.get("test_name", "unknown"),
            condition=condition,
            passed=entry.get("passed", True),
            duration_ms=entry.get("duration_ms", 0.0),
            retries_used=entry.get("retries_used", 0),
            timeout_used=entry.get("timeout_used", False),
        ))

    return results


def generate_sample_results() -> List[TestResult]:
    """Generate sample test results for demo purposes."""
    results = []
    test_configs = [
        ("test_pure_unit", 0.99, 0.0, 0.01),      # Fused Silica
        ("test_with_mocks", 0.95, 0.02, 0.05),     # Borosilicate
        ("test_integration", 0.85, 0.1, 0.15),     # Soda-Lime
        ("test_external_api", 0.7, 0.3, 0.4),      # Lead Crystal
        ("test_flaky_with_retries", 0.98, 0.05, 0.7),  # Tempered
        ("test_deterministic", 1.0, 0.0, 0.0),     # Fused Silica
    ]

    envs = [
        EnvironmentCondition("linux", "3.11", 1, 0.0),
        EnvironmentCondition("linux", "3.11", 4, 0.5),
        EnvironmentCondition("linux", "3.10", 1, 0.0),
        EnvironmentCondition("macos", "3.11", 1, 0.0),
        EnvironmentCondition("macos", "3.12", 2, 0.25),
        EnvironmentCondition("windows", "3.11", 1, 0.0),
        EnvironmentCondition("linux", "3.12", 8, 0.75),
    ]

    import random
    rng = random.Random(42)

    for test_name, base_pass_rate, cte_sensitivity, brittleness in test_configs:
        for env in envs:
            # Adjust pass rate based on environment distance from baseline
            env_factor = 0.0
            if env.os != "linux":
                env_factor += cte_sensitivity
            if env.python_version != "3.11":
                env_factor += cte_sensitivity * 0.5
            if env.parallelism > 1:
                env_factor += cte_sensitivity * 0.3
            if env.load_level > 0.1:
                env_factor += cte_sensitivity * 0.2

            adjusted_rate = max(0.0, base_pass_rate - env_factor)

            # With hardening (retries) - improves pass rate for brittle tests
            passes_with_hardening = rng.random() < min(adjusted_rate + brittleness * 0.3, 1.0)
            # Without hardening
            passes_raw = rng.random() < adjusted_rate

            # Record both: first without hardening, then with
            results.append(TestResult(
                test_name=test_name,
                condition=env,
                passed=passes_raw,
                duration_ms=rng.uniform(10, 500),
                retries_used=0,
                timeout_used=False,
            ))

            if brittleness > 0.1:
                results.append(TestResult(
                    test_name=test_name,
                    condition=env,
                    passed=passes_with_hardening,
                    duration_ms=rng.uniform(50, 2000),
                    retries_used=rng.randint(1, 3) if not passes_raw else 0,
                    timeout_used=brittleness > 0.5 and rng.random() < 0.3,
                ))

    return results


def cmd_scan(args: argparse.Namespace) -> None:
    """Run birefringence scan on test results."""
    results = _load_results(args)
    if not results:
        print("No test results found.")
        return

    report = analyze(results)

    from ussy_calibre.birefringence import format_stress_map
    output = format_stress_map(report.stress_reports)

    if getattr(args, "json", False):
        data = {
            name: {
                "total_stress": r.total_stress,
                "fringe_order": r.fringe_order,
                "directional_stress": r.directional_stress,
                "is_stressed": r.is_stressed,
            }
            for name, r in report.stress_reports.items()
        }
        print(json.dumps(data, indent=2))
    else:
        print(output)


def cmd_cte(args: argparse.Namespace) -> None:
    """Profile CTE (environment sensitivity) for tests."""
    results = _load_results(args)
    if not results:
        print("No test results found.")
        return

    report = analyze(results)

    from ussy_calibre.cte import format_cte_profiles
    output = format_cte_profiles(report.cte_profiles)

    if getattr(args, "json", False):
        data = {
            name: {
                "composite_cte": p.composite_cte,
                "cte_by_dimension": p.cte_by_dimension,
                "glass_analogy": p.glass_analogy,
            }
            for name, p in report.cte_profiles.items()
        }
        print(json.dumps(data, indent=2))
    else:
        print(output)


def cmd_shock(args: argparse.Namespace) -> None:
    """Test thermal shock resistance."""
    results = _load_results(args)
    if not results:
        print("No test results found.")
        return

    report = analyze(results)

    from ussy_calibre.thermal_shock import format_shock_report
    output = format_shock_report(report.shock_resistances)

    if getattr(args, "json", False):
        data = {
            name: {
                "resistance_score": r.resistance_score,
                "max_environment_change": r.max_environment_change,
                "shock_pass_rate": r.shock_pass_rate,
                "is_shock_resistant": r.is_shock_resistant,
            }
            for name, r in report.shock_resistances.items()
        }
        print(json.dumps(data, indent=2))
    else:
        print(output)


def cmd_anneal(args: argparse.Namespace) -> None:
    """Generate annealing schedules for unstable tests."""
    results = _load_results(args)
    if not results:
        print("No test results found.")
        return

    report = analyze(results)

    from ussy_calibre.annealing import format_schedules
    output = format_schedules(report.annealing_schedules)

    if getattr(args, "json", False):
        data = {}
        for name, schedule in report.annealing_schedules.items():
            data[name] = {
                "estimated_total_steps": schedule.estimated_total_steps,
                "complexity_factor": schedule.complexity_factor,
                "phases": [
                    {
                        "phase_name": p.phase_name,
                        "duration_steps": p.duration_steps,
                        "target_pass_rate": p.target_pass_rate,
                        "environment_changes": p.environment_changes,
                    }
                    for p in schedule.phases
                ],
            }
        print(json.dumps(data, indent=2))
    else:
        print(output)


def cmd_temper(args: argparse.Namespace) -> None:
    """Detect tempered (brittle-stable) tests."""
    results = _load_results(args)
    if not results:
        print("No test results found.")
        return

    report = analyze(results)

    from ussy_calibre.tempering import format_temper_report
    output = format_temper_report(report.temper_results)

    if getattr(args, "json", False):
        data = {
            name: {
                "pass_rate_with_hardening": r.pass_rate_with_hardening,
                "pass_rate_without_hardening": r.pass_rate_without_hardening,
                "brittleness_index": r.brittleness_index,
                "brittleness_class": r.brittleness_class.value,
                "is_tempered": r.is_tempered,
            }
            for name, r in report.temper_results.items()
        }
        print(json.dumps(data, indent=2))
    else:
        print(output)


def cmd_classify(args: argparse.Namespace) -> None:
    """Classify tests into glass types."""
    results = _load_results(args)
    if not results:
        print("No test results found.")
        return

    report = analyze(results)

    from ussy_calibre.classifier import format_classifications
    output = format_classifications(report.glass_classifications)

    if getattr(args, "json", False):
        data = {
            name: {
                "glass_type": c.glass_type.value,
                "glass_label": c.glass_type.label,
                "cte": c.cte,
                "shock_resistance": c.shock_resistance,
                "brittleness": c.brittleness,
                "confidence": c.confidence,
                "recommendation": c.recommendation,
            }
            for name, c in report.glass_classifications.items()
        }
        print(json.dumps(data, indent=2))
    else:
        print(output)


def cmd_analyze(args: argparse.Namespace) -> None:
    """Run full Lehr analysis (all instruments)."""
    results = _load_results(args)
    if not results:
        print("No test results found.")
        return

    report = analyze(results)

    if getattr(args, "json", False):
        data = {
            "tests": report.tests,
            "suite_health": report.suite_health,
            "tempered_count": report.tempered_count,
            "glass_distribution": report.glass_distribution,
            "stress_reports": {
                name: {
                    "total_stress": r.total_stress,
                    "fringe_order": r.fringe_order,
                    "is_stressed": r.is_stressed,
                }
                for name, r in report.stress_reports.items()
            },
            "glass_classifications": {
                name: {
                    "glass_type": c.glass_type.value,
                    "glass_label": c.glass_type.label,
                    "cte": c.cte,
                    "shock_resistance": c.shock_resistance,
                    "brittleness": c.brittleness,
                    "confidence": c.confidence,
                    "recommendation": c.recommendation,
                }
                for name, c in report.glass_classifications.items()
            },
        }
        print(json.dumps(data, indent=2))
    else:
        print(format_report(report))


def _load_results(args: argparse.Namespace) -> List[TestResult]:
    """Load test results from file or generate sample data."""
    path = getattr(args, "path", None)
    if path:
        try:
            return parse_results_file(path)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading results: {e}", file=sys.stderr)
            return []
    else:
        return generate_sample_results()


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="lehr",
        description="Lehr — Glass Annealing Science for Test Suite Stabilization",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available instruments")

    # scan
    scan_parser = subparsers.add_parser(
        "scan", help="Birefringence scan — stress visualization"
    )
    scan_parser.add_argument("path", nargs="?", help="Path to test results JSON file")

    # cte
    cte_parser = subparsers.add_parser(
        "cte", help="CTE profiler — environment sensitivity"
    )
    cte_parser.add_argument("path", nargs="?", help="Path to test results JSON file")

    # shock
    shock_parser = subparsers.add_parser(
        "shock", help="Thermal shock tester — rapid change resilience"
    )
    shock_parser.add_argument("path", nargs="?", help="Path to test results JSON file")

    # anneal
    anneal_parser = subparsers.add_parser(
        "anneal", help="Annealing scheduler — stabilization protocols"
    )
    anneal_parser.add_argument("path", nargs="?", help="Path to test results JSON file")

    # temper
    temper_parser = subparsers.add_parser(
        "temper", help="Tempering detector — brittleness discrimination"
    )
    temper_parser.add_argument("path", nargs="?", help="Path to test results JSON file")

    # classify
    classify_parser = subparsers.add_parser(
        "classify", help="Glass type classifier — fragility taxonomy"
    )
    classify_parser.add_argument("path", nargs="?", help="Path to test results JSON file")

    # analyze (full)
    analyze_parser = subparsers.add_parser(
        "analyze", help="Full analysis (all instruments)"
    )
    analyze_parser.add_argument("path", nargs="?", help="Path to test results JSON file")

    return parser


def main() -> None:
    """Entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        # Default to full analysis with sample data
        args.command = "analyze"

    commands = {
        "scan": cmd_scan,
        "cte": cmd_cte,
        "shock": cmd_shock,
        "anneal": cmd_anneal,
        "temper": cmd_temper,
        "classify": cmd_classify,
        "analyze": cmd_analyze,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
