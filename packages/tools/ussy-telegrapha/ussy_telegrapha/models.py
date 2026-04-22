"""Shared data models for Telegrapha."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Hop:
    """A single hop in a pipeline route."""

    name: str
    degradation: float = 0.0  # epsilon_i
    reliability: float = 1.0  # R_i (0.0–1.0)
    details: str = ""
    serialization_degradation: float = 0.0
    deserialization_degradation: float = 0.0


@dataclass
class Route:
    """A pipeline route composed of hops."""

    name: str
    hops: list[Hop] = field(default_factory=list)

    @property
    def hop_count(self) -> int:
        return len(self.hops)

    @property
    def end_to_end_fidelity(self) -> float:
        """Cumulative fidelity: M(n) = M0 * prod(1 - epsilon_i)."""
        fidelity = 1.0
        for hop in self.hops:
            fidelity *= 1.0 - hop.degradation
        return fidelity

    @property
    def end_to_end_reliability(self) -> float:
        """Series reliability: R_total = prod(R_i)."""
        reliability = 1.0
        for hop in self.hops:
            reliability *= hop.reliability
        return reliability


@dataclass
class AttenuationResult:
    """Result of attenuation budget analysis."""

    route: Route
    fidelity: float = 0.0
    cumulative_degradation: float = 0.0
    is_distortionless: bool = False
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.fidelity == 0.0 and self.route.hops:
            self.fidelity = self.route.end_to_end_fidelity
        self.cumulative_degradation = 1.0 - self.fidelity


@dataclass
class RelayChainResult:
    """Result of relay chain reliability analysis."""

    route: Route
    target_sla: float = 0.999
    required_per_hop: float = 0.0
    actual_reliability: float = 0.0
    weakest_link: str = ""
    meets_sla: bool = False
    recommendations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.required_per_hop == 0.0 and self.route.hop_count > 0:
            self.required_per_hop = self.target_sla ** (1.0 / self.route.hop_count)
        if self.actual_reliability == 0.0 and self.route.hops:
            self.actual_reliability = self.route.end_to_end_reliability
        self.meets_sla = self.actual_reliability >= self.target_sla
        if not self.weakest_link and self.route.hops:
            weakest = min(self.route.hops, key=lambda h: h.reliability)
            self.weakest_link = weakest.name


@dataclass
class CapacityResult:
    """Result of Shannon-Hartley capacity analysis."""

    bandwidth: float = 0.0  # B_pipeline
    signal_rate: float = 0.0  # S_signal
    noise_rate: float = 0.0  # N_noise
    snr: float = 0.0
    theoretical_ceiling: float = 0.0
    utilization_pct: float = 0.0
    multiplexing_gain: float = 1.0
    recommendations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.noise_rate > 0 and self.snr == 0.0:
            self.snr = self.signal_rate / self.noise_rate
        elif self.noise_rate == 0 and self.snr == 0.0:
            self.snr = float("inf")
        if self.snr > 0 and self.theoretical_ceiling == 0.0:
            import math
            self.theoretical_ceiling = self.bandwidth * math.log2(1 + self.snr)
        if self.theoretical_ceiling > 0 and self.utilization_pct == 0.0:
            self.utilization_pct = (self.signal_rate / self.theoretical_ceiling) * 100


@dataclass
class PrecedenceClass:
    """A single priority class in the M/G/1 model."""

    name: str
    label: str  # FLASH, IMMEDIATE, PRIORITY, ROUTINE
    arrival_rate: float = 0.0  # lambda (per second)
    service_time: float = 0.0  # 1/mu (seconds)
    avg_wait: float = 0.0
    preemption_overhead: float = 0.0


@dataclass
class PrecedenceResult:
    """Result of precedence analysis."""

    classes: list[PrecedenceClass] = field(default_factory=list)
    optimal_class_count: int = 0
    system_stability: float = 0.0
    is_stable: bool = False
    recommendations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.classes:
            total_rho = sum(
                c.arrival_rate * c.service_time for c in self.classes
            )
            self.system_stability = total_rho
            self.is_stable = total_rho < 1.0
        if self.optimal_class_count == 0 and self.classes:
            self.optimal_class_count = len(self.classes)


@dataclass
class HammingResult:
    """Result of FEC vs ARQ analysis."""

    error_rate: float = 0.0
    pipeline_length: int = 0
    target_reliability: float = 0.999
    arq_expected_transmissions: float = 0.0
    arq_latency_factor: float = 0.0
    arq_bandwidth_overhead: float = 0.0
    fec_code_n: int = 3
    fec_code_k: int = 2
    fec_failure_prob: float = 0.0
    fec_latency_factor: float = 0.0
    fec_bandwidth_overhead: float = 0.0
    preferred: str = ""  # "ARQ" or "FEC"
    break_even_error_rate: float = 0.0
    schema_drift_distance: int = 0
    correction_capacity: int = 0
    recommendations: list[str] = field(default_factory=list)


@dataclass
class DLQEntry:
    """A single dead letter queue entry."""

    id: str = ""
    timestamp: str = ""
    failure_type: str = ""
    source_hop: str = ""
    original_topic: str = ""
    payload_summary: str = ""
    age_hours: float = 0.0


@dataclass
class DLOResult:
    """Result of Dead Letter Office analysis."""

    total_entries: int = 0
    accumulation_rate: float = 0.0  # messages/hour
    resolution_rate: float = 0.0  # messages/hour
    churn_rate: float = 0.0
    failure_taxonomy: dict[str, float] = field(default_factory=dict)
    health_score: float = 0.0
    health_status: str = "UNKNOWN"
    systemic_source: str = ""
    systemic_source_pct: float = 0.0
    recommendations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.accumulation_rate > 0 and self.churn_rate == 0.0:
            if self.resolution_rate > 0:
                self.churn_rate = self.accumulation_rate / self.resolution_rate
            else:
                self.churn_rate = float("inf")
        if self.health_score == 0.0:
            # Health = churn_ratio * resolution_ratio * (1 - aging_factor)
            # Simplified: lower churn and higher resolution = healthier
            churn_factor = min(1.0, self.resolution_rate / max(self.accumulation_rate, 0.001))
            self.health_score = churn_factor * 0.5  # simplified
        if self.health_status == "UNKNOWN":
            if self.health_score >= 0.7:
                self.health_status = "HEALTHY"
            elif self.health_score >= 0.4:
                self.health_status = "WARNING"
            else:
                self.health_status = "CRITICAL"


@dataclass
class PipelineTopology:
    """Full pipeline topology definition."""

    name: str = ""
    routes: list[Route] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    loaded_at: str = ""

    def __post_init__(self) -> None:
        if not self.loaded_at:
            self.loaded_at = datetime.now(timezone.utc).isoformat()
