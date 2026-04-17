"""Core data models for Cambium dependency analysis."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CompatibilityZone(Enum):
    """Zone classification for dependency compatibility."""
    SAFE = "safe"
    PARTIAL = "partial"
    DOOMED = "doomed"


class BondTrend(Enum):
    """Trend direction for integration bond strength."""
    STRENGTHENING = "strengthening"
    STABLE = "stable"
    DECAYING = "decaying"


@dataclass
class DependencyPair:
    """Represents a consumer-provider dependency relationship."""
    consumer: str
    provider: str
    consumer_version: str = ""
    provider_version: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class CompatibilityScore:
    """Scion/rootstock compatibility — API surface match score.

    C(a,b) = Φ(δ_tax) × β_recog × ψ_phen
    """
    type_similarity: float = 0.0   # Φ(δ_tax) — Jaccard of exported types
    precondition_satisfaction: float = 0.0  # β_recog — fraction of provider preconditions satisfied
    version_overlap: float = 0.0    # ψ_phen — version range overlap
    weight_types: float = 0.4
    weight_preconditions: float = 0.3
    weight_version: float = 0.3

    @property
    def composite(self) -> float:
        """Weighted compatibility score in [0, 1]."""
        return (
            self.weight_types * self.type_similarity
            + self.weight_preconditions * self.precondition_satisfaction
            + self.weight_version * self.version_overlap
        )


@dataclass
class AlignmentScore:
    """Cambium alignment — interface precision score.

    A_align(a,b) = w1·A_name + w2·A_signature + w3·A_semantic
    """
    name_match: float = 0.0       # A_name — method/attribute name matching ratio
    signature_match: float = 0.0  # A_signature — parameter type/count matching
    semantic_match: float = 0.0   # A_semantic — behavioral contract alignment
    w_name: float = 0.3
    w_signature: float = 0.4
    w_semantic: float = 0.3

    @property
    def composite(self) -> float:
        """Weighted alignment score in [0, 1]."""
        return (
            self.w_name * self.name_match
            + self.w_signature * self.signature_match
            + self.w_semantic * self.semantic_match
        )

    @property
    def status(self) -> str:
        c = self.composite
        if c >= 0.9:
            return "ALIGNED"
        elif c >= 0.6:
            return "PARTIAL"
        else:
            return "MISALIGNED"


@dataclass
class CallusDynamics:
    """Callus formation — adapter generation dynamics.

    M_callus(t) = K / (1 + (K/M0 - 1) · e^(-r·t))
    """
    k_adapter: float = 10.0   # total mismatches requiring adapters
    n0: float = 2.0           # initially auto-resolvable
    r_gen: float = 0.5        # adapter generation rate
    test_pass_rate: float = 0.0  # Q_adapter quality metric

    def callus_at(self, t: float) -> float:
        """Number of adapters resolved at time t."""
        if self.k_adapter == 0:
            return 0.0
        ratio = self.k_adapter / self.n0 - 1.0
        if ratio <= 0:
            return self.k_adapter
        return self.k_adapter / (1.0 + ratio * math.exp(-self.r_gen * t))

    @property
    def bridging_time(self) -> float:
        """Time until minimum functional integration.

        t_bridge = (1/r_gen) · ln((K_adapter - N_bridge) / (N_bridge · (K_adapter/N0 - 1)))
        N_bridge is half of K_adapter (minimum functional threshold).
        """
        if self.r_gen == 0 or self.k_adapter == 0:
            return float("inf")
        if self.k_adapter / self.n0 <= 1.0:
            # Already past bridging point (N0 >= K)
            return 0.0
        # Solve: K / (1 + (K/N0-1)*e^(-r*t)) = K/2
        # => e^(-r*t) = 1/(K/N0 - 1)
        # => t = ln(K/N0 - 1) / r
        ratio = self.k_adapter / self.n0 - 1.0
        if ratio <= 0:
            return 0.0
        return (1.0 / self.r_gen) * math.log(ratio)

    @property
    def adapter_quality(self) -> float:
        """Q_adapter = test_pass_rate (0-1). 1 = fully differentiated, 0 = undifferentiated callus."""
        return self.test_pass_rate


@dataclass
class DriftDebt:
    """Delayed incompatibility — predictive drift breakage.

    D(t) = Δ₀ · λ · (1 - e^(-t/λ))
    t_break = -λ · ln(1 - D_critical / (Δ₀ · λ))
    """
    delta_behavior: float = 0.0    # Δ_behavior: sorting stability, error format changes
    delta_contract: float = 0.0    # Δ_contract: undocumented required fields, changed side effects
    delta_environment: float = 0.0 # Δ_environment: Python/OS/timezone drift
    lambda_s: float = 6.0          # dissipation timescale (months)
    d_critical: float = 1.0        # critical drift threshold

    @property
    def delta_0(self) -> float:
        """Total drift rate: Δ₀ = Δ_behavior + Δ_contract + Δ_environment."""
        return self.delta_behavior + self.delta_contract + self.delta_environment

    @property
    def zone(self) -> CompatibilityZone:
        """Classify as safe or doomed based on drift vs dissipation."""
        if self.delta_0 * self.lambda_s < self.d_critical:
            return CompatibilityZone.SAFE
        return CompatibilityZone.DOOMED

    def drift_at(self, t: float) -> float:
        """Drift debt at time t: D(t) = Δ₀ · λ · (1 - e^(-t/λ))."""
        if self.lambda_s == 0:
            return float("inf")
        return self.delta_0 * self.lambda_s * (1.0 - math.exp(-t / self.lambda_s))

    @property
    def breakage_time(self) -> float:
        """Predicted time to breakage in months.

        t_break = -λ · ln(1 - D_critical / (Δ₀ · λ))
        Returns inf if in safe zone.
        """
        product = self.delta_0 * self.lambda_s
        if product == 0:
            return float("inf")
        if product < self.d_critical:
            return float("inf")  # safe zone — drift dissipates faster than it accumulates
        ratio = self.d_critical / product
        if ratio >= 1.0:
            return float("inf")
        return -self.lambda_s * math.log(1.0 - ratio)

    def drift_budget_consumed(self, t: float) -> float:
        """Fraction of drift budget consumed at time t: D(t)/D_critical."""
        if self.d_critical == 0:
            return 1.0
        return min(self.drift_at(t) / self.d_critical, 1.0)


@dataclass
class BondStrength:
    """Graft union strength — integration bond trajectory.

    B(t) = B_max / (1 + e^(-k_b·(t - t50_b)))
    """
    b_max: float = 1.0       # maximum bond strength
    k_b: float = 0.3         # maturation rate
    t50: float = 5.0         # half-strength time (months)
    s_test: float = 0.0      # test evidence component
    s_incident: float = 0.0  # incident-free period component
    s_change: float = 0.0    # stability under version changes
    s_doc: float = 0.0       # documentation alignment

    def strength_at(self, t: float) -> float:
        """Bond strength at time t."""
        if self.b_max == 0:
            return 0.0
        return self.b_max / (1.0 + math.exp(-self.k_b * (t - self.t50)))

    def strength_rate(self, t: float) -> float:
        """dB/dt = k_b · B(t) · (1 - B(t)/B_max).

        Positive = strengthening, Negative = decaying.
        """
        b_t = self.strength_at(t)
        return self.k_b * b_t * (1.0 - b_t / self.b_max)

    def trend_at(self, t: float) -> BondTrend:
        """Classify bond trajectory at time t."""
        rate = self.strength_rate(t)
        threshold = 0.01
        if rate > threshold:
            return BondTrend.STRENGTHENING
        elif rate < -threshold:
            return BondTrend.DECAYING
        return BondTrend.STABLE


@dataclass
class DwarfFactor:
    """Rootstock vigor/dwarfing — constraint propagation.

    Capability_chain = 1 / Σ_d (1/C_d)
    """
    capability_with: float = 1.0    # capability when dependency is present
    capability_without: float = 1.0  # capability when dependency is absent

    @property
    def dwarf_ratio(self) -> float:
        """Dwarf_factor(d) = Capability_with(d) / Capability_without(d).

        <1 means dwarfing (reduces capability), >=1 means neutral or beneficial.
        """
        if self.capability_without == 0:
            return 0.0
        return self.capability_with / self.capability_without

    @property
    def is_dwarfing(self) -> bool:
        return self.dwarf_ratio < 0.7

    @property
    def capability_reduction_pct(self) -> float:
        """Percentage of capability reduction."""
        return (1.0 - self.dwarf_ratio) * 100.0


@dataclass
class DependencyNode:
    """A node in the dependency tree for dwarfing analysis."""
    name: str
    capability: float = 1.0
    children: list[DependencyNode] = field(default_factory=list)

    @property
    def chain_capability(self) -> float:
        """Capability throughput through this chain: 1 / Σ(1/C_d).
        
        Only considers the deepest path to each leaf. Zero capability
        on any node in the path zeroes the entire path.
        """
        paths = self._collect_paths()
        if not paths:
            return self.capability
        # Use the path with the minimum capability (weakest link)
        path_caps = []
        for path in paths:
            if any(c == 0 for c in path):
                path_caps.append(0.0)
            else:
                path_caps.append(1.0 / sum(1.0 / c for c in path))
        # Return the average capability across all paths
        return sum(path_caps) / len(path_caps) if path_caps else 0.0

    def _collect_paths(self, current: list[float] | None = None) -> list[list[float]]:
        """Collect all root-to-leaf capability paths."""
        if current is None:
            current = []
        current = current + [self.capability]
        if not self.children:
            return [current]
        paths = []
        for child in self.children:
            paths.extend(child._collect_paths(current))
        return paths

    def _collect_conductances(self, out: list[float]) -> None:
        if self.capability > 0:
            out.append(self.capability)
        for child in self.children:
            child._collect_conductances(out)


@dataclass
class GCISnapshot:
    """Graft Compatibility Index — the unified metric.

    GCI(a,b,t) = C(a,b) · A_interface · Q_adapter(t) · (1-D(t)/D_critical) · B(t)/B_max · V_system
    """
    compatibility: float = 0.0     # C(a,b)
    alignment: float = 0.0         # A_interface
    adapter_quality: float = 0.0   # Q_adapter(t)
    drift_fraction: float = 0.0    # D(t)/D_critical
    bond_fraction: float = 0.0     # B(t)/B_max
    system_vigor: float = 0.0      # V_system (dwarfing chain capability)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def gci(self) -> float:
        """Compute GCI. Any zero component kills the whole score."""
        drift_penalty = max(0.0, 1.0 - self.drift_fraction)
        return (
            self.compatibility
            * self.alignment
            * self.adapter_quality
            * drift_penalty
            * self.bond_fraction
            * self.system_vigor
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "gci": round(self.gci, 4),
            "compatibility": round(self.compatibility, 4),
            "alignment": round(self.alignment, 4),
            "adapter_quality": round(self.adapter_quality, 4),
            "drift_fraction": round(self.drift_fraction, 4),
            "bond_fraction": round(self.bond_fraction, 4),
            "system_vigor": round(self.system_vigor, 4),
            "timestamp": self.timestamp,
        }


@dataclass
class InterfaceInfo:
    """Extracted interface information for a module/package."""
    name: str = ""
    exported_types: set[str] = field(default_factory=set)
    exported_functions: set[str] = field(default_factory=set)
    method_signatures: dict[str, list[str]] = field(default_factory=dict)
    preconditions: list[str] = field(default_factory=list)
