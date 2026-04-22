"""Drift Detector — Measurement Instrument Drift with CUSUM.

Linear drift model: d(t) = d_0 + alpha*t + sum(Delta_i) + epsilon(t)

Where:
  d_0 = initial bias
  alpha = drift rate
  Delta_i = shock events (refactors)
  epsilon(t) = random noise

CUSUM detection:
  S_t^+ = max(0, S_{t-1}^+ + (d_t - mu_0 - K))
  S_t^- = max(0, S_{t-1}^- + (mu_0 + K - d_t))
  Alarm when |S_t| > H

Calibration interval:
  t_max = (MPE - d_0) / alpha

Zombie test detection:
  Tests that always pass but have drifted beyond MPE.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

from calibre.models import DriftObservation, DriftResult


def fit_linear_drift(
    timestamps: List[datetime],
    values: List[float],
) -> Tuple[float, float]:
    """Fit linear drift model d(t) = d_0 + alpha * t.

    Uses ordinary least squares.
    Returns (d_0, alpha) where alpha is drift rate per day.
    """
    n = len(timestamps)
    if n < 2:
        return (values[0] if values else 0.0, 0.0)

    # Convert timestamps to days from first observation
    t0 = timestamps[0]
    t_days = [(ts - t0).total_seconds() / 86400.0 for ts in timestamps]

    # OLS: y = d_0 + alpha * t
    sum_t = sum(t_days)
    sum_y = sum(values)
    sum_tt = sum(t * t for t in t_days)
    sum_ty = sum(t * y for t, y in zip(t_days, values))

    denom = n * sum_tt - sum_t**2
    if abs(denom) < 1e-15:
        return (sum_y / n, 0.0)

    d_0 = (sum_y * sum_tt - sum_t * sum_ty) / denom
    alpha = (n * sum_ty - sum_t * sum_y) / denom

    return (d_0, alpha)


def detect_cusum(
    values: List[float],
    target: float,
    k: float = 0.5,
    h: float = 5.0,
) -> Tuple[List[float], List[float], List[int]]:
    """Run CUSUM detection on a sequence of values.

    Args:
        values: Observed values over time.
        target: Expected value (mu_0).
        k: Reference value (slack). Typically 0.5 * sigma.
        h: Decision interval (threshold). Typically 4-5 * sigma.

    Returns:
        (S_plus, S_minus, alert_indices)
        where alert_indices are the time indices where CUSUM triggered.
    """
    n = len(values)
    s_plus: List[float] = [0.0] * n
    s_minus: List[float] = [0.0] * n
    alerts: List[int] = []

    for i in range(n):
        if i == 0:
            s_plus[i] = max(0.0, values[i] - target - k)
            s_minus[i] = max(0.0, target - values[i] - k)
        else:
            s_plus[i] = max(0.0, s_plus[i - 1] + (values[i] - target - k))
            s_minus[i] = max(0.0, s_minus[i - 1] + (target - values[i] - k))

        if s_plus[i] > h or s_minus[i] > h:
            alerts.append(i)

    return (s_plus, s_minus, alerts)


def detect_shock_events(
    values: List[float],
    threshold_sigma: float = 3.0,
) -> List[int]:
    """Detect shock events (sudden large changes) in the value series.

    Uses a robust approach: compute the median absolute deviation (MAD)
    of consecutive differences and flag outliers. This is more resistant
    to a single large shock inflating the standard deviation.
    """
    if len(values) < 3:
        return []

    diffs = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    if not diffs:
        return []

    # Use median and MAD for robustness
    sorted_diffs = sorted(diffs)
    n = len(sorted_diffs)
    median_diff = sorted_diffs[n // 2] if n % 2 == 1 else (sorted_diffs[n // 2 - 1] + sorted_diffs[n // 2]) / 2

    # MAD (median absolute deviation)
    abs_devs = sorted(abs(d - median_diff) for d in diffs)
    mad = abs_devs[len(abs_devs) // 2]

    # Convert MAD to estimate of sigma: sigma ≈ 1.4826 * MAD
    sigma_est = 1.4826 * mad

    if sigma_est < 1e-10:
        # If MAD is zero, fall back to std but require absolute threshold too
        mean_diff = sum(diffs) / len(diffs)
        var_diff = sum((d - mean_diff) ** 2 for d in diffs) / len(diffs)
        sigma_est = var_diff ** 0.5
        if sigma_est < 1e-10:
            return []

    shocks: List[int] = []
    for i, d in enumerate(diffs):
        if d > threshold_sigma * sigma_est:
            shocks.append(i + 1)  # index in original values

    return shocks


def compute_recalibration_interval(
    mpe: float, initial_bias: float, drift_rate: float
) -> float:
    """Compute maximum time before recalibration is needed.

    t_max = (MPE - d_0) / alpha

    Returns days until recalibration needed. Returns inf if no drift.
    """
    if abs(drift_rate) < 1e-15:
        return float("inf")
    interval = (mpe - abs(initial_bias)) / abs(drift_rate)
    return max(0.0, interval)


def analyze_drift(
    observations: List[DriftObservation],
    mpe: float = 0.1,
    cusum_k: float = 0.5,
    cusum_h: float = 5.0,
) -> DriftResult:
    """Perform complete drift analysis for a test.

    Args:
        observations: Time-ordered drift observations.
        mpe: Maximum Permissible Error for drift.
        cusum_k: CUSUM reference value.
        cusum_h: CUSUM decision interval.
    """
    if not observations:
        return DriftResult(
            test_name="unknown",
            mpe=mpe,
            diagnosis="No data available",
        )

    test_name = observations[0].test_name
    timestamps = [obs.timestamp for obs in observations]
    values = [obs.observed_value for obs in observations]

    if len(values) < 2:
        return DriftResult(
            test_name=test_name,
            initial_bias=values[0] if values else 0.0,
            mpe=mpe,
            diagnosis="Insufficient data for drift analysis",
        )

    # Fit linear drift model
    d_0, alpha = fit_linear_drift(timestamps, values)

    # Compute cumulative drift
    total_time_days = (timestamps[-1] - timestamps[0]).total_seconds() / 86400.0
    cumulative_drift = abs(alpha * total_time_days)

    # CUSUM detection
    target = values[0] if values else 0.0
    # Estimate sigma for CUSUM parameters
    if len(values) >= 2:
        diffs = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
        sigma_est = sum(diffs) / len(diffs) if diffs else 1.0
    else:
        sigma_est = 1.0

    cusum_k_adj = cusum_k * sigma_est
    cusum_h_adj = cusum_h * sigma_est

    _, _, cusum_alerts = detect_cusum(values, target, cusum_k_adj, cusum_h_adj)

    # Detect shock events
    shock_indices = detect_shock_events(values)
    shock_dates = [timestamps[i] for i in shock_indices if i < len(timestamps)]

    # Check MPE
    exceeds_mpe = cumulative_drift > mpe

    # Zombie test detection: always passes but drifted beyond MPE
    all_pass = all(v >= 0.95 for v in values)  # assuming pass rate >= 0.95
    is_zombie = all_pass and exceeds_mpe

    # Recalibration interval
    recal_interval = compute_recalibration_interval(mpe, d_0, alpha)

    # Diagnosis
    if is_zombie:
        diagnosis = (
            f"ZOMBIE TEST: Always passes but drifted {cumulative_drift:.4f} beyond MPE={mpe:.4f}. "
            f"Expectations are too loose — recalibrate test."
        )
    elif exceeds_mpe:
        diagnosis = (
            f"Drift exceeds MPE: cumulative={cumulative_drift:.4f} > MPE={mpe:.4f}. "
            f"Drift rate α={alpha:.6f}/day."
        )
    elif cusum_alerts:
        diagnosis = (
            f"CUSUM detected drift at {len(cusum_alerts)} point(s). "
            f"Drift rate α={alpha:.6f}/day. Within MPE but trending."
        )
    else:
        diagnosis = (
            f"Drift within acceptable limits. "
            f"Rate α={alpha:.6f}/day. "
            f"Recalibration in {recal_interval:.0f} days."
        )

    return DriftResult(
        test_name=test_name,
        drift_rate=alpha,
        initial_bias=d_0,
        cumulative_drift=cumulative_drift,
        mpe=mpe,
        exceeds_mpe=exceeds_mpe,
        is_zombie=is_zombie,
        shock_events=shock_dates,
        cusum_alerts=cusum_alerts,
        recalibration_interval_days=recal_interval,
        diagnosis=diagnosis,
    )


def format_drift_result(result: DriftResult) -> str:
    """Format a drift analysis result as a readable report."""
    lines: List[str] = []
    lines.append(f"{'='*60}")
    lines.append(f"Drift Analysis: {result.test_name}")
    lines.append(f"{'='*60}")
    lines.append("")
    lines.append(f"  Initial bias (d₀):     {result.initial_bias:.6f}")
    lines.append(f"  Drift rate (α):        {result.drift_rate:.6f} /day")
    lines.append(f"  Cumulative drift:      {result.cumulative_drift:.6f}")
    lines.append(f"  MPE:                   {result.mpe:.6f}")
    lines.append(f"  Exceeds MPE:           {'YES' if result.exceeds_mpe else 'NO'}")
    lines.append(f"  Zombie test:           {'YES' if result.is_zombie else 'NO'}")
    lines.append(f"  CUSUM alerts:          {len(result.cusum_alerts)}")
    lines.append(f"  Shock events:          {len(result.shock_events)}")

    if result.recalibration_interval_days != float("inf"):
        lines.append(f"  Recalibration in:      {result.recalibration_interval_days:.0f} days")
    else:
        lines.append(f"  Recalibration in:      ∞ (no detectable drift)")

    lines.append("")
    lines.append(f"  Diagnosis: {result.diagnosis}")
    lines.append("")

    return "\n".join(lines)
