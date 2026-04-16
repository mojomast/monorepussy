"""Core data models for the Cyclone pipeline anomaly detection system.

Maps meteorological concepts to data pipeline properties:
- Velocity field (u, v) → forward flow rate, reprocessing rate
- Vorticity (ζ) → net rotational tendency
- Coriolis parameter (f) → base retry rate
- Potential vorticity (PV) → conserved quantity
- Saffir-Simpson categories → severity classification
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple


class CycloneCategory(IntEnum):
    """Saffir-Simpson analog for pipeline cyclone severity."""

    CALM = 0        # ζ ≈ 0, reprocessing < 1%
    DEPRESSION = 1  # ζ > 0, reprocessing < 5%
    STORM = 2       # ζ > threshold_1, reprocessing 5-15%
    SEVERE_STORM = 3  # ζ > threshold_2, reprocessing 15-30%, CISK detected
    CYCLONE = 4     # ζ > threshold_3, reprocessing 30-50%, cascading >2 stages
    HURRICANE = 5   # ζ > threshold_4, reprocessing >50%, pipeline stalled

    @property
    def label(self) -> str:
        labels = {
            0: "Calm",
            1: "Depression",
            2: "Storm",
            3: "Severe Storm",
            4: "Cyclone",
            5: "Hurricane",
        }
        return labels[self.value]

    @property
    def emoji(self) -> str:
        emojis = {
            0: "🌤️",
            1: "🌧️",
            2: "⛈️",
            3: "🌀",
            4: "🌪️",
            5: "☄️",
        }
        return emojis[self.value]


@dataclass
class VelocityField:
    """2D velocity field for a pipeline stage.

    u = forward flow rate (messages/second processed successfully)
    v = reprocessing rate (messages/second being retried/reprocessed)
    """

    u: float  # forward rate
    v: float  # reprocessing rate

    @property
    def speed(self) -> float:
        return (self.u ** 2 + self.v ** 2) ** 0.5

    @property
    def angle(self) -> float:
        """Angle of the velocity vector in radians."""
        import math
        return math.atan2(self.v, self.u)

    @property
    def reprocessing_ratio(self) -> float:
        """Fraction of total flow that is reprocessing."""
        total = self.u + self.v
        return self.v / total if total > 0 else 0.0


@dataclass
class PipelineStage:
    """A single stage in a data pipeline.

    Maps to a location in the 'fluid' where velocity and vorticity are measured.
    """

    name: str
    stage_type: str = "generic"  # kafka, rabbitmq, sqs, sns, pubsub, generic
    forward_rate: float = 0.0    # u: messages/s processed successfully
    reprocessing_rate: float = 0.0  # v: messages/s being retried
    queue_depth: int = 0         # current backlog
    consumer_count: int = 1      # parallel consumers/workers
    error_rate: float = 0.0      # errors per second
    dlq_depth: int = 0           # dead letter queue depth
    base_retry_rate: float = 0.0  # Coriolis parameter f

    # Computed in post_init — give defaults
    velocity: VelocityField = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.velocity is None:
            self.velocity = VelocityField(u=self.forward_rate, v=self.reprocessing_rate)

    @property
    def total_throughput(self) -> float:
        return self.forward_rate + self.reprocessing_rate

    @property
    def reprocessing_fraction(self) -> float:
        total = self.total_throughput
        return self.reprocessing_rate / total if total > 0 else 0.0

    @property
    def coriolis_parameter(self) -> float:
        """Base retry rate — the Coriolis parameter f."""
        return self.base_retry_rate if self.base_retry_rate > 0 else self.reprocessing_rate * 0.1

    @property
    def load_variance(self) -> float:
        """Stability metric: variance in load (simplified as queue/consumers ratio)."""
        return self.queue_depth / max(self.consumer_count, 1)


@dataclass
class VorticityReading:
    """Vorticity measurement at a pipeline stage."""

    stage_name: str
    zeta: float                # relative vorticity ζ
    absolute_vorticity: float = 0.0  # η = ζ + f
    divergence: float = 0.0    # ∇·V
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Computed
    pv: float = 0.0            # potential vorticity
    category: CycloneCategory = CycloneCategory.CALM
    is_accelerating: bool = False

    def __post_init__(self) -> None:
        if self.category == CycloneCategory.CALM and self.zeta > 0:
            self.category = classify_vorticity(self.zeta, 0.0)


@dataclass
class PipelineTopology:
    """The full pipeline topology — a directed graph of stages."""

    stages: Dict[str, PipelineStage] = field(default_factory=dict)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    # error/retry edges for CISK analysis
    retry_edges: List[Tuple[str, str, float]] = field(default_factory=list)

    def add_stage(self, stage: PipelineStage) -> None:
        self.stages[stage.name] = stage

    def add_edge(self, from_stage: str, to_stage: str) -> None:
        self.edges.append((from_stage, to_stage))

    def add_retry_edge(self, from_stage: str, to_stage: str, error_amplification: float) -> None:
        self.retry_edges.append((from_stage, to_stage, error_amplification))

    def get_stage(self, name: str) -> Optional[PipelineStage]:
        return self.stages.get(name)

    @property
    def stage_names(self) -> List[str]:
        return list(self.stages.keys())

    @property
    def downstream(self) -> Dict[str, List[str]]:
        """Map each stage to its downstream neighbors."""
        result: Dict[str, List[str]] = {s: [] for s in self.stages}
        for src, dst in self.edges:
            if src in result:
                result[src].append(dst)
        return result

    @property
    def upstream(self) -> Dict[str, List[str]]:
        """Map each stage to its upstream neighbors."""
        result: Dict[str, List[str]] = {s: [] for s in self.stages}
        for src, dst in self.edges:
            if dst in result:
                result[dst].append(src)
        return result


@dataclass
class CycloneDetection:
    """A detected cyclonic formation in the pipeline."""

    id: str
    center_stage: str
    category: CycloneCategory
    vorticity: float
    stages_affected: List[str] = field(default_factory=list)
    cisk_cycle: Optional[List[str]] = None
    cycle_gain: float = 0.0
    dlq_depth: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

    @property
    def severity_label(self) -> str:
        return f"Cat-{self.category.value} {self.category.label}"


@dataclass
class StabilityReading:
    """Stability analysis at a stage boundary."""

    boundary: str  # "stage1 → stage2"
    richardson_number: float
    throughput_gradient: float
    load_stability: float
    is_unstable: bool = False
    critical_threshold: float = 0.25

    def __post_init__(self) -> None:
        if not self.is_unstable:
            self.is_unstable = self.richardson_number < self.critical_threshold


@dataclass
class ForecastStep:
    """One step in a vorticity forecast."""

    timestamp: datetime
    stage_vorticities: Dict[str, float]
    stage_categories: Dict[str, CycloneCategory]
    cyclone_count: int = 0


# ── Helper functions ──────────────────────────────────────────

def classify_vorticity(zeta: float, reprocessing_fraction: float) -> CycloneCategory:
    """Classify a vorticity reading into a Saffir-Simpson analog category.

    Category 1 (Depression):   ζ > 0, reprocessing < 5%
    Category 2 (Storm):        ζ > 0.5, reprocessing 5-15%
    Category 3 (Severe Storm): ζ > 1.0, reprocessing 15-30%
    Category 4 (Cyclone):      ζ > 2.0, reprocessing 30-50%
    Category 5 (Hurricane):    ζ > 3.0, reprocessing > 50%
    """
    pct = reprocessing_fraction * 100

    if zeta <= 0:
        return CycloneCategory.CALM
    if zeta < 0.5 and pct < 5:
        return CycloneCategory.DEPRESSION
    if zeta < 1.0 and pct < 15:
        return CycloneCategory.STORM
    if zeta < 2.0 and pct < 30:
        return CycloneCategory.SEVERE_STORM
    if zeta < 3.0 and pct < 50:
        return CycloneCategory.CYCLONE
    return CycloneCategory.HURRICANE


def topology_from_dict(data: Dict[str, Any]) -> PipelineTopology:
    """Build a PipelineTopology from a dictionary (e.g. parsed JSON)."""
    topo = PipelineTopology()
    for s in data.get("stages", []):
        stage = PipelineStage(
            name=s["name"],
            stage_type=s.get("type", "generic"),
            forward_rate=s.get("forward_rate", 0.0),
            reprocessing_rate=s.get("reprocessing_rate", 0.0),
            queue_depth=s.get("queue_depth", 0),
            consumer_count=s.get("consumer_count", 1),
            error_rate=s.get("error_rate", 0.0),
            dlq_depth=s.get("dlq_depth", 0),
            base_retry_rate=s.get("base_retry_rate", 0.0),
        )
        topo.add_stage(stage)
    for e in data.get("edges", []):
        topo.add_edge(e[0], e[1])
    for re in data.get("retry_edges", []):
        topo.add_retry_edge(re[0], re[1], re[2])
    return topo


def topology_from_json(path: str) -> PipelineTopology:
    """Load a PipelineTopology from a JSON file."""
    with open(path, "r") as f:
        data = json.load(f)
    return topology_from_dict(data)


def load_fixture(name: str) -> Dict[str, Any]:
    """Load a JSON fixture file from the fixtures directory."""
    import os
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "fixtures")
    path = os.path.join(fixtures_dir, name)
    with open(path, "r") as f:
        return json.load(f)
