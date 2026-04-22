"""
Grouping Analyzer — Rayleigh Precision Parameter (σ_T).

Models test quality as a bivariate normal distribution of
false positive and false negative rates, producing a single
Rayleigh precision parameter.
"""

from __future__ import annotations

import math
from typing import Sequence

from ussy_calibre.models import GroupingResult, TestExecution


def compute_fp_fn_rates(
    executions: Sequence[TestExecution],
) -> tuple[float, float]:
    """
    Compute false positive and false negative rates from test executions.

    Returns (fp_rate, fn_rate).
    """
    if not executions:
        return 0.0, 0.0
    n = len(executions)
    fp_count = sum(1 for e in executions if e.is_false_positive)
    fn_count = sum(1 for e in executions if e.is_false_negative)
    return fp_count / n, fn_count / n


def compute_sigma_from_rates(
    fp_rates: Sequence[float],
    fn_rates: Sequence[float],
) -> tuple[float, float]:
    """
    Compute σ_FP and σ_FN from sequences of per-run or per-test rates.

    Returns (sigma_fp, sigma_fn).
    """
    if not fp_rates or not fn_rates:
        return 0.0, 0.0

    n = len(fp_rates)
    mean_fp = sum(fp_rates) / n
    mean_fn = sum(fn_rates) / n

    if n < 2:
        return 0.0, 0.0

    var_fp = sum((x - mean_fp) ** 2 for x in fp_rates) / (n - 1)
    var_fn = sum((x - mean_fn) ** 2 for x in fn_rates) / (n - 1)

    return math.sqrt(var_fp), math.sqrt(var_fn)


def analyze_grouping(
    executions: Sequence[TestExecution],
    test_name: str = "",
) -> GroupingResult:
    """
    Analyze the precision grouping for a set of test executions.

    Computes σ_T from the bivariate FP×FN distribution.
    """
    if not executions:
        return GroupingResult(test_name=test_name, n_runs=0)

    # Group by run_id if available, otherwise treat each execution as one run
    run_ids = set(e.run_id for e in executions)
    if len(run_ids) > 1 and any(r for r in run_ids):
        # Multiple runs: compute per-run FP/FN rates
        fp_rates: list[float] = []
        fn_rates: list[float] = []
        for run_id in sorted(run_ids):
            run_execs = [e for e in executions if e.run_id == run_id]
            fp_rate, fn_rate = compute_fp_fn_rates(run_execs)
            fp_rates.append(fp_rate)
            fn_rates.append(fn_rate)
    else:
        # Single or no runs: compute per-test FP/FN rates
        test_names = sorted(set(e.test_name for e in executions))
        fp_rates = []
        fn_rates = []
        for tn in test_names:
            test_execs = [e for e in executions if e.test_name == tn]
            fp, fn = compute_fp_fn_rates(test_execs)
            fp_rates.append(fp)
            fn_rates.append(fn)

    sigma_fp, sigma_fn = compute_sigma_from_rates(fp_rates, fn_rates)

    return GroupingResult(
        test_name=test_name,
        sigma_fp=sigma_fp,
        sigma_fn=sigma_fn,
        n_runs=len(executions),
    )


def analyze_suite(
    executions: Sequence[TestExecution],
    suite: str = "",
) -> list[GroupingResult]:
    """
    Analyze grouping for each test in a suite individually.
    """
    test_names = sorted(set(e.test_name for e in executions))
    results = []
    for name in test_names:
        test_execs = [e for e in executions if e.test_name == name]
        result = analyze_grouping(test_execs, test_name=name)
        results.append(result)
    return results


def compute_suite_sigma(
    results: Sequence[GroupingResult],
) -> float:
    """
    Compute an aggregate σ_T for a whole suite from individual results.
    """
    if not results:
        return 0.0
    sigma_ts = [r.sigma_t for r in results if r.sigma_t > 0]
    if not sigma_ts:
        return 0.0
    # RMS of individual σ_T values
    return math.sqrt(sum(s ** 2 for s in sigma_ts) / len(sigma_ts))
