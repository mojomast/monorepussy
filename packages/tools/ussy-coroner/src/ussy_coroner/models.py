"""Data models for Coroner forensic analysis."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ── Enums ──────────────────────────────────────────────────────────────────

class TraceType(str, Enum):
    """Seven trace types mapped from forensic science to CI/CD equivalents."""
    FIBERS = "fibers"                   # Dependency residue (transitive versions)
    DNA = "dna"                         # Configuration fingerprints (env+feature flags)
    FINGERPRINTS = "fingerprints"       # Build hash digests at stage boundaries
    SOIL = "soil"                       # Platform residue (OS, kernel, arch)
    TOOL_MARKS = "tool_marks"           # Toolchain impressions (compiler flags, versions)
    GLASS_FRAGMENTS = "glass_fragments" # Artifact shards (partial outputs, intermediate files)
    PAINT_LAYERS = "paint_layers"       # Docker layer provenance


# Persistence decay constants (lambda) per trace type
TRACE_PERSISTENCE: dict[TraceType, float] = {
    TraceType.FIBERS: 0.05,
    TraceType.DNA: 0.15,
    TraceType.FINGERPRINTS: 0.02,
    TraceType.SOIL: 0.30,
    TraceType.TOOL_MARKS: 0.10,
    TraceType.GLASS_FRAGMENTS: 0.08,
    TraceType.PAINT_LAYERS: 0.12,
}


class StageStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    RUNNING = "running"


class VelocityClass(str, Enum):
    LOW = "low"           # Gradual degradation
    MEDIUM = "medium"     # Sudden failure (assertion/type error pattern)
    HIGH = "high"         # Catastrophic failure (OOM, segfault)


class LuminolResult(str, Enum):
    NEGATIVE = "negative"
    PRESUMPTIVE_POSITIVE = "presumptive_positive"
    CONFIRMED = "confirmed"


# ── Stage ──────────────────────────────────────────────────────────────────

@dataclass
class Stage:
    """A single pipeline stage."""
    name: str
    index: int
    status: StageStatus = StageStatus.SUCCESS
    start_time: datetime | None = None
    end_time: datetime | None = None
    log_content: str = ""
    env_vars: dict[str, str] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    artifact_hashes: dict[str, str] = field(default_factory=dict)


# ── PipelineRun ────────────────────────────────────────────────────────────

@dataclass
class PipelineRun:
    """A single CI/CD pipeline run."""
    run_id: str
    stages: list[Stage] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def failed_stages(self) -> list[Stage]:
        return [s for s in self.stages if s.status == StageStatus.FAILURE]

    @property
    def first_failure(self) -> Stage | None:
        failures = self.failed_stages
        return failures[0] if failures else None


# ── Trace Evidence ─────────────────────────────────────────────────────────

@dataclass
class TraceEvidence:
    """A single piece of trace evidence between two stages."""
    source_stage: str
    target_stage: str
    trace_type: TraceType
    strength: float = 1.0
    description: str = ""
    source_index: int = 0
    target_index: int = 0
    suspicion_score: float = 0.0

    def __post_init__(self) -> None:
        # Compute suspicion score using persistence-weighted formula
        # S(t, i, j) = T[i][j] * P0(t) * e^(-lambda_t * |stage_index(j) - stage_index(i)|)
        lam = TRACE_PERSISTENCE.get(self.trace_type, 0.10)
        distance = abs(self.target_index - self.source_index)
        self.suspicion_score = self.strength * pow(2.718281828, -lam * distance)


@dataclass
class TraceTransferResult:
    """Result of bidirectional trace analysis between stages."""
    forward_traces: list[TraceEvidence] = field(default_factory=list)
    reverse_traces: list[TraceEvidence] = field(default_factory=list)
    suspicious_transfers: list[TraceEvidence] = field(default_factory=list)


# ── Error Spatter (Blood Spatter) ─────────────────────────────────────────

@dataclass
class ErrorStain:
    """A single error indicator treated as a blood stain."""
    stage_name: str
    stage_index: int
    breadth: int = 0    # affected components
    depth: int = 0      # consecutive failing stages
    impact_angle: float = 0.0
    component: str = ""

    def __post_init__(self) -> None:
        # impact angle: alpha = arcsin(breadth / depth) when depth > breadth
        # We use a safe version: alpha = arcsin(min(breadth/max(depth,1), 1))
        import math
        if self.depth > 0:
            ratio = min(self.breadth / max(self.depth, 1), 1.0)
            self.impact_angle = math.degrees(math.asin(ratio))
        else:
            self.impact_angle = 0.0


@dataclass
class SpatterReconstruction:
    """Result of error spatter reconstruction."""
    stains: list[ErrorStain] = field(default_factory=list)
    convergence_stage: str = ""
    convergence_component: str = ""
    origin_depth: float = 0.0
    confidence: float = 0.0
    variance: float = 0.0
    velocity_class: VelocityClass = VelocityClass.MEDIUM
    likely_cause: str = ""


# ── Striation ──────────────────────────────────────────────────────────────

@dataclass
class StriationMatch:
    """Cross-correlation match between two builds' error signatures."""
    build_id_1: str
    build_id_2: str
    correlation: float = 0.0
    same_root_cause: bool = False
    resolution_note: str = ""

    def __post_init__(self) -> None:
        if self.correlation > 0.8:
            self.same_root_cause = True


