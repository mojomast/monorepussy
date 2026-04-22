"""Data models for Stemma."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class VariantType(Enum):
    """Type of variant reading."""
    UNANIMOUS = "unanimous"
    MAJORITY = "majority"
    VARIANT = "variant"
    OMISSION = "omission"


class Classification(Enum):
    """Classification of a variant as error or intentional."""
    SCRIBAL_ERROR = "scribal_error"
    CONSCIOUS_MODIFICATION = "conscious_modification"
    AMBIGUOUS = "ambiguous"


class WitnessRole(Enum):
    """Role of a witness in the stemma."""
    ARCHETYPE = "archetype"
    HYPERARCHETYPE = "hyparchetype"
    TERMINAL = "terminal"
    CONTAMINATED = "contaminated"


@dataclass
class Witness:
    """A code witness (one variant of a function/module)."""
    label: str
    source: str  # file path or description
    lines: list[str] = field(default_factory=list)
    normalized_lines: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.normalized_lines and not self.lines:
            self.lines = list(self.normalized_lines)
        if self.lines and not self.normalized_lines:
            self.normalized_lines = [normalize_line(l) for l in self.lines]


@dataclass
class Reading:
    """A specific reading at a variation unit."""
    text: str
    witnesses: list[str] = field(default_factory=list)
    variant_type: VariantType = VariantType.UNANIMOUS

    @property
    def witness_count(self) -> int:
        return len(self.witnesses)

    @property
    def witness_labels(self) -> str:
        return " ".join(self.witnesses)


@dataclass
class VariationUnit:
    """A position where witnesses disagree."""
    line_number: int
    readings: list[Reading] = field(default_factory=list)
    classification: Optional[Classification] = None
    confidence: float = 0.0
    rationale: str = ""

    @property
    def is_variant(self) -> bool:
        return len(self.readings) > 1

    @property
    def majority_reading(self) -> Optional[Reading]:
        if not self.readings:
            return None
        return max(self.readings, key=lambda r: r.witness_count)

    @property
    def minority_readings(self) -> list[Reading]:
        if not self.readings:
            return []
        maj = self.majority_reading
        return [r for r in self.readings if r is not maj]


@dataclass
class CollationResult:
    """Result of collating multiple witnesses."""
    witnesses: list[Witness] = field(default_factory=list)
    variation_units: list[VariationUnit] = field(default_factory=list)
    aligned_lines: dict[int, dict[str, str]] = field(default_factory=dict)

    @property
    def total_lines(self) -> int:
        return len(self.aligned_lines)

    @property
    def variant_count(self) -> int:
        return sum(1 for v in self.variation_units if v.is_variant)

    @property
    def unanimous_count(self) -> int:
        return sum(1 for v in self.variation_units if not v.is_variant)


@dataclass
class StemmaNode:
    """A node in the stemma tree."""
    label: str
    role: WitnessRole = WitnessRole.TERMINAL
    children: list["StemmaNode"] = field(default_factory=list)
    parent: Optional["StemmaNode"] = None
    readings: dict[int, str] = field(default_factory=dict)  # line_num -> reading
    annotation: str = ""

    def add_child(self, child: "StemmaNode") -> None:
        child.parent = self
        self.children.append(child)


@dataclass
class StemmaTree:
    """The reconstructed family tree of code variants."""
    root: Optional[StemmaNode] = None
    nodes: list[StemmaNode] = field(default_factory=list)
    contaminated: list[str] = field(default_factory=list)

    def find_node(self, label: str) -> Optional[StemmaNode]:
        for node in self.nodes:
            if node.label == label:
                return node
        return None

    @property
    def terminal_nodes(self) -> list[StemmaNode]:
        return [n for n in self.nodes if n.role == WitnessRole.TERMINAL]

    @property
    def archetype(self) -> Optional[StemmaNode]:
        for n in self.nodes:
            if n.role == WitnessRole.ARCHETYPE:
                return n
        return None


@dataclass
class ContaminationReport:
    """Report on a contaminated witness."""
    witness: str
    primary_lineage: str = ""
    contaminating_source: str = ""
    mixing_pattern: str = ""
    likelihood: str = ""


@dataclass
class ArchetypeResult:
    """Result of archetype reconstruction."""
    lines: list[str] = field(default_factory=list)
    annotations: dict[int, str] = field(default_factory=dict)
    confidence: float = 0.0
    method: str = "Lachmannian"


def normalize_line(line: str) -> str:
    """Normalize a code line for comparison: strip comments, extra whitespace."""
    # Strip inline comments
    stripped = line.split("#")[0] if "#" in line else line
    # Normalize whitespace
    stripped = " ".join(stripped.split())
    return stripped.strip()
