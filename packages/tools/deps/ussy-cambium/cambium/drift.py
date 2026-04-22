"""Drift forecasting — Predictive drift breakage analysis."""

from __future__ import annotations

import math

from cambium.models import CompatibilityZone, DriftDebt


def compute_drift_debt(
    delta_behavior: float = 0.0,
    delta_contract: float = 0.0,
    delta_environment: float = 0.0,
    lambda_s: float = 6.0,
    d_critical: float = 1.0,
) -> DriftDebt:
    """Create a DriftDebt model from drift parameters."""
    return DriftDebt(
        delta_behavior=delta_behavior,
        delta_contract=delta_contract,
        delta_environment=delta_environment,
        lambda_s=lambda_s,
        d_critical=d_critical,
    )


def drift_forecast(debt: DriftDebt, months: int = 24, step: float = 1.0) -> list[dict]:
    """Generate drift debt forecast for N months."""
    result: list[dict] = []
    t = 0.0
    while t <= months:
        d = debt.drift_at(t)
        budget = debt.drift_budget_consumed(t)
        result.append({
            "month": round(t, 1),
            "drift_debt": round(d, 4),
            "budget_consumed": round(budget, 4),
        })
        t += step
    return result


def classify_drift_zone(debt: DriftDebt) -> dict:
    """Classify the drift zone and provide analysis."""
    zone = debt.zone
    t_break = debt.breakage_time

    analysis: dict = {
        "zone": zone.value,
        "delta_total": round(debt.delta_0, 4),
        "delta_behavior": round(debt.delta_behavior, 4),
        "delta_contract": round(debt.delta_contract, 4),
        "delta_environment": round(debt.delta_environment, 4),
        "lambda_s": debt.lambda_s,
        "d_critical": debt.d_critical,
        "product_delta_lambda": round(debt.delta_0 * debt.lambda_s, 4),
    }

    if zone == CompatibilityZone.DOOMED:
        analysis["breakage_time_months"] = round(t_break, 1)
        analysis["message"] = (
            f"DOOMED: Drift exceeds dissipation. Breakage predicted in ~{t_break:.1f} months."
        )
    else:
        analysis["breakage_time_months"] = None
        analysis["message"] = (
            "SAFE: Dissipation exceeds drift. Integration is stable."
        )

    return analysis


def format_drift_report(debt: DriftDebt) -> str:
    """Format a drift forecast report with ASCII chart."""
    lines: list[str] = []
    lines.append("Drift Debt Accumulation Forecast")
    lines.append("═" * 50)

    analysis = classify_drift_zone(debt)
    lines.append(f"  Zone: {analysis['zone'].upper()}")
    lines.append(f"  Δ_behavior:   {debt.delta_behavior:.3f}")
    lines.append(f"  Δ_contract:   {debt.delta_contract:.3f}")
    lines.append(f"  Δ_environment:{debt.delta_environment:.3f}")
    lines.append(f"  Δ_total:      {debt.delta_0:.3f}")
    lines.append(f"  λ_s:          {debt.lambda_s:.1f} months")
    lines.append(f"  D_critical:   {debt.d_critical:.1f}")
    lines.append(f"  Δ₀·λ_s:       {debt.delta_0 * debt.lambda_s:.3f}")

    if debt.zone == CompatibilityZone.DOOMED:
        lines.append(f"  ⚠️  Breakage predicted in ~{debt.breakage_time:.1f} months")
    else:
        lines.append("  ✅ Safe — dissipation exceeds drift accumulation")

    lines.append("")
    lines.append("  " + analysis["message"])
    lines.append("")

    # ASCII chart
    lines.append("  Drift Accumulation Chart:")
    lines.append(f"  D_critical {'─' * 5} {'─' * 30}")

    forecast = drift_forecast(debt, months=24, step=2)
    max_drift = max(f["drift_debt"] for f in forecast) if forecast else 1.0
    scale = min(max_drift, debt.d_critical * 1.2) if max_drift > 0 else 1.0

    for point in forecast:
        bar_len = int(point["drift_debt"] / scale * 30) if scale > 0 else 0
        bar_len = min(bar_len, 30)
        marker = "⚠️" if point["budget_consumed"] > 0.8 else ""
        lines.append(f"  m{point['month']:5.0f} {'█' * bar_len} {point['drift_debt']:.2f} {marker}")

    return "\n".join(lines)