# ── Luminol ────────────────────────────────────────────────────────────────

@dataclass
class LuminolFinding:
    """A single luminol finding (presumptive or confirmed)."""
    category: str        # "cache" or "ninhydrin" or "confirmatory"
    path: str = ""
    expected_hash: str = ""
    actual_hash: str = ""
    env_vars: list[str] = field(default_factory=list)
    source_stage: str = ""
    target_stage: str = ""
    result: LuminolResult = LuminolResult.NEGATIVE
    description: str = ""


@dataclass
class LuminolReport:
    """Complete luminol scan report."""
    findings: list[LuminolFinding] = field(default_factory=list)
    root_cause: str = ""
    confirmed: bool = False


# ── Custody ────────────────────────────────────────────────────────────────

@dataclass
class CustodyEntry:
    """A single entry in the chain of custody."""
    stage_name: str
    stage_index: int
    handler: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    action: str = ""
    hash_value: str = ""

    def compute_hash(self, previous_hash: str) -> str:
        """H_n = H(H_{n-1} || handler_n || t_n || action_n)"""
        data = f"{previous_hash}||{self.handler}||{self.timestamp.isoformat()}||{self.action}"
        self.hash_value = hashlib.sha256(data.encode()).hexdigest()
        return self.hash_value


@dataclass
class CustodyChain:
    """Full chain of custody for a pipeline run."""
    run_id: str = ""
    entries: list[CustodyEntry] = field(default_factory=list)


@dataclass
class CustodyComparison:
    """Result of comparing custody chains between two runs."""
    run_id_1: str
    run_id_2: str
    divergence_stage: str = ""
    divergence_index: int = 0
    same_inputs: bool = False
    same_process: bool = False
    nondeterminism: bool = False
    likely_cause: str = ""


# ── Investigation ──────────────────────────────────────────────────────────

@dataclass
class Investigation:
    """Complete forensic investigation of a pipeline run."""
    run_id: str
    trace_result: TraceTransferResult = field(default_factory=TraceTransferResult)
    spatter_result: SpatterReconstruction = field(default_factory=SpatterReconstruction)
    striation_matches: list[StriationMatch] = field(default_factory=list)
    luminol_report: LuminolReport = field(default_factory=LuminolReport)
    custody_chain: CustodyChain = field(default_factory=CustodyChain)
    custody_comparison: CustodyComparison | None = None
    summary: str = ""
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
