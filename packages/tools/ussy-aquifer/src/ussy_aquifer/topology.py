"""
Topology module — Service topology parsing and hydrogeological mapping.

Maps distributed system services to geological layers with properties:
- Hydraulic conductivity K (throughput capacity req/s)
- Specific storage Ss (queue persistence)
- Transmissivity T (cluster total throughput)
- Hydraulic head h (data pressure = queue_depth × latency)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ServiceLayer:
    """A service mapped to a geological layer."""

    name: str
    hydraulic_conductivity: float  # K — throughput capacity (req/s)
    specific_storage: float = 0.01  # Ss — queue persistence
    queue_depth: int = 0  # Current queue depth
    processing_latency: float = 0.0  # Seconds per request
    replicas: int = 1
    is_recharge: bool = False  # Data ingestion endpoint
    is_discharge: bool = False  # Data sink
    grid_x: int = 0  # Position on finite-difference grid
    grid_y: int = 0
    # Computed fields (set in __post_init__)
    transmissivity: float = 0.0
    hydraulic_head: float = 0.0
    effective_K: float = 0.0

    def __post_init__(self) -> None:
        self.transmissivity = self.hydraulic_conductivity * self.replicas
        self.hydraulic_head = self.queue_depth * self.processing_latency
        self.effective_K = self.hydraulic_conductivity * self.replicas

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "hydraulic_conductivity": self.hydraulic_conductivity,
            "specific_storage": self.specific_storage,
            "queue_depth": self.queue_depth,
            "processing_latency": self.processing_latency,
            "replicas": self.replicas,
            "is_recharge": self.is_recharge,
            "is_discharge": self.is_discharge,
            "grid_x": self.grid_x,
            "grid_y": self.grid_y,
        }


@dataclass
class FlowConnection:
    """A flow path between two services (fracture or porous flow)."""

    source: str
    target: str
    connection_type: str = "porous"  # "porous" (via queue) or "fracture" (direct call)
    bandwidth: float = 0.0  # Max flow rate (0 = unlimited by connection)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "connection_type": self.connection_type,
            "bandwidth": self.bandwidth,
        }


@dataclass
class Topology:
    """Complete system topology — the geological formation."""

    name: str = "default"
    services: Dict[str, ServiceLayer] = field(default_factory=dict)
    connections: List[FlowConnection] = field(default_factory=list)
    # Computed
    grid_width: int = 0
    grid_height: int = 0

    def add_service(self, service: ServiceLayer) -> None:
        self.services[service.name] = service
        self._update_grid_size()

    def add_connection(self, conn: FlowConnection) -> None:
        self.connections.append(conn)

    def _update_grid_size(self) -> None:
        if not self.services:
            self.grid_width = 0
            self.grid_height = 0
            return
        max_x = max(s.grid_x for s in self.services.values())
        max_y = max(s.grid_y for s in self.services.values())
        self.grid_width = max_x + 1
        self.grid_height = max_y + 1

    def get_downstream(self, service_name: str) -> List[str]:
        """Get services downstream from the given service."""
        return [c.target for c in self.connections if c.source == service_name]

    def get_upstream(self, service_name: str) -> List[str]:
        """Get services upstream from the given service."""
        return [c.source for c in self.connections if c.target == service_name]

    def get_connection(self, source: str, target: str) -> Optional[FlowConnection]:
        for c in self.connections:
            if c.source == source and c.target == target:
                return c
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "services": {name: svc.to_dict() for name, svc in self.services.items()},
            "connections": [c.to_dict() for c in self.connections],
        }

    def validate(self) -> List[str]:
        """Validate topology, returning list of issues (empty = valid)."""
        issues: List[str] = []
        for name, svc in self.services.items():
            if svc.hydraulic_conductivity <= 0:
                issues.append(f"Service '{name}' has K <= 0")
            if svc.specific_storage <= 0:
                issues.append(f"Service '{name}' has Ss <= 0")
        for conn in self.connections:
            if conn.source not in self.services:
                issues.append(f"Connection source '{conn.source}' not found in services")
            if conn.target not in self.services:
                issues.append(f"Connection target '{conn.target}' not found in services")
        return issues


def load_topology(path: str) -> Topology:
    """Load a topology from a JSON file."""
    with open(path, "r") as f:
        data = json.load(f)
    return parse_topology(data)


def parse_topology(data: Dict[str, Any]) -> Topology:
    """Parse topology from a dictionary."""
    topo = Topology(name=data.get("name", "default"))
    services_data = data.get("services", [])
    if isinstance(services_data, dict):
        services_data = list(services_data.values())
    for svc_data in services_data:
        svc = ServiceLayer(
            name=svc_data["name"],
            hydraulic_conductivity=svc_data["hydraulic_conductivity"],
            specific_storage=svc_data.get("specific_storage", 0.01),
            queue_depth=svc_data.get("queue_depth", 0),
            processing_latency=svc_data.get("processing_latency", 0.0),
            replicas=svc_data.get("replicas", 1),
            is_recharge=svc_data.get("is_recharge", False),
            is_discharge=svc_data.get("is_discharge", False),
            grid_x=svc_data.get("grid_x", 0),
            grid_y=svc_data.get("grid_y", 0),
        )
        topo.add_service(svc)
    for conn_data in data.get("connections", []):
        conn = FlowConnection(
            source=conn_data["source"],
            target=conn_data["target"],
            connection_type=conn_data.get("connection_type", "porous"),
            bandwidth=conn_data.get("bandwidth", 0.0),
        )
        topo.add_connection(conn)
    return topo


def save_topology(topo: Topology, path: str) -> None:
    """Save a topology to a JSON file."""
    with open(path, "w") as f:
        json.dump(topo.to_dict(), f, indent=2)


def create_sample_topology() -> Topology:
    """Create a sample topology for demonstration."""
    topo = Topology(name="sample_pipeline")

    services = [
        ServiceLayer("ingestion", hydraulic_conductivity=1000.0, queue_depth=50,
                      processing_latency=0.01, is_recharge=True, grid_x=0, grid_y=2),
        ServiceLayer("validator", hydraulic_conductivity=500.0, specific_storage=0.02,
                      queue_depth=120, processing_latency=0.05, grid_x=1, grid_y=1),
        ServiceLayer("enricher", hydraulic_conductivity=300.0, specific_storage=0.015,
                      queue_depth=80, processing_latency=0.08, grid_x=1, grid_y=3),
        ServiceLayer("transformer", hydraulic_conductivity=200.0, specific_storage=0.03,
                      queue_depth=200, processing_latency=0.12, grid_x=2, grid_y=2),
        ServiceLayer("cache_writer", hydraulic_conductivity=800.0, queue_depth=10,
                      processing_latency=0.005, grid_x=3, grid_y=1),
        ServiceLayer("db_writer", hydraulic_conductivity=150.0, specific_storage=0.05,
                      queue_depth=300, processing_latency=0.2, grid_x=3, grid_y=3),
        ServiceLayer("api_out", hydraulic_conductivity=600.0, queue_depth=20,
                      processing_latency=0.02, is_discharge=True, grid_x=4, grid_y=2),
    ]
    for svc in services:
        topo.add_service(svc)

    connections = [
        FlowConnection("ingestion", "validator"),
        FlowConnection("ingestion", "enricher"),
        FlowConnection("validator", "transformer"),
        FlowConnection("enricher", "transformer"),
        FlowConnection("transformer", "cache_writer"),
        FlowConnection("transformer", "db_writer"),
        FlowConnection("cache_writer", "api_out"),
        FlowConnection("db_writer", "api_out"),
    ]
    for conn in connections:
        topo.add_connection(conn)

    return topo
