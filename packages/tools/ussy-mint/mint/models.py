"""Data models for Mint — numismatic package provenance system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Optional


class ProvenanceLevel(IntEnum):
    """Provenance verification level."""
    UNVERIFIED = 0      # No signatures, no build metadata
    BUILD_SIGNED = 1    # Artifact hash matches a signed build record
    SOURCE_LINKED = 2   # Build record links to a specific source commit
    END_TO_END = 3      # Full chain of custody verified


@dataclass
class MintMark:
    """Provenance identifier for a package version — like a mint mark on a coin."""
    registry: str = "unknown"
    publisher: str = "unknown"
    publisher_key: str = ""
    build_signature: str = ""
    artifact_hash: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    distribution_path: str = "unknown"  # direct, transitive, workspace


@dataclass
class DieVariety:
    """Build variant of a specific package version."""
    version: str = ""
    platform: str = "unknown"
    variant_hash: str = ""
    build_env: dict = field(default_factory=dict)
    optional_deps: list = field(default_factory=list)


@dataclass
class Composition:
    """Dependency alloy composition of a package — like metal composition of a coin."""
    own_code_ratio: float = 1.0
    transitive_depth: int = 0
    transitive_count: int = 0
    alloy_breakdown: dict = field(default_factory=dict)
    maintainer_overlap: float = 0.0
    license_mix: dict = field(default_factory=dict)


@dataclass
class DebasementCurve:
    """Track quality degradation of a package over versions."""
    package: str = ""
    versions: list = field(default_factory=list)  # list of (version, grade, datetime)
    debasement_rate: float = 0.0
    projected_zero_date: Optional[datetime] = None
    recoinage_events: list = field(default_factory=list)  # indices where grade jumped up


@dataclass
class Hoard:
    """A dependency cluster — like a coin hoard revealing trade patterns."""
    name: str = ""
    packages: list = field(default_factory=list)
    co_occurrence: float = 0.0
    common_maintainers: list = field(default_factory=list)
    total_fineness: float = 0.0
    max_debasement: float = 0.0
    contamination_risk: float = 0.0


@dataclass
class ProvenanceLink:
    """A single step in the chain of custody."""
    source: str = ""
    actor: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signature: str = ""
    verified: bool = False


@dataclass
class ProvenanceChain:
    """Full chain of custody for a package version."""
    package: str = ""
    chain: list = field(default_factory=list)  # list of ProvenanceLink


@dataclass
class PackageInfo:
    """Composite information about a package version for grading."""
    name: str = ""
    version: str = ""
    mint_mark: MintMark = field(default_factory=MintMark)
    die_variety: DieVariety = field(default_factory=DieVariety)
    composition: Composition = field(default_factory=Composition)
    provenance_chain: ProvenanceChain = field(default_factory=ProvenanceChain)

    # Grading criteria inputs (0.0 - 1.0)
    strike_quality: float = 0.5
    surface_preservation: float = 0.5
    luster: float = 0.5
    eye_appeal: float = 0.5

    # Computed
    sheldon_grade: int = 0
    grade_label: str = ""


# Grade label mapping
GRADE_LABELS = [
    (1, "P-1", "Poor"),
    (2, "FA-2", "Fair"),
    (3, "AG-3", "About Good"),
    (4, "G-4", "Good"),
    (6, "G-6", "Good"),
    (8, "VG-8", "Very Good"),
    (10, "VG-10", "Very Good"),
    (12, "F-12", "Fine"),
    (15, "F-15", "Fine"),
    (20, "VF-20", "Very Fine"),
    (25, "VF-25", "Very Fine"),
    (30, "VF-30", "Very Fine"),
    (35, "VF-35", "Very Fine"),
    (40, "XF-40", "Extremely Fine"),
    (45, "XF-45", "Extremely Fine"),
    (50, "AU-50", "About Uncirculated"),
    (53, "AU-53", "About Uncirculated"),
    (55, "AU-55", "About Uncirculated"),
    (58, "AU-58", "About Uncirculated"),
    (60, "MS-60", "Mint State"),
    (61, "MS-61", "Mint State"),
    (62, "MS-62", "Mint State"),
    (63, "MS-63", "Mint State"),
    (64, "MS-64", "Mint State"),
    (65, "MS-65", "Mint State"),
    (66, "MS-66", "Mint State"),
    (67, "MS-67", "Mint State"),
    (68, "MS-68", "Mint State"),
    (69, "MS-69", "Mint State"),
    (70, "MS-70", "Mint State"),
]


def get_grade_label(grade: int) -> tuple[str, str]:
    """Get the numismatic label for a Sheldon grade.

    Returns (short_label, description) e.g. ("MS-65", "Mint State").
    """
    best = ("P-1", "Poor")
    for g, short, desc in GRADE_LABELS:
        if grade >= g:
            best = (short, desc)
        else:
            break
    return best


def get_grade_category(grade: int) -> str:
    """Get broad grade category string."""
    if grade >= 60:
        return "Mint State"
    elif grade >= 50:
        return "About Uncirculated"
    elif grade >= 40:
        return "Extremely Fine"
    elif grade >= 20:
        return "Very Fine"
    elif grade >= 12:
        return "Fine"
    elif grade >= 8:
        return "Very Good"
    elif grade >= 4:
        return "Good"
    elif grade >= 3:
        return "About Good"
    elif grade >= 2:
        return "Fair"
    else:
        return "Poor"
