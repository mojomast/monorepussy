"""Bond trajectory — Integration bond strength analysis."""

from __future__ import annotations

from cambium.models import BondStrength, BondTrend


def compute_bond_strength(
    b_max: float = 1.0,
    k_b: float = 0.3,
    t50: float = 5.0,
    s_test: float = 0.0,
    s_incident: float = 0.0,
    s_change: float = 0.0,
    s_doc: float = 0.0,
) -> BondStrength:
    """Create a BondStrength model from parameters."""
    return BondStrength(
        b_max=b_max,
        k_b=k_b,
        t50=t50,
        s_test=s_test,
        s_incident=s_incident,
        s_change=s_change,
        s_doc=s_doc,
    )


def bond_trajectory(bond: BondStrength, months: int = 24, step: float = 1.0) -> list[dict]:
    """Generate bond strength trajectory over time."""
    result: list[dict] = []
    t = 0.0
    while t <= months:
        strength = bond.strength_at(t)
        rate = bond.strength_rate(t)
        trend = bond.trend_at(t)
        result.append({
            "month": round(t, 1),
            "strength": round(strength, 4),
            "rate": round(rate, 6),
            "trend": trend.value,
        })
        t += step
    return result


def detect_decay(bond: BondStrength, months: int = 24) -> list[dict]:
    """Detect periods where dB/dt < 0 (bond strength decaying)."""
    decay_periods: list[dict] = []
    prev_rate = None

    for point in bond_trajectory(bond, months=months, step=0.5):
        if point["trend"] == "decaying":
            decay_periods.append({
                "month": point["month"],
                "strength": point["strength"],
                "rate": point["rate"],
            })

    return decay_periods


def format_bond_report(bond: BondStrength) -> str:
    """Format bond trajectory report with ASCII chart."""
    lines: list[str] = []
    lines.append("Integration Bond Strength Trajectory")
    lines.append("═" * 50)

    # Current state (at t=0)
    current = bond.strength_at(0)
    rate = bond.strength_rate(0)
    trend = bond.trend_at(0)

    lines.append(f"  B_max:    {bond.b_max:.2f}")
    lines.append(f"  k_b:      {bond.k_b:.2f}")
    lines.append(f"  t₅₀:      {bond.t50:.1f} months")
    lines.append(f"  Current:  {current:.2f}")
    lines.append(f"  dB/dt:    {rate:.4f}")
    lines.append(f"  Trend:    {trend.value}")

    if trend == BondTrend.DECAYING:
        lines.append("  ⚠️  WARNING: Bond strength is DECAYING!")
    elif trend == BondTrend.STRENGTHENING:
        lines.append("  ✅ Bond strength is strengthening")
    else:
        lines.append("  ➡️  Bond strength is stable")

    lines.append("")
    lines.append("  Strength Chart:")

    traj = bond_trajectory(bond, months=24, step=2)
    for point in traj:
        bar_len = int(point["strength"] / bond.b_max * 20) if bond.b_max > 0 else 0
        bar_len = min(bar_len, 20)
        trend_icon = "↑" if point["trend"] == "strengthening" else ("↓" if point["trend"] == "decaying" else "→")
        lines.append(
            f"  m{point['month']:5.0f} {'█' * bar_len}{'░' * (20 - bar_len)} "
            f"{point['strength']:.2f} {trend_icon}"
        )

    return "\n".join(lines)
