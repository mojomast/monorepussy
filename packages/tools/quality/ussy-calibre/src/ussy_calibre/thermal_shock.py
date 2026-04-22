"""Thermal Shock Tester — Rapid Environment Change Resilience."""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from ussy_calibre.models import EnvironmentCondition, ShockResistance, TestResult


def compute_shock_pass_rate(
    results: List[TestResult],
    baseline_condition: Optional[EnvironmentCondition] = None,
) -> Dict[str, float]:
    """Compute pass rate under shock (sudden environment change) conditions.

    Shock = test run immediately after environment change without cleanup.
    """
    if baseline_condition is None:
        baseline_condition = EnvironmentCondition()

    # Group by test
    by_test: Dict[str, List[TestResult]] = {}
    for r in results:
        if r.test_name not in by_test:
            by_test[r.test_name] = []
        by_test[r.test_name].append(r)

    shock_rates: Dict[str, float] = {}

    for test_name, test_results in by_test.items():
        # Find results where condition differs significantly from baseline
        shock_outcomes = []
        for r in test_results:
            cond = r.condition
            # Consider it a shock if any dimension differs from baseline
            is_shock = (
                cond.os != baseline_condition.os
                or cond.python_version != baseline_condition.python_version
                or cond.parallelism != baseline_condition.parallelism
                or abs(cond.load_level - baseline_condition.load_level) > 0.1
            )
            if is_shock:
                shock_outcomes.append(r.passed)

        if shock_outcomes:
            shock_rates[test_name] = sum(shock_outcomes) / len(shock_outcomes)
        else:
            # No shock conditions found, use overall pass rate
            if test_results:
                all_pass = sum(1 for r in test_results if r.passed)
                shock_rates[test_name] = all_pass / len(test_results)
            else:
                shock_rates[test_name] = 0.0

    return shock_rates


def compute_stable_pass_rate(
    results: List[TestResult],
    baseline_condition: Optional[EnvironmentCondition] = None,
) -> Dict[str, float]:
    """Compute pass rate under stable (baseline) conditions."""
    if baseline_condition is None:
        baseline_condition = EnvironmentCondition()

    by_test: Dict[str, List[TestResult]] = {}
    for r in results:
        if r.test_name not in by_test:
            by_test[r.test_name] = []
        by_test[r.test_name].append(r)

    stable_rates: Dict[str, float] = {}

    for test_name, test_results in by_test.items():
        baseline_outcomes = []
        for r in test_results:
            cond = r.condition
            is_baseline = (
                cond.os == baseline_condition.os
                and cond.python_version == baseline_condition.python_version
                and cond.parallelism == baseline_condition.parallelism
                and abs(cond.load_level - baseline_condition.load_level) < 0.01
            )
            if is_baseline:
                baseline_outcomes.append(r.passed)

        if baseline_outcomes:
            stable_rates[test_name] = sum(baseline_outcomes) / len(baseline_outcomes)
        else:
            # Use first condition as baseline if exact match not found
            if test_results:
                all_pass = sum(1 for r in test_results if r.passed)
                stable_rates[test_name] = all_pass / len(test_results)
            else:
                stable_rates[test_name] = 0.0

    return stable_rates


def compute_max_environment_change(
    results: List[TestResult],
) -> Dict[str, float]:
    """Compute the largest environment change a test can survive.

    Returns the normalized distance of the most different environment
    where the test still passes.
    """
    by_test: Dict[str, List[TestResult]] = {}
    for r in results:
        if r.test_name not in by_test:
            by_test[r.test_name] = []
        by_test[r.test_name].append(r)

    max_changes: Dict[str, float] = {}

    for test_name, test_results in by_test.items():
        if not test_results:
            max_changes[test_name] = 0.0
            continue

        # Compute distance from first condition
        ref = test_results[0].condition
        max_survived = 0.0

        for r in test_results:
            if r.passed:
                # Compute normalized distance
                dist = 0.0
                if r.condition.os != ref.os:
                    dist += 1.0
                try:
                    pv_diff = abs(float(r.condition.python_version) - float(ref.python_version))
                    dist += pv_diff
                except (ValueError, TypeError):
                    if r.condition.python_version != ref.python_version:
                        dist += 0.1
                dist += abs(r.condition.parallelism - ref.parallelism) * 0.25
                dist += abs(r.condition.load_level - ref.load_level)
                max_survived = max(max_survived, dist)

        max_changes[test_name] = max_survived

    return max_changes


def test_thermal_shock(
    results: List[TestResult],
    cte_by_test: Optional[Dict[str, float]] = None,
    baseline_condition: Optional[EnvironmentCondition] = None,
) -> Dict[str, ShockResistance]:
    """Run thermal shock test on test results.

    Shock resistance R(t) = p_stable(t) / (CTE(t) × ΔT_max(t))
    High R = test survives shock; Low R = test cracks under sudden change.
    """
    stable_rates = compute_stable_pass_rate(results, baseline_condition)
    shock_rates = compute_shock_pass_rate(results, baseline_condition)
    max_changes = compute_max_environment_change(results)

    resistances: Dict[str, ShockResistance] = {}

    for test_name in stable_rates:
        p_stable = stable_rates.get(test_name, 0.0)
        cte = cte_by_test.get(test_name, 0.1) if cte_by_test else 0.1
        delta_t = max_changes.get(test_name, 1.0)

        # R = p_stable / (CTE × ΔT)
        denominator = cte * delta_t
        if denominator > 0:
            resistance = p_stable / denominator
        else:
            resistance = p_stable if p_stable > 0 else 1.0

        shock_rate = shock_rates.get(test_name, 0.0)

        resistances[test_name] = ShockResistance(
            test_name=test_name,
            resistance_score=resistance,
            max_environment_change=delta_t,
            shock_pass_rate=shock_rate,
        )

    return resistances


def format_shock_report(resistances: Dict[str, ShockResistance]) -> str:
    """Format thermal shock test results."""
    lines = []
    lines.append("=" * 60)
    lines.append("THERMAL SHOCK TEST — Rapid Environment Change Resilience")
    lines.append("=" * 60)
    lines.append("")

    if not resistances:
        lines.append("No test results to analyze.")
        return "\n".join(lines)

    sorted_res = sorted(
        resistances.values(), key=lambda r: r.resistance_score, reverse=True
    )

    for res in sorted_res:
        status = "✓  resistant" if res.is_shock_resistant else "⚠️  fragile"
        lines.append(f"  {res.test_name}")
        lines.append(f"    Resistance: {res.resistance_score:.4f}  [{status}]")
        lines.append(f"    Max ΔEnv: {res.max_environment_change:.2f}  Shock Pass Rate: {res.shock_pass_rate:.2%}")
        lines.append("")

    fragile = sum(1 for r in resistances.values() if not r.is_shock_resistant)
    total = len(resistances)
    lines.append(f"Summary: {fragile}/{total} tests are shock-fragile")

    return "\n".join(lines)
