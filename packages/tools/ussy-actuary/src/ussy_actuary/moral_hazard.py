"""Moral Hazard — Security Incentive Quantification."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class MoralHazardResult:
    """Result of moral hazard analysis."""
    base_loss: float            # L - potential loss from breach
    base_probability: float     # p0 - breach probability without coverage
    effort_cost: float          # c - cost per unit of security effort
    coverage_fraction: float    # alpha - insurance/SLA coverage fraction
    effort_elasticity: float    # eta - effort elasticity of breach probability

    optimal_effort_uncovered: float    # e* = p0*L/(2c)
    optimal_effort_covered: float      # e_hat = p0*(1-alpha)*L/(2c)
    effort_reduction: float            # delta_e/e* = alpha
    effort_reduction_pct: float        # as percentage

    welfare_loss: float         # WL = alpha^2 * p0^2 * L^2 / (8c)
    adverse_selection_ratio: float  # ASR = E[risk|covered] / E[risk|population]

    optimal_coinsurance: float  # alpha* = 1 / (1 + p0*L/(2c) * eta)
    covered_breach_probability: float  # p(e_hat)


def compute_moral_hazard(
    base_loss: float,
    base_probability: float,
    effort_cost: float,
    coverage_fraction: float = 1.0,
    effort_elasticity: float = 0.5,
    adverse_selection_ratio: Optional[float] = None,
) -> MoralHazardResult:
    """Compute moral hazard from insurance/SLA coverage.

    Models how security effort decreases when losses are covered,
    and computes the welfare loss and optimal coinsurance.

    Args:
        base_loss: Potential loss from a security breach (L).
        base_probability: Breach probability without coverage (p0).
        effort_cost: Cost per unit of security effort (c).
        coverage_fraction: Fraction of loss covered by SLA/insurance (alpha, 0-1).
        effort_elasticity: How much breach probability responds to effort (eta).
        adverse_selection_ratio: Ratio of covered risk to population risk.
            Defaults to 1 + coverage_fraction * 0.1 (simple model).

    Returns:
        MoralHazardResult with effort reduction and optimal design.
    """
    # Uncovered optimal effort: e* = p0 * L / (2c)
    if effort_cost > 0:
        e_star = base_probability * base_loss / (2 * effort_cost)
    else:
        e_star = 0.0

    # Covered optimal effort: e_hat = p0 * (1 - alpha) * L / (2c)
    if effort_cost > 0:
        e_hat = base_probability * (1 - coverage_fraction) * base_loss / (2 * effort_cost)
    else:
        e_hat = 0.0

    # Effort reduction: delta_e/e* = alpha
    if e_star > 0:
        effort_reduction = coverage_fraction
        effort_reduction_pct = coverage_fraction * 100
    else:
        effort_reduction = 0.0
        effort_reduction_pct = 0.0

    # Welfare loss: WL = alpha^2 * p0^2 * L^2 / (8c)
    if effort_cost > 0:
        welfare_loss = (coverage_fraction ** 2 * base_probability ** 2
                       * base_loss ** 2 / (8 * effort_cost))
    else:
        welfare_loss = 0.0

    # Adverse selection ratio
    if adverse_selection_ratio is not None:
        asr = adverse_selection_ratio
    else:
        # Simple model: ASR increases with coverage fraction
        asr = 1.0 + coverage_fraction * 0.1

    # Optimal coinsurance: alpha* = 1 / (1 + p0*L/(2c) * eta)
    if e_star > 0 and effort_elasticity > 0:
        optimal_coinsurance = 1.0 / (1.0 + e_star * effort_elasticity)
    else:
        optimal_coinsurance = 1.0

    # Breach probability under covered effort
    # p(e) = p0 - eta * e (linear model)
    p_covered = max(0.0, base_probability - effort_elasticity * e_hat)

    return MoralHazardResult(
        base_loss=base_loss,
        base_probability=base_probability,
        effort_cost=effort_cost,
        coverage_fraction=coverage_fraction,
        effort_elasticity=effort_elasticity,
        optimal_effort_uncovered=e_star,
        optimal_effort_covered=e_hat,
        effort_reduction=effort_reduction,
        effort_reduction_pct=effort_reduction_pct,
        welfare_loss=welfare_loss,
        adverse_selection_ratio=asr,
        optimal_coinsurance=optimal_coinsurance,
        covered_breach_probability=p_covered,
    )


def analyze_sla(
    vendor_coverage: float,
    sla_penalty: float,
    base_loss: float,
    base_probability: float,
    effort_cost: float,
    effort_elasticity: float = 0.5,
) -> dict:
    """Analyze a vendor SLA for moral hazard effects.

    Args:
        vendor_coverage: Fraction of loss covered by SLA.
        sla_penalty: Penalty for SLA violation (reduces effective coverage).
        base_loss: Potential loss from a breach.
        base_probability: Breach probability without coverage.
        effort_cost: Cost per unit of security effort.
        effort_elasticity: Effort elasticity of breach probability.

    Returns:
        Dictionary with moral hazard analysis and SLA-specific metrics.
    """
    effective_coverage = max(0.0, vendor_coverage - sla_penalty / base_loss) if base_loss > 0 else 0.0

    result = compute_moral_hazard(
        base_loss=base_loss,
        base_probability=base_probability,
        effort_cost=effort_cost,
        coverage_fraction=effective_coverage,
        effort_elasticity=effort_elasticity,
    )

    return {
        "vendor_coverage": vendor_coverage,
        "sla_penalty": sla_penalty,
        "effective_coverage": effective_coverage,
        "effort_reduction_pct": result.effort_reduction_pct,
        "welfare_loss": result.welfare_loss,
        "optimal_coinsurance": result.optimal_coinsurance,
        "breach_probability_change": result.covered_breach_probability - base_probability,
        "recommendation": _generate_sla_recommendation(result),
    }


def _generate_sla_recommendation(result: MoralHazardResult) -> str:
    """Generate a human-readable recommendation based on moral hazard analysis."""
    if result.effort_reduction_pct < 10:
        return "Low moral hazard — coverage has minimal impact on security effort."
    elif result.effort_reduction_pct < 30:
        return "Moderate moral hazard — consider increasing coinsurance or adding audit requirements."
    elif result.effort_reduction_pct < 60:
        return (f"Significant moral hazard — effort drops {result.effort_reduction_pct:.0f}%. "
                f"Reduce coverage to {result.optimal_coinsurance:.0%} (optimal coinsurance) "
                f"or implement mandatory security controls.")
    else:
        return (f"Severe moral hazard — effort drops {result.effort_reduction_pct:.0f}%. "
                f"URGENT: Restructure SLA. Optimal coinsurance is {result.optimal_coinsurance:.0%}. "
                f"Welfare loss: {result.welfare_loss:,.0f}.")


def format_moral_hazard(result: MoralHazardResult) -> str:
    """Format moral hazard result as a readable string."""
    lines = [
        "Moral Hazard Analysis",
        f"  Base loss (L):           {result.base_loss:,.0f}",
        f"  Base probability (p0):   {result.base_probability:.4f}",
        f"  Effort cost (c):         {result.effort_cost:.4f}",
        f"  Coverage fraction (α):   {result.coverage_fraction:.2%}",
        f"  Effort elasticity (η):   {result.effort_elasticity:.4f}",
        "",
        f"  Optimal effort (uncovered): {result.optimal_effort_uncovered:.4f}",
        f"  Optimal effort (covered):   {result.optimal_effort_covered:.4f}",
        f"  Effort reduction:           {result.effort_reduction_pct:.1f}%",
        "",
        f"  Welfare loss:            {result.welfare_loss:,.0f}",
        f"  Adverse selection ratio: {result.adverse_selection_ratio:.4f}",
        f"  Optimal coinsurance:     {result.optimal_coinsurance:.2%}",
        f"  Covered breach prob:     {result.covered_breach_probability:.4f}",
    ]
    return "\n".join(lines)
