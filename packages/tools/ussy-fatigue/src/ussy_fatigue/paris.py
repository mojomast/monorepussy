"""Paris' Law calibration — determines codebase-specific material constants.

da/dN = C × (ΔK)^m

Implements simple least-squares fitting using only Python stdlib.
"""

from __future__ import annotations

import math
from typing import Optional

from .models import MaterialConstants


def paris_law(delta_K: float, C: float, m: float) -> float:
    """Calculate crack growth rate using Paris' Law.

    da/dN = C × (ΔK)^m

    Args:
        delta_K: Stress intensity factor range.
        C: Crack growth coefficient.
        m: Stress exponent.

    Returns:
        Crack growth rate (da/dN).
    """
    if delta_K <= 0:
        return 0.0
    return C * (delta_K ** m)


def log_paris_law(log_delta_K: float, log_C: float, m: float) -> float:
    """Log-transformed Paris' Law: log(da/dN) = log(C) + m × log(ΔK).

    This is linear in parameters log(C) and m, enabling simple linear regression.
    """
    return log_C + m * log_delta_K


def calibrate_material_constants(
    delta_K_values: list[float],
    growth_rates: list[float],
    K_Ic: float = 28.0,
    K_e: float = 8.2,
) -> MaterialConstants:
    """Calibrate Paris' Law material constants from observed data.

    Uses log-linear regression: log(da/dN) = log(C) + m × log(ΔK)
    which is a simple linear least-squares problem.

    Args:
        delta_K_values: Observed stress intensity factor ranges.
        growth_rates: Observed crack growth rates (da/dN).
        K_Ic: Fracture toughness threshold.
        K_e: Endurance limit threshold.

    Returns:
        MaterialConstants with calibrated C, m, and R².
    """
    # Filter out non-positive values (can't take log)
    valid_pairs = [
        (dk, gr) for dk, gr in zip(delta_K_values, growth_rates)
        if dk > 0 and gr > 0
    ]

    if len(valid_pairs) < 2:
        # Not enough data, return defaults
        return MaterialConstants(
            C=0.015, m=2.5, K_Ic=K_Ic, K_e=K_e, r_squared=0.0
        )

    x = [math.log(dk) for dk, _ in valid_pairs]  # log(ΔK)
    y = [math.log(gr) for _, gr in valid_pairs]    # log(da/dN)

    n = len(x)

    # Simple linear regression: y = a + b*x
    # where a = log(C), b = m
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_x2 = sum(xi * xi for xi in x)

    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-12:
        return MaterialConstants(
            C=0.015, m=2.5, K_Ic=K_Ic, K_e=K_e, r_squared=0.0
        )

    # Slope (m) and intercept (log(C))
    b = (n * sum_xy - sum_x * sum_y) / denom
    a = (sum_y - b * sum_x) / n

    C = math.exp(a)
    m = b

    # Ensure physical constraints
    C = max(C, 1e-8)
    m = max(m, 0.5)

    # Compute R²
    y_mean = sum_y / n
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    y_pred = [a + b * xi for xi in x]
    ss_res = sum((yi - yp) ** 2 for yi, yp in zip(y, y_pred))

    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    r_squared = max(0.0, min(1.0, r_squared))

    return MaterialConstants(
        C=round(C, 6),
        m=round(m, 2),
        K_Ic=K_Ic,
        K_e=K_e,
        r_squared=round(r_squared, 4),
    )


def calibrate_from_history(
    historical_data: list[dict],
    K_Ic: float = 28.0,
    K_e: float = 8.2,
) -> MaterialConstants:
    """Calibrate material constants from historical commit data.

    Each entry in historical_data should have:
        - 'delta_K': stress intensity range
        - 'growth_rate': observed debt growth rate (da/dN)

    Args:
        historical_data: List of dicts with delta_K and growth_rate.
        K_Ic: Fracture toughness threshold.
        K_e: Endurance limit threshold.

    Returns:
        Calibrated MaterialConstants.
    """
    delta_K_values = [d['delta_K'] for d in historical_data if 'delta_K' in d and 'growth_rate' in d]
    growth_rates = [d['growth_rate'] for d in historical_data if 'delta_K' in d and 'growth_rate' in d]

    return calibrate_material_constants(delta_K_values, growth_rates, K_Ic, K_e)


def calibrate_per_module(
    module_data: dict[str, list[dict]],
    K_Ic: float = 28.0,
    K_e: float = 8.2,
) -> dict[str, MaterialConstants]:
    """Calibrate material constants per module.

    Args:
        module_data: Mapping from module name to list of historical data dicts.
        K_Ic: Fracture toughness threshold.
        K_e: Endurance limit threshold.

    Returns:
        Mapping from module name to calibrated MaterialConstants.
    """
    result: dict[str, MaterialConstants] = {}
    for module, data in module_data.items():
        result[module] = calibrate_from_history(data, K_Ic, K_e)
    return result


def estimate_endurance_limit(
    delta_K_values: list[float],
    growth_rates: list[float],
) -> float:
    """Estimate the endurance limit from observed data.

    The endurance limit is the ΔK below which no fatigue growth occurs.
    Estimated as the minimum ΔK for which non-zero growth was observed,
    minus a safety margin.

    Args:
        delta_K_values: Observed stress intensity ranges.
        growth_rates: Observed growth rates.

    Returns:
        Estimated endurance limit.
    """
    positive_growth = [
        dk for dk, gr in zip(delta_K_values, growth_rates)
        if gr > 0 and dk > 0
    ]

    if not positive_growth:
        return 8.2  # Default

    # Endurance limit is below the minimum ΔK that showed growth
    min_dk = min(positive_growth)
    return round(min_dk * 0.8, 2)  # 80% of minimum observed growth ΔK


def estimate_fracture_toughness(
    delta_K_values: list[float],
    growth_rates: list[float],
) -> float:
    """Estimate the fracture toughness from observed data.

    The fracture toughness K_Ic is the ΔK above which crack growth
    becomes catastrophic (rapidly accelerating). Estimated by finding
    the inflection point in the growth rate vs. ΔK curve.

    Args:
        delta_K_values: Observed stress intensity ranges.
        growth_rates: Observed growth rates.

    Returns:
        Estimated fracture toughness.
    """
    pairs = [(dk, gr) for dk, gr in zip(delta_K_values, growth_rates) if dk > 0 and gr > 0]

    if len(pairs) < 3:
        return 28.0  # Default

    # Sort by delta_K
    pairs.sort(key=lambda p: p[0])

    # Look for acceleration point: where growth rate increase per unit ΔK
    # exceeds the average by 2x
    accelerations = []
    for i in range(1, len(pairs)):
        dk_diff = pairs[i][0] - pairs[i - 1][0]
        gr_diff = pairs[i][1] - pairs[i - 1][1]
        if dk_diff > 0:
            accelerations.append((pairs[i][0], gr_diff / dk_diff))

    if not accelerations:
        return 28.0

    avg_accel = sum(a for _, a in accelerations) / len(accelerations)

    # Find the first point where acceleration exceeds 2x average
    for dk, accel in accelerations:
        if accel > 2 * avg_accel and avg_accel > 0:
            return round(dk * 0.9, 2)  # Slightly below inflection

    # Fallback: use 75th percentile of ΔK values
    sorted_dk = sorted(p[0] for p in pairs)
    idx = int(len(sorted_dk) * 0.75)
    return round(sorted_dk[idx], 2)
