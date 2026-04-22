"""
Dispersion Ellipse — Correlated Error Mode Detection.

Computes the covariance matrix of FP and FN rates, extracts
eigenvalues/eigenvectors, and classifies the error mode.
"""

from __future__ import annotations

import math
from typing import Sequence

from ussy_calibre.models import DispersionResult, EllipseShape, TestExecution


def compute_covariance(
    fp_rates: Sequence[float],
    fn_rates: Sequence[float],
    sigma_fp: float,
    sigma_fn: float,
) -> float:
    """
    Compute the covariance between FP and FN rate sequences.
    """
    n = len(fp_rates)
    if n < 2:
        return 0.0

    mean_fp = sum(fp_rates) / n
    mean_fn = sum(fn_rates) / n

    cov = sum(
        (fp_rates[i] - mean_fp) * (fn_rates[i] - mean_fn)
        for i in range(n)
    ) / (n - 1)

    return cov


def analyze_dispersion(
    executions: Sequence[TestExecution],
    test_name: str = "",
) -> DispersionResult:
    """
    Analyze the dispersion ellipse for a set of test executions.

    Computes covariance matrix eigenstructure and classifies the error mode.
    """
    if not executions:
        return DispersionResult(test_name=test_name)

    # Group by run to get per-run rates
    run_ids = sorted(set(e.run_id for e in executions))
    if len(run_ids) > 1 and any(r for r in run_ids):
        fp_rates: list[float] = []
        fn_rates: list[float] = []
        for run_id in run_ids:
            run_execs = [e for e in executions if e.run_id == run_id]
            fp_count = sum(1 for e in run_execs if e.is_false_positive)
            fn_count = sum(1 for e in run_execs if e.is_false_negative)
            n = len(run_execs)
            fp_rates.append(fp_count / n if n > 0 else 0.0)
            fn_rates.append(fn_count / n if n > 0 else 0.0)
    else:
        # Per-test rates
        test_names = sorted(set(e.test_name for e in executions))
        fp_rates = []
        fn_rates = []
        for tn in test_names:
            test_execs = [e for e in executions if e.test_name == tn]
            fp_count = sum(1 for e in test_execs if e.is_false_positive)
            fn_count = sum(1 for e in test_execs if e.is_false_negative)
            n = len(test_execs)
            fp_rates.append(fp_count / n if n > 0 else 0.0)
            fn_rates.append(fn_count / n if n > 0 else 0.0)

    if not fp_rates or not fn_rates:
        return DispersionResult(test_name=test_name)

    # Compute standard deviations
    n = len(fp_rates)
    mean_fp = sum(fp_rates) / n
    mean_fn = sum(fn_rates) / n

    if n < 2:
        sigma_fp = 0.0
        sigma_fn = 0.0
        cov = 0.0
    else:
        var_fp = sum((x - mean_fp) ** 2 for x in fp_rates) / (n - 1)
        var_fn = sum((x - mean_fn) ** 2 for x in fn_rates) / (n - 1)
        sigma_fp = math.sqrt(var_fp) if var_fp > 0 else 0.0
        sigma_fn = math.sqrt(var_fn) if var_fn > 0 else 0.0
        cov = compute_covariance(fp_rates, fn_rates, sigma_fp, sigma_fn)

    return DispersionResult(
        test_name=test_name,
        sigma_fp=sigma_fp,
        sigma_fn=sigma_fn,
        covariance=cov,
    )


def classify_ellipse(result: DispersionResult) -> EllipseShape:
    """
    Classify the dispersion ellipse shape.

    Returns the ellipse shape classification.
    """
    return result.shape


def is_systematic_bias(result: DispersionResult) -> bool:
    """
    Determine if the dispersion indicates systematic (non-random) bias.

    Returns True if the ellipse is tilted (high covariance), indicating
    that FP and FN rates are coupled — a structural test quality problem.
    """
    return result.shape == EllipseShape.TILTED
