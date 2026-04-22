"""Data models for Operon gene-regulation documentation system."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any


class MarkType(Enum):
    """Types of epigenetic marks."""

    METHYLATION = "methylation"
    ACETYLATION = "acetylation"
    CHROMATIN_REMODELING = "chromatin_remodeling"


class RepressorType(Enum):
    """Types of repressors."""

    CONSTITUTIVE = "constitutive"
    INDUCIBLE = "inducible"
    COREPRESSOR_DEPENDENT = "corepressor_dependent"


class FactorType(Enum):
    """Types of transcription factors."""

    ACTIVATOR = "activator"
    REPRESSOR = "repressor"


@dataclass
class Gene:
    """A gene represents a module or feature in the codebase."""

    name: str
    path: str
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    docstring: str = ""
    is_public: bool = True
    is_deprecated: bool = False
    is_internal: bool = False
    lines_of_code: int = 0

    def __hash__(self) -> int:
        return hash(self.path)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Gene):
            return NotImplemented
        return self.path == other.path

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Operon:
    """An operon is a cluster of co-regulated genes (modules)."""

    operon_id: str
    genes: list[Gene] = field(default_factory=list)
    promoter_region: list[str] = field(default_factory=list)
    operator_sites: list[str] = field(default_factory=list)
    polycistronic: bool = False
    regulatory_proteins: list[str] = field(default_factory=list)
    coupling_score: float = 0.0

    def __post_init__(self) -> None:
        if not self.polycistronic:
            self.polycistronic = len(self.genes) > 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "operon_id": self.operon_id,
            "genes": [g.to_dict() for g in self.genes],
            "promoter_region": self.promoter_region,
            "operator_sites": self.operator_sites,
            "polycistronic": self.polycistronic,
            "regulatory_proteins": self.regulatory_proteins,
            "coupling_score": self.coupling_score,
        }


@dataclass
class Promoter:
    """A promoter triggers documentation generation."""

    promoter_id: str
    trigger_type: str
    strength: float = 0.0
    rnap_binding: list[str] = field(default_factory=list)
    transcription_rate: float | str = 0.0
    target_operon: str = ""
    sigma_factor: list[str] = field(default_factory=list)
    upstream_activators: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Repressor:
    """A repressor suppresses documentation generation."""

    repressor_id: str
    repressor_type: RepressorType
    operator_site: str = ""
    repressor_protein: str = ""
    inducer: str = ""
    corepressor: str = ""
    allosteric_state: str = "active"
    repression_level: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "repressor_id": self.repressor_id,
            "repressor_type": self.repressor_type.value,
            "operator_site": self.operator_site,
            "repressor_protein": self.repressor_protein,
            "inducer": self.inducer,
            "corepressor": self.corepressor,
            "allosteric_state": self.allosteric_state,
            "repression_level": self.repression_level,
        }


@dataclass
class Enhancer:
    """An enhancer boosts cross-references between distant modules."""

    enhancer_id: str
    source_gene: str
    target_gene: str
    target_operon: str = ""
    distance_kb: float = 0.0
    orientation: str = "forward"
    enhancer_strength: float = 0.0
    transcription_factors_required: list[str] = field(default_factory=list)
    tissue_specificity: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TranscriptionFactor:
    """A transcription factor controls conditional doc inclusion."""

    factor_id: str
    name: str
    factor_type: FactorType
    binding_motif: list[str] = field(default_factory=list)
    target_operons: list[str] = field(default_factory=list)
    excludes: list[str] = field(default_factory=list)
    coactivators_required: list[str] = field(default_factory=list)
    corepressors_lifted: list[str] = field(default_factory=list)
    conditional_expression: str = ""
    repression_scope: list[str] = field(default_factory=list)
    strength: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "name": self.name,
            "factor_type": self.factor_type.value,
            "binding_motif": self.binding_motif,
            "target_operons": self.target_operons,
            "excludes": self.excludes,
            "coactivators_required": self.coactivators_required,
            "corepressors_lifted": self.corepressors_lifted,
            "conditional_expression": self.conditional_expression,
            "repression_scope": self.repression_scope,
            "strength": self.strength,
        }


@dataclass
class EpigeneticMark:
    """An epigenetic mark tracks documentation state across generations."""

    mark_id: str
    operon_id: str
    mark_type: MarkType
    position: str = ""
    inheritance: str = "stable"
    effect: str = ""
    level: float = 0.0
    deacetylase_risk: bool = False
    change: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "mark_id": self.mark_id,
            "operon_id": self.operon_id,
            "mark_type": self.mark_type.value,
            "position": self.position,
            "inheritance": self.inheritance,
            "effect": self.effect,
            "level": self.level,
            "deacetylase_risk": self.deacetylase_risk,
            "change": self.change,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Codebase:
    """Represents a codebase to be analyzed."""

    root_path: str
    genes: list[Gene] = field(default_factory=list)
    operons: list[Operon] = field(default_factory=list)
    deprecated_features: list[Gene] = field(default_factory=list)
    internal_apis: list[Gene] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_path": self.root_path,
            "genes": [g.to_dict() for g in self.genes],
            "operons": [o.to_dict() for o in self.operons],
            "deprecated_features": [g.to_dict() for g in self.deprecated_features],
            "internal_apis": [g.to_dict() for g in self.internal_apis],
        }


def serialize_to_json(obj: Any) -> str:
    """Serialize an object or list of objects to JSON."""
    if isinstance(obj, list):
        return json.dumps([item.to_dict() if hasattr(item, "to_dict") else item for item in obj], indent=2)
    if hasattr(obj, "to_dict"):
        return json.dumps(obj.to_dict(), indent=2)
    return json.dumps(obj, indent=2)
