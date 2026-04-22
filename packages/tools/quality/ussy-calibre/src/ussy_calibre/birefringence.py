"""Birefringence Scanner — Stress Visualization via Test × Environment Polariscopy."""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from ussy_calibre.models import EnvironmentCondition, StressReport, TestResult

# Stress threshold for fringe order calculation
DEFAULT_STRESS_THRESHOLD = 0.1


def compute_pass_rates(
    results: List[TestResult],
) -> Dict[str, Dict[str, float]]:
    """Compute pass rate per test per environment condition string.

    Returns: {test_name: {condition_key: pass_rate}}
    """
    data: Dict[str, Dict[str, List[bool]]] = {}
    for r in results:
        key = r.condition.to_tuple()
        cond_key = f"{key[0]}/{key[1]}/par{key[2]}/load{key[3]:.1f}"
        if r.test_name not in data:
            data[r.test_name] = {}
        if cond_key not in data[r.test_name]:
            data[r.test_name][cond_key] = []
        data[r.test_name][cond_key].append(r.passed)

    rates: Dict[str, Dict[str, float]] = {}
    for test_name, conds in data.items():
        rates[test_name] = {}
        for cond_key, outcomes in conds.items():
            rates[test_name][cond_key] = sum(outcomes) / len(outcomes) if outcomes else 0.0

    return rates


def compute_directional_stress(
    results: List[TestResult],
    dimension_values: Optional[Dict[str, List]] = None,
) -> Dict[str, Dict[str, float]]:
    """Compute stress contribution per environment dimension.

    For each dimension (os, python_version, parallelism, load_level),
    compute the variance in pass rate when that dimension varies while
    others are held constant.

    Returns: {test_name: {dimension: stress_contribution}}
    """
    if dimension_values is None:
        dimension_values = {
            "os": ["linux", "macos", "windows"],
            "python_version": ["3.9", "3.10", "3.11", "3.12"],
            "parallelism": [1, 2, 4, 8],
            "load_level": [0.0, 0.25, 0.5, 0.75, 1.0],
        }

    # Group results by test name
    by_test: Dict[str, List[TestResult]] = {}
    for r in results:
        if r.test_name not in by_test:
            by_test[r.test_name] = []
        by_test[r.test_name].append(r)

    directional: Dict[str, Dict[str, float]] = {}

    for test_name, test_results in by_test.items():
        directional[test_name] = {}

        # For each dimension, compute pass rate variance
        for dim_name in ["os", "python_version", "parallelism", "load_level"]:
            dim_key = dim_name
            # Group by this dimension's value
            by_dim: Dict[str, List[bool]] = {}
            for r in test_results:
                val = getattr(r.condition, dim_key)
                val_str = str(val)
                if val_str not in by_dim:
                    by_dim[val_str] = []
                by_dim[val_str].append(r.passed)

            if len(by_dim) < 2:
                directional[test_name][dim_name] = 0.0
                continue

            # Compute pass rates per dimension value
            dim_rates = []
            for val_str, outcomes in by_dim.items():
                rate = sum(outcomes) / len(outcomes) if outcomes else 0.0
                dim_rates.append(rate)

            # Variance across dimension values
            if dim_rates:
                mean_rate = sum(dim_rates) / len(dim_rates)
                variance = sum((r - mean_rate) ** 2 for r in dim_rates) / len(dim_rates)
                directional[test_name][dim_name] = math.sqrt(variance)
            else:
                directional[test_name][dim_name] = 0.0

    return directional


def scan_birefringence(
    results: List[TestResult],
    stress_threshold: float = DEFAULT_STRESS_THRESHOLD,
) -> Dict[str, StressReport]:
    """Run birefringence scan on test results.

    Computes per-test stress visualization showing which environmental
    dimensions cause the most variance — analogous to colored fringe
    patterns in a polariscope.
    """
    pass_rates = compute_pass_rates(results)
    directional = compute_directional_stress(results)

    reports: Dict[str, StressReport] = {}

    all_tests = set(pass_rates.keys()) | set(directional.keys())

    for test_name in all_tests:
        rates = pass_rates.get(test_name, {})
        dir_stress = directional.get(test_name, {})

        # Total stress = RMS of directional stresses
        dir_values = list(dir_stress.values())
        if dir_values:
            total_stress = math.sqrt(sum(s * s for s in dir_values) / len(dir_values))
        else:
            total_stress = 0.0

        # Also compute from pass rate variance across all conditions
        rate_values = list(rates.values())
        if len(rate_values) > 1:
            mean_rate = sum(rate_values) / len(rate_values)
            rate_stress = math.sqrt(
                sum((r - mean_rate) ** 2 for r in rate_values) / len(rate_values)
            )
            total_stress = max(total_stress, rate_stress)
        elif len(rate_values) == 1:
            total_stress = max(total_stress, 0.0)

        # Fringe order
        fringe = int(total_stress / stress_threshold) if stress_threshold > 0 else 0

        reports[test_name] = StressReport(
            test_name=test_name,
            total_stress=total_stress,
            directional_stress=dir_stress,
            fringe_order=fringe,
            pass_rates=rates,
        )

    return reports


def format_stress_map(reports: Dict[str, StressReport]) -> str:
    """Format stress reports as a readable polariscope-style map."""
    lines = []
    lines.append("=" * 60)
    lines.append("BIREFRINGENCE SCAN — Stress Visualization")
    lines.append("=" * 60)
    lines.append("")

    if not reports:
        lines.append("No test results to analyze.")
        return "\n".join(lines)

    # Sort by total stress (highest first)
    sorted_reports = sorted(
        reports.values(), key=lambda r: r.total_stress, reverse=True
    )

    for report in sorted_reports:
        status = "⚠️  STRESSED" if report.is_stressed else "✓  stable"
        lines.append(f"  {report.test_name}")
        lines.append(f"    Total Stress: {report.total_stress:.4f}  Fringe Order: {report.fringe_order}  [{status}]")

        if report.directional_stress:
            sorted_dims = sorted(
                report.directional_stress.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for dim, stress in sorted_dims:
                bar = "█" * int(stress * 50)
                lines.append(f"      {dim:20s} {stress:.4f} {bar}")

        lines.append("")

    # Summary
    stressed = sum(1 for r in reports.values() if r.is_stressed)
    total = len(reports)
    lines.append(f"Summary: {stressed}/{total} tests show detectable stress")

    return "\n".join(lines)
