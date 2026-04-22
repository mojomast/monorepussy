"""
Drawdown — Cone of depression model for cascading failure analysis.

A "cone of depression" models how a single point of degradation creates
a spatial cone that propagates and attenuates through the system, accurately
modeling partial degradation that event-chain models miss.

When a service slows down (its K decreases), it creates a "drawdown" in the
pressure field that propagates outward like a cone. The further away a service
is from the degraded service, the less it's affected — but it IS affected.

This is the key differentiator from cyclone (which uses vorticity/turbulence).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .topology import ServiceLayer, Topology
from .theis import compute_drawdown, well_function


@dataclass
class DrawdownPoint:
    """A single point in the cone of depression."""

    service_name: str
    distance: float  # Graph distance from the degraded service
    drawdown: float  # Head loss at this point
    original_head: float  # Original hydraulic head
    new_head: float = 0.0  # Head after drawdown
    impact_percent: float = 0.0  # % degradation

    def __post_init__(self) -> None:
        self.new_head = max(0.0, self.original_head - self.drawdown)
        if self.original_head > 0:
            self.impact_percent = (self.drawdown / self.original_head) * 100
        else:
            self.impact_percent = 0.0


@dataclass
class ConeOfDepression:
    """Complete cone of depression from a degraded service."""

    epicenter: str  # The degraded service
    degradation_factor: float  # How much K was reduced (e.g., 0.5 = 50% reduction)
    Q: float  # Effective pumping rate (additional load from degradation)
    T: float  # Transmissivity at epicenter
    S: float  # Storage coefficient at epicenter
    time_seconds: float  # Time since degradation
    points: List[DrawdownPoint] = field(default_factory=list)
    affected_services: List[str] = field(default_factory=list)
    max_drawdown: float = 0.0

    def summary(self) -> str:
        lines = [
            f"Cone of Depression: {self.epicenter}",
            f"{'=' * 50}",
            f"Degradation: {self.degradation_factor:.0%} capacity loss",
            f"Time since degradation: {self.time_seconds:.0f}s",
            f"Max drawdown: {self.max_drawdown:.3f}",
            f"Affected services: {len(self.affected_services)}",
            "",
            "Impact by distance:",
        ]
        for pt in sorted(self.points, key=lambda p: p.distance):
            marker = " ⚠" if pt.impact_percent > 10 else ""
            lines.append(
                f"  {pt.service_name} (d={pt.distance:.1f}): "
                f"drawdown={pt.drawdown:.3f}, "
                f"impact={pt.impact_percent:.1f}%{marker}"
            )
        return "\n".join(lines)


def compute_graph_distance(topology: Topology, source: str, target: str) -> float:
    """
    Compute graph distance between two services using BFS.

    Returns:
        Distance in hops (1.0 per hop), or float('inf') if not connected
    """
    if source == target:
        return 0.0

    visited = {source}
    queue = [(source, 0.0)]
    idx = 0

    while idx < len(queue):
        current, dist = queue[idx]
        idx += 1

        for neighbor in topology.get_downstream(current):
            if neighbor == target:
                return dist + 1.0
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1.0))

        for neighbor in topology.get_upstream(current):
            if neighbor == target:
                return dist + 1.0
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1.0))

    return float("inf")


def compute_cone_of_depression(
    topology: Topology,
    service_name: str,
    degradation_factor: float = 0.5,
    time_seconds: float = 300.0,
) -> ConeOfDepression:
    """
    Compute the cone of depression from a degraded service.

    When a service loses capacity (K reduced), it effectively "pumps" load
    onto the system — the excess requests that can't be processed accumulate
    as pressure. This creates a cone of depression in the head field.

    Args:
        topology: The system topology
        service_name: The degraded service
        degradation_factor: Fraction of capacity lost (0.5 = 50% lost)
        time_seconds: Time since the degradation occurred

    Returns:
        ConeOfDepression with impact on all services
    """
    svc = topology.services.get(service_name)
    if svc is None:
        return ConeOfDepression(
            epicenter=service_name,
            degradation_factor=degradation_factor,
            Q=0, T=0, S=0,
            time_seconds=time_seconds,
        )

    # Effective additional "pumping" from the degradation
    Q = svc.effective_K * degradation_factor
    T = svc.transmissivity
    S = svc.specific_storage * 1000  # Scale for reasonable behavior

    cone = ConeOfDepression(
        epicenter=service_name,
        degradation_factor=degradation_factor,
        Q=Q,
        T=T,
        S=S,
        time_seconds=time_seconds,
    )

    max_dd = 0.0

    for name, other_svc in topology.services.items():
        dist = compute_graph_distance(topology, service_name, name)
        if dist == float("inf"):
            continue

        r = max(0.001, dist)
        dd = compute_drawdown(Q, T, S, r, time_seconds)

        point = DrawdownPoint(
            service_name=name,
            distance=dist,
            drawdown=dd,
            original_head=other_svc.hydraulic_head,
        )
        cone.points.append(point)

        if dd > 0.01 * svc.hydraulic_head:  # More than 1% of original head
            cone.affected_services.append(name)

        if dd > max_dd:
            max_dd = dd

    cone.max_drawdown = max_dd
    return cone


def predict_cascade(
    topology: Topology,
    degraded_service: str,
    degradation_factor: float = 0.5,
    time_seconds: float = 300.0,
    cascade_threshold: float = 0.3,
) -> List[str]:
    """
    Predict which services will cascade-fail due to a degradation.

    A service cascades when its drawdown exceeds the cascade_threshold
    fraction of its original head.

    Args:
        topology: The system topology
        degraded_service: The initially degraded service
        degradation_factor: How much capacity was lost
        time_seconds: Time since degradation
        cascade_threshold: Fraction of head loss that triggers cascade

    Returns:
        List of service names that will cascade, ordered by impact
    """
    cone = compute_cone_of_depression(
        topology, degraded_service, degradation_factor, time_seconds
    )

    cascading = []
    for pt in cone.points:
        if pt.service_name == degraded_service:
            continue
        if pt.original_head > 0 and pt.drawdown / pt.original_head > cascade_threshold:
            cascading.append((pt.service_name, pt.impact_percent))

    cascading.sort(key=lambda x: -x[1])
    return [name for name, _ in cascading]
