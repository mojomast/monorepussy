"""
Weibull Maturity Classifier — Continuous Test Suite Maturity Spectrum.

Fits a Weibull distribution to test failure inter-arrival times
and classifies suite maturity on a continuous spectrum.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Sequence

from ussy_calibre.models import MaturityClass, WeibullResult


def compute_inter_arrival_times(
    failure_times: Sequence[datetime],
) -> list[float]:
    """
    Compute inter-arrival times (in seconds) between consecutive failures.
    """
    if len(failure_times) < 2:
        return []

    sorted_times = sorted(failure_times)
    intervals = []
    for i in range(1, len(sorted_times)):
        delta = (sorted_times[i] - sorted_times[i - 1]).total_seconds()
        if delta > 0:
            intervals.append(delta)
    return intervals


def fit_weibull_mle(intervals: Sequence[float]) -> tuple[float, float]:
    """
    Fit Weibull distribution parameters using maximum likelihood estimation.

    Uses scipy for numerical optimization if available, otherwise
    falls back to a method-of-moments approximation.

    Returns (beta, eta) — shape and scale parameters.
    """
    if not intervals:
        return 1.0, 1.0

    positive_intervals = [x for x in intervals if x > 0]
    if not positive_intervals:
        return 1.0, 1.0

    n = len(positive_intervals)

    try:
        import numpy as np
        from scipy.optimize import minimize

        data = np.array(positive_intervals)

        def neg_log_likelihood(params: np.ndarray) -> float:
            beta_val = params[0]
            eta_val = params[1]
            if beta_val <= 0 or eta_val <= 0:
                return 1e15
            n_log = n * math.log(beta_val / eta_val)
            log_sum = (beta_val - 1) * float(np.sum(np.log(data / eta_val)))
            power_sum = float(np.sum((data / eta_val) ** beta_val))
            return -(n_log + log_sum - power_sum)

        # Initial guess using method of moments
        mean_val = float(np.mean(data))
        std_val = float(np.std(data, ddof=1))
        if std_val > 0 and mean_val > 0:
            cv = std_val / mean_val
            beta_init = max(0.5, min(1.0 / cv, 5.0))
        else:
            beta_init = 1.0
        eta_init = mean_val / math.gamma(1 + 1 / beta_init)

        result = minimize(
            neg_log_likelihood,
            x0=np.array([beta_init, eta_init]),
            method="Nelder-Mead",
            options={"maxiter": 5000, "xatol": 1e-8, "fatol": 1e-8},
        )

        if result.success and result.x[0] > 0 and result.x[1] > 0:
            return float(result.x[0]), float(result.x[1])
    except ImportError:
        pass

    # Fallback: method of moments approximation
    mean_val = sum(positive_intervals) / n
    if n >= 2:
        var_val = sum(
            (x - mean_val) ** 2 for x in positive_intervals
        ) / (n - 1)
        std_val = math.sqrt(var_val) if var_val > 0 else 0
    else:
        std_val = 0

    if std_val > 0 and mean_val > 0:
        cv = std_val / mean_val
        # Approximate beta from coefficient of variation
        # For Weibull: CV² = Γ(1+2/β)/[Γ(1+1/β)]² - 1
        # Simple approximation: β ≈ 1/CV for CV near 1
        beta = max(0.5, min(1.0 / cv, 5.0))
    else:
        beta = 1.0

    eta = mean_val / math.gamma(1 + 1 / beta)
    return beta, eta


def classify_maturity(beta: float) -> MaturityClass:
    """
    Classify test suite maturity from the Weibull shape parameter.

    β < 0.8   → Fragile
    0.8 - 1.2 → Unstable
    1.2 - 2.0 → Maturing
    2.0 - 3.0 → Stable
    β > 3.0   → Robust
    """
    if beta < 0.8:
        return MaturityClass.FRAGILE
    elif beta < 1.2:
        return MaturityClass.UNSTABLE
    elif beta < 2.0:
        return MaturityClass.MATURING
    elif beta < 3.0:
        return MaturityClass.STABLE
    else:
        return MaturityClass.ROBUST


def analyze_maturity(
    failure_times: Sequence[datetime],
    suite: str = "",
) -> WeibullResult:
    """
    Full Weibull maturity analysis for a test suite.
    """
    intervals = compute_inter_arrival_times(failure_times)
    n_failures = len(failure_times)

    if not intervals:
        return WeibullResult(suite=suite, beta=1.0, eta=1.0, n_failures=n_failures)

    beta, eta = fit_weibull_mle(intervals)

    return WeibullResult(
        suite=suite,
        beta=round(beta, 4),
        eta=round(eta, 4),
        n_failures=n_failures,
    )


def maturity_trend(
    beta_history: Sequence[float],
) -> str:
    """
    Assess maturity trend from historical beta values.

    Returns "improving", "degrading", or "stable".
    """
    if len(beta_history) < 2:
        return "stable"

    recent = list(beta_history[-3:]) if len(beta_history) >= 3 else list(beta_history)
    early = list(beta_history[:3]) if len(beta_history) >= 3 else list(beta_history[:1])

    mean_recent = sum(recent) / len(recent)
    mean_early = sum(early) / len(early)

    if mean_recent > mean_early * 1.1:
        return "improving"
    elif mean_recent < mean_early * 0.9:
        return "degrading"
    else:
        return "stable"
