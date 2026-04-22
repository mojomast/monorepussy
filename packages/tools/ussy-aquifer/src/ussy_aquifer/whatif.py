"""
What-If Engine — Simulate infrastructure changes and predict effects.

Supports:
- "Drill a well" — add capacity at a service point
- Add a fracture — new direct path between services
- Remove a confining layer — remove rate limit
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .topology import ServiceLayer, Topology, FlowConnection
from .darcy import analyze_flow, FlowAnalysis, compute_darcy_flux
from .drawdown import compute_cone_of_depression, ConeOfDepression
from .theis import compute_drawdown, compute_time_to_saturation, predict_system


@dataclass
class WhatIfResult:
    """Result of a what-if scenario."""

    scenario: str
    description: str
    original_flow: float  # Total system flow before change
    new_flow: float  # Total system flow after change
    flow_change_pct: float = 0.0
    original_bottlenecks: int = 0
    new_bottlenecks: int = 0
    bottleneck_change: int = 0
    affected_services: List[str] = field(default_factory=list)
    details: Dict[str, float] = field(default_factory=dict)
    modified_topology: Optional[Topology] = None

    def __post_init__(self) -> None:
        if self.original_flow > 0:
            self.flow_change_pct = ((self.new_flow - self.original_flow) / self.original_flow) * 100
        self.bottleneck_change = self.new_bottlenecks - self.original_bottlenecks

    def summary(self) -> str:
        direction = "↑" if self.flow_change_pct >= 0 else "↓"
        lines = [
            f"What-If: {self.scenario}",
            f"{'=' * 50}",
            f"{self.description}",
            "",
            f"System flow: {self.original_flow:.1f} → {self.new_flow:.1f} req/s ({direction}{abs(self.flow_change_pct):.1f}%)",
            f"Bottlenecks: {self.original_bottlenecks} → {self.new_bottlenecks} ({self.bottleneck_change:+d})",
        ]
        if self.affected_services:
            lines.append(f"Affected services: {', '.join(self.affected_services)}")
        if self.details:
            lines.append("\nDetails:")
            for k, v in self.details.items():
                lines.append(f"  {k}: {v:.2f}")
        return "\n".join(lines)


def drill_well(
    topology: Topology,
    service_name: str,
    additional_K: float = 0.0,
    additional_replicas: int = 1,
) -> WhatIfResult:
    """
    "Drill a well" — add capacity at a service point.

    Simulates adding replicas or increasing K at a service.

    Args:
        topology: The system topology
        service_name: Service to add capacity to
        additional_K: Additional hydraulic conductivity to add
        additional_replicas: Number of replicas to add

    Returns:
        WhatIfResult showing impact of the change
    """
    # Analyze current state
    current_analysis = analyze_flow(topology)

    # Create modified topology
    modified = _deep_copy_topology(topology)

    svc = modified.services.get(service_name)
    if svc is None:
        return WhatIfResult(
            scenario="drill_well",
            description=f"Service '{service_name}' not found",
            original_flow=current_analysis.total_system_flow,
            new_flow=current_analysis.total_system_flow,
        )

    # Modify the service
    svc.replicas += additional_replicas
    svc.hydraulic_conductivity += additional_K
    svc.transmissivity = svc.hydraulic_conductivity * svc.replicas
    svc.effective_K = svc.hydraulic_conductivity * svc.replicas

    # Analyze modified state
    new_analysis = analyze_flow(modified)

    # Compute affected services
    affected = []
    for flow in new_analysis.flows:
        if flow.source == service_name or flow.target == service_name:
            affected.append(flow.target if flow.source == service_name else flow.source)

    # Check drawdown reduction
    old_cone = compute_cone_of_depression(topology, service_name, 0.5, 300.0)
    new_cone = compute_cone_of_depression(modified, service_name, 0.5, 300.0)

    details = {
        "old_max_drawdown": old_cone.max_drawdown,
        "new_max_drawdown": new_cone.max_drawdown,
        "drawdown_reduction_pct": 0.0,
    }
    if old_cone.max_drawdown > 0:
        details["drawdown_reduction_pct"] = (
            (old_cone.max_drawdown - new_cone.max_drawdown) / old_cone.max_drawdown * 100
        )

    return WhatIfResult(
        scenario="drill_well",
        description=f"Add {additional_replicas} replica(s) and K+{additional_K:.0f} to {service_name}",
        original_flow=current_analysis.total_system_flow,
        new_flow=new_analysis.total_system_flow,
        original_bottlenecks=len(current_analysis.bottlenecks),
        new_bottlenecks=len(new_analysis.bottlenecks),
        affected_services=list(set(affected)),
        details=details,
        modified_topology=modified,
    )


def add_fracture(
    topology: Topology,
    source: str,
    target: str,
    bandwidth: float = 0.0,
) -> WhatIfResult:
    """
    Add a fracture — new direct path between services.

    This bypasses the normal queue-based flow, creating a "fracture flow"
    path between two services.

    Args:
        topology: The system topology
        source: Source service
        target: Target service
        bandwidth: Max flow rate for the fracture (0 = unlimited)

    Returns:
        WhatIfResult showing impact
    """
    current_analysis = analyze_flow(topology)
    modified = _deep_copy_topology(topology)

    conn = FlowConnection(
        source=source,
        target=target,
        connection_type="fracture",
        bandwidth=bandwidth,
    )
    modified.add_connection(conn)

    new_analysis = analyze_flow(modified)

    return WhatIfResult(
        scenario="add_fracture",
        description=f"Add fracture flow: {source} → {target}",
        original_flow=current_analysis.total_system_flow,
        new_flow=new_analysis.total_system_flow,
        original_bottlenecks=len(current_analysis.bottlenecks),
        new_bottlenecks=len(new_analysis.bottlenecks),
        affected_services=[source, target],
        modified_topology=modified,
    )


def remove_confining_layer(
    topology: Topology,
    service_name: str,
) -> WhatIfResult:
    """
    Remove a confining layer — remove rate limiting at a service.

    Effectively doubles the K at the service (removes the restriction).

    Args:
        topology: The system topology
        service_name: Service to remove rate limit from

    Returns:
        WhatIfResult showing impact
    """
    current_analysis = analyze_flow(topology)
    modified = _deep_copy_topology(topology)

    svc = modified.services.get(service_name)
    if svc is None:
        return WhatIfResult(
            scenario="remove_confining_layer",
            description=f"Service '{service_name}' not found",
            original_flow=current_analysis.total_system_flow,
            new_flow=current_analysis.total_system_flow,
        )

    svc.hydraulic_conductivity *= 2.0
    svc.transmissivity = svc.hydraulic_conductivity * svc.replicas
    svc.effective_K = svc.hydraulic_conductivity * svc.replicas

    new_analysis = analyze_flow(modified)

    affected = [service_name]
    for flow in new_analysis.flows:
        if flow.source == service_name or flow.target == service_name:
            neighbor = flow.target if flow.source == service_name else flow.source
            if neighbor not in affected:
                affected.append(neighbor)

    return WhatIfResult(
        scenario="remove_confining_layer",
        description=f"Remove rate limit at {service_name} (K doubled)",
        original_flow=current_analysis.total_system_flow,
        new_flow=new_analysis.total_system_flow,
        original_bottlenecks=len(current_analysis.bottlenecks),
        new_bottlenecks=len(new_analysis.bottlenecks),
        affected_services=affected,
        modified_topology=modified,
    )


def _deep_copy_topology(topology: Topology) -> Topology:
    """Create a deep copy of a topology."""
    new_topo = Topology(name=topology.name)
    for name, svc in topology.services.items():
        new_svc = ServiceLayer(
            name=svc.name,
            hydraulic_conductivity=svc.hydraulic_conductivity,
            specific_storage=svc.specific_storage,
            queue_depth=svc.queue_depth,
            processing_latency=svc.processing_latency,
            replicas=svc.replicas,
            is_recharge=svc.is_recharge,
            is_discharge=svc.is_discharge,
            grid_x=svc.grid_x,
            grid_y=svc.grid_y,
        )
        new_topo.add_service(new_svc)
    for conn in topology.connections:
        new_conn = FlowConnection(
            source=conn.source,
            target=conn.target,
            connection_type=conn.connection_type,
            bandwidth=conn.bandwidth,
        )
        new_topo.add_connection(new_conn)
    return new_topo
