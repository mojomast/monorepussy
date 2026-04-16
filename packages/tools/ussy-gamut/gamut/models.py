"""Core data models for the gamut package.

Defines the fundamental abstractions: TypeGamut, StageProfile, ClippingResult,
RenderingIntent, and PipelineDAG — everything the analyzers and visualizers
operate on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RenderingIntent(Enum):
    """How out-of-gamut values are handled at a stage boundary.

    Mirrors the ICC color-management rendering intents:

    * **Perceptual** – best-effort mapping that preserves relationships
      (e.g. rounding a value to fit).
    * **AbsoluteColorimetric** – error / reject on out-of-gamut values
      (e.g. NOT NULL constraint violation).
    * **Saturation** – clamping to the nearest in-gamut value
      (e.g. integer overflow wrapping / saturation).
    """

    PERCEPTUAL = "perceptual"
    ABSOLUTE_COLORIMETRIC = "absolute_colorimetric"
    SATURATION = "saturation"


class ClippingRisk(Enum):
    """Qualitative risk level for a field-level gamut transition."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FieldType(Enum):
    """Broad category of a data field."""

    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    STRING = "string"
    BINARY = "binary"
    TIMESTAMP = "timestamp"
    DATE = "date"
    TIME = "time"
    BOOLEAN = "boolean"
    ARRAY = "array"
    MAP = "map"
    STRUCT = "struct"
    ENUM = "enum"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# TypeGamut — describes the representable value space of a single type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TypeGamut:
    """The representable value space of a data type.

    Attributes:
        system: Source system name (e.g. "postgresql", "json").
        type_name: Native type name (e.g. "NUMERIC(38,18)", "number").
        field_type: Broad field-type category.
        min_value: Minimum representable value (None = unbounded).
        max_value: Maximum representable value (None = unbounded).
        precision: Total digits of precision (None = infinite/variable).
        scale: Digits after decimal point (None = floating / variable).
        charset: Character set for strings (None = binary/unrestricted).
        max_length: Maximum length for strings / arrays (None = unbounded).
        timezone_aware: Whether temporal types carry timezone info.
        tz_precision: Sub-second precision in decimal digits (e.g. 6 = micros).
        nullable: Whether the type can represent NULL.
    """

    system: str
    type_name: str
    field_type: FieldType
    min_value: float | None = None
    max_value: float | None = None
    precision: int | None = None
    scale: int | None = None
    charset: str | None = None
    max_length: int | None = None
    timezone_aware: bool | None = None
    tz_precision: int | None = None
    nullable: bool = True


# ---------------------------------------------------------------------------
# FieldProfile — a named field resolved to a TypeGamut
# ---------------------------------------------------------------------------

@dataclass
class FieldProfile:
    """A named data field with its resolved gamut."""

    name: str
    gamut: TypeGamut
    source_type_raw: str = ""


# ---------------------------------------------------------------------------
# StageProfile — the gamut of an entire pipeline stage
# ---------------------------------------------------------------------------

@dataclass
class StageProfile:
    """Gamut profile for one pipeline stage (e.g. a table, a schema)."""

    name: str
    system: str
    fields: list[FieldProfile] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def field_names(self) -> list[str]:
        return [f.name for f in self.fields]

    def get_field(self, name: str) -> FieldProfile | None:
        for f in self.fields:
            if f.name == name:
                return f
        return None


# ---------------------------------------------------------------------------
# ClippingResult — per-field clipping analysis at a boundary
# ---------------------------------------------------------------------------

@dataclass
class ClippingResult:
    """Result of comparing a source field gamut to a destination field gamut."""

    field_name: str
    source_gamut: TypeGamut
    dest_gamut: TypeGamut
    risk: ClippingRisk = ClippingRisk.NONE
    delta_e: float = 0.0
    rendering_intent: RenderingIntent = RenderingIntent.PERCEPTUAL
    clipped_examples: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def is_clipping(self) -> bool:
        return self.risk != ClippingRisk.NONE


# ---------------------------------------------------------------------------
# BoundaryReport — full analysis of a stage-to-stage boundary
# ---------------------------------------------------------------------------

@dataclass
class BoundaryReport:
    """Aggregated clipping analysis for a single stage boundary."""

    source_stage: str
    dest_stage: str
    results: list[ClippingResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def clipping_count(self) -> int:
        return sum(1 for r in self.results if r.is_clipping)

    @property
    def critical_count(self) -> int:
        return sum(1 for r in self.results if r.risk == ClippingRisk.CRITICAL)

    @property
    def max_delta_e(self) -> float:
        return max((r.delta_e for r in self.results), default=0.0)

    def get_clipping_results(self) -> list[ClippingResult]:
        return [r for r in self.results if r.is_clipping]


# ---------------------------------------------------------------------------
# PipelineDAG — a directed acyclic graph of stage profiles
# ---------------------------------------------------------------------------

@dataclass
class PipelineEdge:
    """A directed edge between two stages in the pipeline DAG."""

    source: str
    dest: str
    label: str = ""


@dataclass
class PipelineDAG:
    """A pipeline represented as a DAG of stage profiles."""

    name: str
    stages: dict[str, StageProfile] = field(default_factory=dict)
    edges: list[PipelineEdge] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_stage(self, stage: StageProfile) -> None:
        self.stages[stage.name] = stage

    def add_edge(self, source: str, dest: str, label: str = "") -> None:
        self.edges.append(PipelineEdge(source=source, dest=dest, label=label))

    def get_stage(self, name: str) -> StageProfile | None:
        return self.stages.get(name)

    def boundary_pairs(self) -> list[tuple[StageProfile, StageProfile]]:
        """Return (source, dest) pairs for every edge."""
        pairs: list[tuple[StageProfile, StageProfile]] = []
        for edge in self.edges:
            src = self.stages.get(edge.source)
            dst = self.stages.get(edge.dest)
            if src is not None and dst is not None:
                pairs.append((src, dst))
        return pairs


# ---------------------------------------------------------------------------
# SampleValue — a single observed value from the runtime sampler
# ---------------------------------------------------------------------------

@dataclass
class SampleValue:
    """An observed value at a pipeline boundary."""

    field_name: str
    value: Any
    stage: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_clipped: bool = False
    original_value: Any = None


# ---------------------------------------------------------------------------
# SampleReport — aggregated sampling results
# ---------------------------------------------------------------------------

@dataclass
class SampleReport:
    """Aggregated results from runtime sampling at a boundary."""

    source_stage: str
    dest_stage: str
    samples: list[SampleValue] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_count(self) -> int:
        return len(self.samples)

    @property
    def clipped_count(self) -> int:
        return sum(1 for s in self.samples if s.is_clipped)

    @property
    def clipped_pct(self) -> float:
        if self.total_count == 0:
            return 0.0
        return (self.clipped_count / self.total_count) * 100.0

    def clipped_by_field(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self.samples:
            if s.is_clipped:
                counts[s.field_name] = counts.get(s.field_name, 0) + 1
        return counts
