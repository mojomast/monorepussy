"""
Windage/Elevation Calibration — Systematic Bias Correction Framework.

Provides auditable, verifiable test bias correction, analogous to
windage (left-right) and elevation (up-down) adjustments in marksmanship.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Sequence

from ussy_calibre.models import (
    BiasDirection,
    CalibrationClick,
    CalibrationResult,
    GroupingResult,
)


def identify_bias(result: GroupingResult) -> BiasDirection:
    """
    Identify the bias direction from a grouping result.

    FP-heavy → test is trigger-happy
    FN-heavy → test has blind spots
    Balanced → no significant directional bias
    """
    if result.sigma_fp > result.sigma_fn * 1.5:
        return BiasDirection.FP_HEAVY
    elif result.sigma_fn > result.sigma_fp * 1.5:
        return BiasDirection.FN_HEAVY
    return BiasDirection.BALANCED


def compute_required_correction(
    current_fp_rate: float,
    current_fn_rate: float,
    target_cep: float = 0.05,
) -> tuple[float, float]:
    """
    Compute the required FP and FN rate corrections to achieve target CEP_T.

    The target σ_T = target_cep / 1.1774
    We need both FP and FN to be reduced proportionally.
    """
    target_sigma = target_cep / 1.1774

    # Current σ_T
    current_sigma = math.sqrt(current_fp_rate ** 2 + current_fn_rate ** 2)

    if current_sigma <= target_sigma:
        return 0.0, 0.0

    # Proportional reduction
    ratio = target_sigma / current_sigma
    required_fp = current_fp_rate * (1 - ratio)
    required_fn = current_fn_rate * (1 - ratio)

    return required_fp, required_fn


def create_calibration_click(
    direction: BiasDirection,
    description: str,
    expected_fp_change: float,
    expected_fn_change: float,
) -> CalibrationClick:
    """
    Create a calibration click record.
    """
    # Determine number of "clicks" based on magnitude of correction
    magnitude = max(abs(expected_fp_change), abs(expected_fn_change))
    clicks = max(1, int(round(magnitude * 100)))

    return CalibrationClick(
        timestamp=datetime.now(timezone.utc),
        direction=direction,
        clicks=clicks,
        description=description,
        expected_fp_change=expected_fp_change,
        expected_fn_change=expected_fn_change,
    )


def verify_calibration(
    click: CalibrationClick,
    actual_fp_change: float,
    actual_fn_change: float,
    tolerance: float = 0.1,
) -> CalibrationClick:
    """
    Verify a calibration click by comparing predicted vs actual change.

    Returns an updated CalibrationClick with actual values and verification status.
    """
    click.actual_fp_change = actual_fp_change
    click.actual_fn_change = actual_fn_change

    fp_error = abs(click.expected_fp_change - actual_fp_change)
    fn_error = abs(click.expected_fn_change - actual_fn_change)

    max_expected = max(abs(click.expected_fp_change), abs(click.expected_fn_change), 0.01)
    fp_accuracy = fp_error / max_expected
    fn_accuracy = fn_error / max_expected

    click.verified = fp_accuracy <= tolerance and fn_accuracy <= tolerance
    return click


def compute_calibration_accuracy(
    clicks: Sequence[CalibrationClick],
) -> float | None:
    """
    Compute overall calibration accuracy from verified clicks.

    Returns accuracy as a ratio (0-1) or None if no verified clicks.
    """
    verified = [c for c in clicks if c.verified and c.actual_fp_change is not None]
    if not verified:
        return None

    total_error = 0.0
    total_expected = 0.0

    for c in verified:
        total_error += abs(c.expected_fp_change - (c.actual_fp_change or 0))
        total_error += abs(c.expected_fn_change - (c.actual_fn_change or 0))
        total_expected += abs(c.expected_fp_change)
        total_expected += abs(c.expected_fn_change)

    if total_expected == 0:
        return 1.0

    return max(0.0, 1.0 - total_error / total_expected)


def analyze_calibration(
    grouping_result: GroupingResult,
    suite: str = "",
    target_cep: float = 0.05,
) -> CalibrationResult:
    """
    Full windage/elevation calibration analysis.

    Identifies bias, computes required corrections, and generates
    calibration click recommendations.
    """
    fp_rate = grouping_result.sigma_fp
    fn_rate = grouping_result.sigma_fn

    required_fp, required_fn = compute_required_correction(
        fp_rate, fn_rate, target_cep
    )

    bias = identify_bias(grouping_result)

    clicks: list[CalibrationClick] = []
    if required_fp > 0:
        click = create_calibration_click(
            direction=BiasDirection.FP_HEAVY,
            description=f"Reduce false positive rate by {required_fp:.4f}",
            expected_fp_change=-required_fp,
            expected_fn_change=0.0,
        )
        clicks.append(click)

    if required_fn > 0:
        click = create_calibration_click(
            direction=BiasDirection.FN_HEAVY,
            description=f"Reduce false negative rate by {required_fn:.4f}",
            expected_fp_change=0.0,
            expected_fn_change=-required_fn,
        )
        clicks.append(click)

    return CalibrationResult(
        suite=suite,
        current_fp_rate=fp_rate,
        current_fn_rate=fn_rate,
        bias_direction=bias,
        target_cep=target_cep,
        required_fp_correction=required_fp,
        required_fn_correction=required_fn,
        clicks=clicks,
    )
