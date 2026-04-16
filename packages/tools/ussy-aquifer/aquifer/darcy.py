"""
Darcy Engine — Core computation engine using Darcy's Law.

Darcy's Law: q = -K * (dh/dl)
  q = flow rate (data throughput, req/s)
  K = hydraulic conductivity (service throughput capacity, req/s)
  dh/dl = hydraulic gradient (pressure difference between services)

This module computes:
- Inter-service flow rates
- Bottleneck detection (where q < expected)
- Pressure gradients across the system
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .topology import ServiceLayer, Topology


@dataclass
class FlowResult:
    """Result of a Darcy flow computation between two services."""

    source: str
    target: str
    flow_rate: float  # q — actual throughput (req/s)
    hydraulic_gradient: float  # dh/dl
    conductivity: float  # K of target
    expected_flow: float  # What flow should be based on source head
    is_bottleneck: bool = False
    bottleneck_severity: float = 0.0  # 0-1, how severe

    def __post_init__(self) -> None:
        if self.expected_flow > 0:
            ratio = self.flow_rate / self.expected_flow
            if ratio < 0.8:
                self.is_bottleneck = True
                self.bottleneck_severity = min(1.0, 1.0 - ratio)


@dataclass
class FlowAnalysis:
    """Complete flow analysis of a topology."""

    flows: List[FlowResult] = field(default_factory=list)
    bottlenecks: List[FlowResult] = field(default_factory=list)
    max_pressure_service: str = ""
    max_pressure_head: float = 0.0
    total_system_flow: float = 0.0
    pressure_gradients: Dict[str, float] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"Flow Analysis Summary",
            f"=====================",
            f"Total system flow: {self.total_system_flow:.1f} req/s",
            f"Max pressure at: {self.max_pressure_service} (h={self.max_pressure_head:.2f})",
            f"Bottlenecks found: {len(self.bottlenecks)}",
        ]
        if self.bottlenecks:
            lines.append("")
            lines.append("Bottleneck Details:")
            for b in self.bottlenecks:
                lines.append(
                    f"  {b.source} → {b.target}: "
                    f"q={b.flow_rate:.1f} req/s "
                    f"(expected {b.expected_flow:.1f}), "
                    f"severity={b.bottleneck_severity:.0%}"
                )
        lines.append("")
        lines.append("Pressure Gradients:")
        for svc, grad in sorted(self.pressure_gradients.items(), key=lambda x: -abs(x[1])):
            lines.append(f"  {svc}: dh/dl = {grad:.4f}")
        return "\n".join(lines)


def compute_darcy_flux(
    K: float,
    head_source: float,
    head_target: float,
    distance: float = 1.0,
) -> float:
    """
    Compute Darcy flux: q = -K * (dh/dl)

    Args:
        K: Hydraulic conductivity of the target (receiving) medium
        head_source: Hydraulic head at source
        head_target: Hydraulic head at target
        distance: Distance between source and target (grid units)

    Returns:
        Flow rate q (req/s). Positive = flow from source to target.
    """
    if distance <= 0:
        return 0.0
    gradient = (head_source - head_target) / distance
    q = K * gradient  # Positive when source has higher head
    return max(0.0, q)  # Flow only from high to low pressure


def compute_hydraulic_gradient(
    head_source: float,
    head_target: float,
    distance: float = 1.0,
) -> float:
    """Compute hydraulic gradient dh/dl."""
    if distance <= 0:
        return 0.0
    return (head_source - head_target) / distance


def analyze_flow(topology: Topology) -> FlowAnalysis:
    """
    Perform complete Darcy flow analysis on a topology.

    For each connection, computes the Darcy flux and identifies bottlenecks
    where flow is restricted relative to expected throughput.
    """
    analysis = FlowAnalysis()

    # Find max pressure service
    max_head = 0.0
    max_svc = ""
    for name, svc in topology.services.items():
        if svc.hydraulic_head > max_head:
            max_head = svc.hydraulic_head
            max_svc = name
    analysis.max_pressure_service = max_svc
    analysis.max_pressure_head = max_head

    # Compute flow for each connection
    total_flow = 0.0
    for conn in topology.connections:
        src = topology.services.get(conn.source)
        tgt = topology.services.get(conn.target)
        if src is None or tgt is None:
            continue

        # Compute distance on grid
        dx = abs(src.grid_x - tgt.grid_x)
        dy = abs(src.grid_y - tgt.grid_y)
        distance = max(1.0, (dx**2 + dy**2) ** 0.5)

        # Effective conductivity is limited by the weaker layer
        K_eff = min(src.effective_K, tgt.effective_K)

        # If connection has bandwidth limit, cap K
        if conn.bandwidth > 0:
            K_eff = min(K_eff, conn.bandwidth)

        # Darcy flux
        q = compute_darcy_flux(K_eff, src.hydraulic_head, tgt.hydraulic_head, distance)

        # Expected flow: what source could push if unimpeded
        expected = compute_darcy_flux(
            src.effective_K, src.hydraulic_head, 0.0, distance
        )

        # Gradient
        gradient = compute_hydraulic_gradient(
            src.hydraulic_head, tgt.hydraulic_head, distance
        )

        result = FlowResult(
            source=conn.source,
            target=conn.target,
            flow_rate=q,
            hydraulic_gradient=gradient,
            conductivity=K_eff,
            expected_flow=expected,
        )
        analysis.flows.append(result)
        total_flow += q

        if result.is_bottleneck:
            analysis.bottlenecks.append(result)

    analysis.total_system_flow = total_flow

    # Compute pressure gradients per service
    for name, svc in topology.services.items():
        downstream = topology.get_downstream(name)
        upstream = topology.get_upstream(name)
        gradients = []
        for ds_name in downstream:
            ds = topology.services.get(ds_name)
            if ds:
                dx = abs(svc.grid_x - ds.grid_x)
                dy = abs(svc.grid_y - ds.grid_y)
                dist = max(1.0, (dx**2 + dy**2) ** 0.5)
                gradients.append(
                    compute_hydraulic_gradient(svc.hydraulic_head, ds.hydraulic_head, dist)
                )
        for us_name in upstream:
            us = topology.services.get(us_name)
            if us:
                dx = abs(us.grid_x - svc.grid_x)
                dy = abs(us.grid_y - svc.grid_y)
                dist = max(1.0, (dx**2 + dy**2) ** 0.5)
                gradients.append(
                    compute_hydraulic_gradient(us.hydraulic_head, svc.hydraulic_head, dist)
                )
        if gradients:
            analysis.pressure_gradients[name] = sum(gradients) / len(gradients)
        else:
            analysis.pressure_gradients[name] = 0.0

    return analysis


def find_bottlenecks(topology: Topology, threshold: float = 0.8) -> List[FlowResult]:
    """
    Find bottlenecks where flow_rate / expected_flow < threshold.

    Args:
        topology: The system topology
        threshold: Ratio below which a connection is considered bottlenecked

    Returns:
        List of FlowResult objects for bottlenecked connections
    """
    analysis = analyze_flow(topology)
    return [
        f for f in analysis.flows
        if f.expected_flow > 0 and (f.flow_rate / f.expected_flow) < threshold
    ]


def compute_conductivity_map(topology: Topology) -> Dict[str, float]:
    """
    Map K-values (throughput capacity) across the system.

    Returns a dict mapping service name to effective hydraulic conductivity.
    """
    return {name: svc.effective_K for name, svc in topology.services.items()}
