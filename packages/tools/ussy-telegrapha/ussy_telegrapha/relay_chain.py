"""Relay Chain Reliability — Service Mesh Hop Budget Analysis.

Models pipeline reliability as a series relay chain:
    R_total = prod(R_i)
    R_per_hop = SLA^(1/N)  (required per-hop reliability for SLA compliance)
"""

from __future__ import annotations

from typing import Any

from .models import Hop, RelayChainResult, Route


def compute_required_per_hop(sla: float, hop_count: int) -> float:
    """Compute required per-hop reliability for SLA compliance.

    R_per_hop = SLA^(1/N)
    """
    if hop_count <= 0:
        return sla
    return sla ** (1.0 / hop_count)


def compute_series_reliability(route: Route) -> float:
    """Compute end-to-end reliability for a series chain.

    R_total = prod(R_i)
    """
    reliability = 1.0
    for hop in route.hops:
        reliability *= hop.reliability
    return reliability


def find_weakest_link(route: Route) -> Hop | None:
    """Find the hop with the lowest reliability."""
    if not route.hops:
        return None
    return min(route.hops, key=lambda h: h.reliability)


def compute_parallel_reliability(reliabilities: list[float]) -> float:
    """Compute reliability of parallel paths.

    R_parallel = 1 - prod(1 - R_i)
    """
    failure_product = 1.0
    for r in reliabilities:
        failure_product *= 1.0 - r
    return 1.0 - failure_product


def analyze_relay_chain(
    route: Route,
    target_sla: float = 0.999,
    alternate_path_reliability: float | None = None,
) -> RelayChainResult:
    """Perform full relay chain reliability analysis.

    Args:
        route: Pipeline route with hops and reliability values.
        target_sla: Target end-to-end SLA (e.g., 0.999 for 99.9%).
        alternate_path_reliability: If provided, compute alternate path reliability.

    Returns:
        RelayChainResult with analysis and recommendations.
    """
    required_per_hop = compute_required_per_hop(target_sla, route.hop_count)
    actual_reliability = compute_series_reliability(route)
    weakest = find_weakest_link(route)
    meets_sla = actual_reliability >= target_sla

    recommendations: list[str] = []

    if not meets_sla:
        if weakest:
            recommendations.append(
                f"Weakest link: {weakest.name} "
                f"(reliability: {weakest.reliability:.4%}, "
                f"budget: {required_per_hop:.4%})"
            )
            recommendations.append(
                f"Add circuit breaker + retry at hop "
                f"'{weakest.name}' (relay station)"
            )

        if alternate_path_reliability is not None:
            alt_meets = alternate_path_reliability >= target_sla
            status = "meets SLA" if alt_meets else "below SLA"
            recommendations.append(
                f"Parallel path via alternate route: "
                f"R_alt = {alternate_path_reliability:.4%} ({status})"
            )

    # Identify hops below per-hop budget
    for hop in route.hops:
        if hop.reliability < required_per_hop:
            recommendations.append(
                f"Hop '{hop.name}' below per-hop budget: "
                f"{hop.reliability:.4%} < {required_per_hop:.4%}"
            )

    return RelayChainResult(
        route=route,
        target_sla=target_sla,
        required_per_hop=required_per_hop,
        actual_reliability=actual_reliability,
        weakest_link=weakest.name if weakest else "",
        meets_sla=meets_sla,
        recommendations=recommendations,
    )


def format_relay_chain_report(result: RelayChainResult) -> str:
    """Format relay chain result as a human-readable report."""
    lines: list[str] = []

    route = result.route
    lines.append(f"Route: {route.name} ({route.hop_count} hops)")
    lines.append(f"Required per-hop reliability: {result.required_per_hop:.4%}")
    lines.append("")

    lines.append("Actual reliability:")
    for hop in route.hops:
        status = "✅" if hop.reliability >= result.required_per_hop else "❌"
        lines.append(
            f"  {hop.name}: {hop.reliability:.4%} {status}"
            + (f" (below {result.required_per_hop:.4%} budget)" if hop.reliability < result.required_per_hop else "")
        )

    lines.append("")
    sla_status = "meets SLA" if result.meets_sla else "below SLA"
    lines.append(
        f"End-to-end: {result.actual_reliability:.4%} ({sla_status})"
    )

    if not result.meets_sla:
        lines.append(f"  → Weakest link: {result.weakest_link}")

    for r in result.recommendations:
        lines.append(f"  → {r}")

    return "\n".join(lines)


def relay_chain_to_dict(result: RelayChainResult) -> dict[str, Any]:
    """Convert relay chain result to a JSON-serializable dictionary."""
    return {
        "route": result.route.name,
        "hop_count": result.route.hop_count,
        "target_sla": result.target_sla,
        "required_per_hop": round(result.required_per_hop, 8),
        "actual_reliability": round(result.actual_reliability, 8),
        "meets_sla": result.meets_sla,
        "weakest_link": result.weakest_link,
        "recommendations": result.recommendations,
        "hops": [
            {
                "name": h.name,
                "reliability": h.reliability,
                "meets_budget": h.reliability >= result.required_per_hop,
            }
            for h in result.route.hops
        ],
    }
