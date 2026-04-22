"""Data models for Crystallo structural analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class SymmetryType(Enum):
    """Crystallographic symmetry operation types mapped to code relationships."""

    ROTATIONAL = auto()      # Same structure, different roles (e.g. create_user / create_order)
    REFLECTION = auto()      # Mirror-image modules (e.g. client / server)
    TRANSLATIONAL = auto()   # Repeated pattern across files (e.g. boilerplate)
    GLIDE = auto()           # Repeated with transformation (e.g. test_*.py ↔ *.py)
    BROKEN = auto()          # Expected symmetry but divergence found
    NONE = auto()            # No significant symmetry


class SymmetryIntent(Enum):
    """Whether the detected symmetry is intentional, accidental, or expected."""

    INTENTIONAL = auto()   # Shared abstraction explains symmetry
    ACCIDENTAL = auto()    # Copy-paste duplication without shared abstraction
    EXPECTED = auto()      # Convention-driven (e.g. test mirrors)
    BROKEN = auto()        # Symmetry should exist but doesn't
    UNKNOWN = auto()       # Cannot determine intent


class SpaceGroup(Enum):
    """Simplified crystallographic space groups for code structure classification.

    Analogy:
      - P1 (triclinic):   lowest symmetry, every unit unique
      - Pm (monoclinic):  single reflection symmetry axis
      - P2 (monoclinic):  single rotational symmetry axis
      - P2/m:             rotational + reflection combined
      - P4 (tetragonal):  4-fold rotational symmetry
      - P6 (hexagonal):   high translational repetition
      - Pa3 (cubic):      complex multi-axis, well-architected
    """

    P1 = "P1"          # triclinic
    Pm = "Pm"          # monoclinic — reflection
    P2 = "P2"          # monoclinic — rotation
    P2m = "P2/m"       # monoclinic — combined
    P4 = "P4"          # tetragonal
    P6 = "P6"          # hexagonal
    Pa3 = "Pa3"        # cubic


@dataclass
class StructuralFeature:
    """A single feature extracted from a code unit."""

    name: str
    value: float
    category: str = "general"  # e.g. "method", "attribute", "signature", "call"


@dataclass
class MethodSignature:
    """Lightweight representation of a method signature."""

    name: str
    arg_count: int = 0
    has_return_annotation: bool = False
    is_async: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    decorator_names: list[str] = field(default_factory=list)


@dataclass
class StructuralFingerprint:
    """Feature-vector fingerprint of a code unit (class or function).

    Computed via __post_init__ from raw features. All auto-computed fields
    have defaults so the dataclass can be instantiated without them.
    """

    name: str
    file_path: str = ""
    kind: str = "class"  # "class" or "function"
    method_names: list[str] = field(default_factory=list)
    method_signatures: list[MethodSignature] = field(default_factory=list)
    attribute_names: list[str] = field(default_factory=list)
    base_classes: list[str] = field(default_factory=list)
    decorator_names: list[str] = field(default_factory=list)
    function_count: int = 0
    class_count: int = 0
    has_init: bool = False
    is_abstract: bool = False
    is_async: bool = False
    # --- auto-computed fields ---
    feature_vector: list[float] = field(default_factory=list)
    method_set: set[str] = field(default_factory=set)
    attribute_set: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.method_set = set(self.method_names)
        self.attribute_set = set(self.attribute_names)
        if not self.feature_vector:
            self.feature_vector = self._compute_feature_vector()

    def _compute_feature_vector(self) -> list[float]:
        """Build a fixed-length numerical feature vector for similarity comparison."""
        vec: list[float] = [
            len(self.method_names),
            len(self.attribute_names),
            len(self.base_classes),
            len(self.decorator_names),
            float(self.has_init),
            float(self.is_abstract),
            float(self.is_async) if self.kind == "function" else 0.0,
            sum(1 for s in self.method_signatures if s.has_return_annotation),
            sum(1 for s in self.method_signatures if s.is_async),
            sum(1 for s in self.method_signatures if s.is_classmethod),
            sum(1 for s in self.method_signatures if s.is_staticmethod),
            float(self.function_count),
            float(self.class_count),
            sum(s.arg_count for s in self.method_signatures),
            sum(len(s.decorator_names) for s in self.method_signatures),
        ]
        return vec


@dataclass
class SymmetryRelation:
    """A detected symmetry relationship between two code units."""

    source: str
    target: str
    symmetry_type: SymmetryType = SymmetryType.NONE
    intent: SymmetryIntent = SymmetryIntent.UNKNOWN
    similarity: float = 0.0
    confidence: float = 0.0
    missing_in_source: list[str] = field(default_factory=list)
    missing_in_target: list[str] = field(default_factory=list)
    extra_in_source: list[str] = field(default_factory=list)
    extra_in_target: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class UnitCell:
    """A repeating structural pattern (the 'unit cell' of the codebase)."""

    representative_name: str
    member_names: list[str] = field(default_factory=list)
    member_fingerprints: list[StructuralFingerprint] = field(default_factory=list)
    symmetry_type: SymmetryType = SymmetryType.NONE
    space_group: SpaceGroup = SpaceGroup.P1
    # auto-computed
    member_count: int = 0
    avg_similarity: float = 0.0

    def __post_init__(self) -> None:
        self.member_count = len(self.member_names)


@dataclass
class DefectReport:
    """A broken-symmetry or accidental-symmetry defect."""

    file_path: str
    unit_name: str
    expected_symmetry_with: str = ""
    defect_type: str = "broken"  # "broken" or "accidental"
    missing_features: list[str] = field(default_factory=list)
    extra_features: list[str] = field(default_factory=list)
    confidence: float = 0.0
    suggestion: str = ""


@dataclass
class ModuleClassification:
    """Space-group classification for a directory/module."""

    path: str
    space_group: SpaceGroup = SpaceGroup.P1
    symmetry_description: str = ""
    fingerprint_count: int = 0
    rotational_pairs: int = 0
    reflection_pairs: int = 0
    translational_groups: int = 0
    broken_count: int = 0
