"""
BC Error Propagation — Ballistic Coefficient of Test Inconsistency.

Models how test inconsistency amplifies through the dependency tree,
analogous to a bullet's ballistic coefficient determining precision
degradation at range.
"""

from __future__ import annotations

import math
from typing import Sequence

from ussy_calibre.models import BCResult


def predict_sigma(sigma_consistency: float, scale: float, k: float) -> float:
    """
    Predict test inconsistency at a given integration scale.

    σ_test(S) = S^k × σ_consistency
    """
    return (scale ** k) * sigma_consistency


def fit_ballistic_coefficient(
    scales: Sequence[float],
    measured_sigmas: Sequence[float],
) -> float:
    """
    Fit the ballistic coefficient k from measured inconsistency data.

    Uses log-linear regression on the power-law model:
    σ(S) = S^k × σ_0
    log(σ) = k × log(S) + log(σ_0)

    Returns the fitted k value.
    """
    if len(scales) < 2 or len(scales) != len(measured_sigmas):
        return 0.5  # default medium BC

    # Filter out zero/negative values
    valid_pairs = [
        (s, sig) for s, sig in zip(scales, measured_sigmas)
        if s > 0 and sig > 0
    ]
    if len(valid_pairs) < 2:
        return 0.5

    log_s = [math.log(p[0]) for p in valid_pairs]
    log_sig = [math.log(p[1]) for p in valid_pairs]

    n = len(log_s)
    sum_x = sum(log_s)
    sum_y = sum(log_sig)
    sum_xy = sum(x * y for x, y in zip(log_s, log_sig))
    sum_xx = sum(x * x for x in log_s)

    denom = n * sum_xx - sum_x ** 2
    if abs(denom) < 1e-12:
        return 0.5

    k = (n * sum_xy - sum_x * sum_y) / denom
    # Clamp to reasonable range
    return max(0.01, min(k, 1.0))


def classify_bc(k: float) -> str:
    """
    Classify the ballistic coefficient.

    High BC (k ≈ 0.3): Well-isolated tests
    Medium BC (k ≈ 0.6): Some shared state
    Low BC (k ≈ 0.9): Tightly coupled tests
    """
    if k <= 0.35:
        return "high"
    elif k <= 0.65:
        return "medium"
    else:
        return "low"


def analyze_bc(
    sigma_consistency: float,
    k: float | None = None,
    scales: Sequence[float] | None = None,
    measured_sigmas: Sequence[float] | None = None,
) -> BCResult:
    """
    Full BC error propagation analysis.

    If k is not provided, it will be fitted from measured data.
    """
    if scales is None:
        scales = [1, 5, 10, 20]

    if k is None:
        if measured_sigmas is not None and len(measured_sigmas) == len(scales):
            k = fit_ballistic_coefficient(scales, measured_sigmas)
        else:
            k = 0.5

    return BCResult(
        k=k,
        sigma_consistency=sigma_consistency,
        scales=list(scales),
    )


def predict_e2e_inconsistency(
    sigma_consistency: float,
    k: float,
    e2e_scale: float,
    acceptable_cep: float = 0.1,
) -> dict:
    """
    Predict E2E inconsistency and compare against acceptable CEP_T.

    Returns dict with prediction and assessment.
    """
    predicted_sigma = predict_sigma(sigma_consistency, e2e_scale, k)
    predicted_cep = 1.1774 * predicted_sigma

    return {
        "e2e_scale": e2e_scale,
        "predicted_sigma": round(predicted_sigma, 6),
        "predicted_cep": round(predicted_cep, 6),
        "acceptable_cep": acceptable_cep,
        "exceeds_threshold": predicted_cep > acceptable_cep,
        "bc_classification": classify_bc(k),
    }
