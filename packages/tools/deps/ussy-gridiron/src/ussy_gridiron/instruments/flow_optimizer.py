"""Instrument 3: Flow Optimizer — Optimal Dependency Dispatch (OPF).

DC-OPF analogy:
  min Σᵢ riskᵢ·wᵢ
  s.t. A·w = d (import resolution)
       wᵢ ∈ [w_min, w_max]
       |couplingᵢⱼ| ≤ coupling_max
       Σwᵢ = Σdemand_d

Since we can't use scipy/numpy, we implement a simplified greedy
optimization that minimizes total risk while satisfying import constraints.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from ussy_gridiron.graph import DependencyGraph
from ussy_gridiron.models import (
    DispatchResult,
    DependencyEdge,
    OPFReport,
    PackageInfo,
)


class FlowOptimizer:
    """Optimal dependency dispatch using OPF analogy."""

    DEFAULT_COUPLING_MAX = 0.8
    DEFAULT_W_MIN = 0.0
    DEFAULT_W_MAX = 1.0

    def __init__(self, graph: DependencyGraph) -> None:
        self.graph = graph

    def optimize(self, coupling_max: float = DEFAULT_COUPLING_MAX) -> OPFReport:
        """Find minimum-risk dependency dispatch.

        Uses a greedy approach since we can't use LP solvers:
        1. Start with all packages at minimum weight
        2. Incrementally increase weights of low-risk packages to satisfy demand
        3. Penalize overcoupled pairs
        """
        dispatch: List[DispatchResult] = []
        overcoupled: List[Tuple[str, str]] = []
        congested: List[str] = []
        recommendations: List[str] = []

        # Calculate demand: each direct dependency demands 1.0 unit
        direct_packages = self.graph.direct_packages()
        total_demand = len(direct_packages)

        if total_demand == 0:
            # All packages are indirect; treat all as demand
            for pkg_name in self.graph.packages:
                direct_packages.append(pkg_name)
            total_demand = len(direct_packages)

        # Sort packages by risk (ascending) for greedy allocation
        sorted_packages = sorted(
            self.graph.packages.values(),
            key=lambda p: p.risk_weight,
        )

        # Assign optimal weights: lower risk → higher weight
        total_risk = 0.0
        remaining_demand = float(total_demand)

        for pkg in sorted_packages:
            if remaining_demand > 0:
                weight = min(1.0, remaining_demand)
                remaining_demand -= weight
            else:
                weight = 0.0

            risk_contrib = pkg.risk_weight * weight
            total_risk += risk_contrib

            is_congested = pkg.risk_weight > 1.5
            if is_congested:
                congested.append(pkg.name)

            dispatch.append(DispatchResult(
                package=pkg.name,
                optimal_weight=weight,
                risk_contribution=risk_contrib,
                is_congested=is_congested,
            ))

        # Check overcoupled pairs
        for edge in self.graph.edges:
            if edge.coupling_strength > coupling_max:
                overcoupled.append((edge.source, edge.target))

        # Generate redispatch recommendations for congested packages
        for pkg_name in congested:
            pkg = self.graph.packages.get(pkg_name)
            if pkg and pkg.backup_packages:
                alternatives = [b for b in pkg.backup_packages if b in self.graph.packages]
                if alternatives:
                    recommendations.append(
                        f"Replace {pkg_name} (risk={pkg.risk_weight:.1f}) "
                        f"with lower-risk alternative: {', '.join(alternatives)}"
                    )
                else:
                    recommendations.append(
                        f"Reduce coupling to {pkg_name} (risk={pkg.risk_weight:.1f}) "
                        f"— no alternatives currently available"
                    )
            else:
                recommendations.append(
                    f"Add backup for {pkg_name} to reduce risk concentration"
                )

        # Recommend decoupling for overcoupled pairs
        for src, tgt in overcoupled:
            coupling = self.graph.get_coupling(src, tgt)
            recommendations.append(
                f"Reduce coupling {src}→{tgt} (coupling={coupling:.2f} > max={coupling_max:.2f})"
            )

        return OPFReport(
            total_risk=total_risk,
            dispatch=dispatch,
            overcoupled_pairs=overcoupled,
            congestion_bottlenecks=congested,
            redispatch_recommendations=recommendations,
        )

    def compute_line_flows(self) -> Dict[Tuple[str, str], float]:
        """Compute dependency "line flows" — weighted coupling through edges.

        Line flow = coupling_strength × max(source_weight, target_weight)
        """
        flows: Dict[Tuple[str, str], float] = {}
        dispatch_map = {d.package: d.optimal_weight for d in self.optimize().dispatch}

        for edge in self.graph.edges:
            src_w = dispatch_map.get(edge.source, 0.0)
            tgt_w = dispatch_map.get(edge.target, 0.0)
            flow = edge.coupling_strength * max(src_w, tgt_w)
            flows[(edge.source, edge.target)] = flow

        return flows
