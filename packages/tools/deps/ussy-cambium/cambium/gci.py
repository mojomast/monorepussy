"""GCI — Graft Compatibility Index unified metric."""

from __future__ import annotations

from cambium.models import (
    AlignmentScore,
    BondStrength,
    CallusDynamics,
    CompatibilityScore,
    DependencyPair,
    DriftDebt,
    GCISnapshot,
)


def compute_gci(
    compatibility: CompatibilityScore,
    alignment: AlignmentScore,
    callus: CallusDynamics,
    drift: DriftDebt,
    bond: BondStrength,
    system_vigor: float = 1.0,
    time_months: float = 0.0,
) -> GCISnapshot:
    """Compute the Graft Compatibility Index at a given time.

    GCI(a,b,t) = C(a,b) · A_interface · Q_adapter(t) · (1-D(t)/D_critical) · B(t)/B_max · V_system
    """
    comp_score = compatibility.composite
    align_score = alignment.composite
    adapter_q = callus.adapter_quality
    drift_fraction = drift.drift_budget_consumed(time_months)
    bond_fraction = bond.strength_at(time_months) / bond.b_max if bond.b_max > 0 else 0.0

    return GCISnapshot(
        compatibility=comp_score,
        alignment=align_score,
        adapter_quality=adapter_q,
        drift_fraction=drift_fraction,
        bond_fraction=bond_fraction,
        system_vigor=system_vigor,
    )


def compute_gci_simple(
    compatibility: float = 1.0,
    alignment: float = 1.0,
    adapter_quality: float = 1.0,
    drift_fraction: float = 0.0,
    bond_fraction: float = 1.0,
    system_vigor: float = 1.0,
) -> GCISnapshot:
    """Compute GCI from raw component scores directly."""
    return GCISnapshot(
        compatibility=compatibility,
        alignment=alignment,
        adapter_quality=adapter_quality,
        drift_fraction=drift_fraction,
        bond_fraction=bond_fraction,
        system_vigor=system_vigor,
    )


def gci_trajectory(
    compatibility: CompatibilityScore,
    alignment: AlignmentScore,
    callus: CallusDynamics,
    drift: DriftDebt,
    bond: BondStrength,
    system_vigor: float = 1.0,
    months: int = 24,
    step: float = 1.0,
) -> list[GCISnapshot]:
    """Generate GCI trajectory over time."""
    snapshots: list[GCISnapshot] = []
    t = 0.0
    while t <= months:
        snapshot = compute_gci(
            compatibility, alignment, callus, drift, bond, system_vigor, t
        )
        snapshots.append(snapshot)
        t += step
    return snapshots


def format_gci_report(snapshot: GCISnapshot) -> str:
    """Format a GCI report."""
    lines: list[str] = []
    lines.append("Graft Compatibility Index (GCI)")
    lines.append("═" * 40)

    gci = snapshot.gci
    lines.append(f"  GCI:  {gci:.4f}")

    # Classification
    if gci >= 0.8:
        status = "🟢 HEALTHY — strong graft union"
    elif gci >= 0.5:
        status = "🟡 PARTIAL — some incompatibility"
    elif gci >= 0.2:
        status = "🟠 WEAK — significant issues"
    else:
        status = "🔴 CRITICAL — graft failure likely"
    lines.append(f"  Status: {status}")

    lines.append("")
    lines.append("  Component Breakdown:")

    components = [
        ("Compatibility (C)", snapshot.compatibility),
        ("Alignment (A)", snapshot.alignment),
        ("Adapter Quality (Q)", snapshot.adapter_quality),
        ("Drift Reserve (1-D/D_c)", max(0.0, 1.0 - snapshot.drift_fraction)),
        ("Bond Fraction (B/B_max)", snapshot.bond_fraction),
        ("System Vigor (V)", snapshot.system_vigor),
    ]

    for name, value in components:
        bar_len = int(value * 20) if value > 0 else 0
        bar = "█" * bar_len + "░" * (20 - bar_len)
        lines.append(f"    {name:<24} {bar} {value:.2f}")

    lines.append("")
    lines.append("  Key property: GCI = 0 if ANY component is 0")
    lines.append("  (One failed dimension kills the integration, like a graft)")

    return "\n".join(lines)
