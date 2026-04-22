"""Stratigraphic data model — mapping git concepts to geological metaphors.

Core dataclasses:
- Stratum: a commit with geological metadata
- Intrusion: a branch that merged in
- Unconformity: a gap in history (rebase, squash, orphan)
- FaultLine: a force push or history rewrite
- Fossil: a deleted code artifact preserved in historical strata
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple


class MineralType(enum.Enum):
    """File type → mineral composition mapping."""
    PYTHON = "pyrite"
    JAVASCRIPT = "fluorite"
    TYPESCRIPT = "topaz"
    RUST = "hematite"
    GO = "quartz"
    C = "graphite"
    CPP = "obsidian"
    JAVA = "granite"
    RUBY = "garnet"
    MARKDOWN = "limestone"
    YAML = "shale"
    JSON = "calcite"
    HTML = "sandstone"
    CSS = "marble"
    SHELL = "pumice"
    SQL = "halite"
    OTHER = "clay"


class IntrusionType(enum.Enum):
    """Type of branch intrusion."""
    IGNEOUS = "igneous"      # fast/hot branch (many commits in short time)
    SEDIMENTARY = "sedimentary"  # slow/gradual branch


class UnconformityType(enum.Enum):
    """Type of history gap."""
    REBASE = "rebase"
    SQUASH = "squash"
    CHERRY_PICK = "cherry_pick"
    ORPHAN = "orphan"
    FORCE_PUSH = "force_push"


class StabilityTier(enum.Enum):
    """Stability classification for a stratum."""
    BEDROCK = "bedrock"        # very stable, old, unchanged
    MATURE = "mature"          # well-established
    SETTLING = "settling"      # recently changed, stabilizing
    ACTIVE = "active"          # actively being modified
    VOLATILE = "volatile"      # frequently changing


# Mapping from file extensions to MineralType
_EXTENSION_MINERAL_MAP: dict[str, MineralType] = {
    ".py": MineralType.PYTHON,
    ".js": MineralType.JAVASCRIPT,
    ".jsx": MineralType.JAVASCRIPT,
    ".ts": MineralType.TYPESCRIPT,
    ".tsx": MineralType.TYPESCRIPT,
    ".rs": MineralType.RUST,
    ".go": MineralType.GO,
    ".c": MineralType.C,
    ".h": MineralType.C,
    ".cpp": MineralType.CPP,
    ".cc": MineralType.CPP,
    ".cxx": MineralType.CPP,
    ".hpp": MineralType.CPP,
    ".java": MineralType.JAVA,
    ".rb": MineralType.RUBY,
    ".md": MineralType.MARKDOWN,
    ".rst": MineralType.MARKDOWN,
    ".yml": MineralType.YAML,
    ".yaml": MineralType.YAML,
    ".json": MineralType.JSON,
    ".html": MineralType.HTML,
    ".htm": MineralType.HTML,
    ".css": MineralType.CSS,
    ".scss": MineralType.CSS,
    ".sh": MineralType.SHELL,
    ".bash": MineralType.SHELL,
    ".zsh": MineralType.SHELL,
    ".sql": MineralType.SQL,
}


def extension_to_mineral(ext: str) -> MineralType:
    """Map a file extension to a mineral type."""
    return _EXTENSION_MINERAL_MAP.get(ext.lower(), MineralType.OTHER)


@dataclass
class Stratum:
    """A single stratum (commit) with geological metadata.

    Represents one layer in the geological cross-section of the repository.
    Law of Superposition: deeper strata are older.
    """
    commit_hash: str
    author: str
    date: datetime
    message: str
    parent_hashes: List[str] = field(default_factory=list)
    lines_added: int = 0
    lines_deleted: int = 0
    files_changed: List[str] = field(default_factory=list)
    branch_name: str = ""

    # Geological metadata (auto-computed in __post_init__)
    density: float = 0.0
    minerals: List[MineralType] = field(default_factory=list)
    thickness: float = 0.0
    stability_tier: str = ""

    def __post_init__(self) -> None:
        # Density = complexity proxy (ratio of changes to files)
        if self.files_changed:
            self.density = (self.lines_added + self.lines_deleted) / len(self.files_changed)
        # Minerals from file extensions
        self.minerals = [extension_to_mineral(_ext_of(f)) for f in self.files_changed]
        # Thickness proportional to total lines changed
        self.thickness = max(0.1, (self.lines_added + self.lines_deleted) / 10.0)

    @property
    def mineral_composition(self) -> dict[str, int]:
        """Return a mineral → count mapping."""
        comp: dict[str, int] = {}
        for m in self.minerals:
            comp[m.value] = comp.get(m.value, 0) + 1
        return comp

    @property
    def is_merge(self) -> bool:
        return len(self.parent_hashes) > 1


@dataclass
class Intrusion:
    """A branch intrusion — igneous or sedimentary vein through strata."""
    branch_name: str
    intrusion_type: IntrusionType = IntrusionType.IGNEOUS
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    commit_count: int = 0
    strata: List[Stratum] = field(default_factory=list)

    @property
    def duration_hours(self) -> float:
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).total_seconds() / 3600.0
        return 0.0

    @property
    def commits_per_hour(self) -> float:
        if self.duration_hours > 0:
            return self.commit_count / self.duration_hours
        return 0.0


@dataclass
class Unconformity:
    """A gap in the geological record — missing history."""
    unconformity_type: UnconformityType
    description: str = ""
    commit_hash: str = ""
    date: Optional[datetime] = None
    confidence: float = 1.0  # how confident we are this is a real unconformity

    @property
    def severity(self) -> str:
        if self.confidence >= 0.8:
            return "major"
        elif self.confidence >= 0.5:
            return "moderate"
        return "minor"


@dataclass
class FaultLine:
    """A fault line — history rewrite or force push."""
    ref_name: str
    old_hash: str = ""
    new_hash: str = ""
    date: Optional[datetime] = None
    description: str = ""
    severity: float = 1.0

    @property
    def severity_label(self) -> str:
        if self.severity >= 0.8:
            return "catastrophic"
        elif self.severity >= 0.5:
            return "major"
        return "minor"


@dataclass
class Fossil:
    """A fossil — deleted code artifact preserved in historical strata.

    Like a real fossil, this represents a living thing (function, class,
    variable) that once existed but is now preserved only in the rock
    record (git history).
    """
    name: str
    kind: str  # "function", "class", "variable", "import"
    file_path: str
    deposited_hash: str  # commit where it was first added
    deposited_date: Optional[datetime] = None
    extinct_hash: str = ""  # commit where it was deleted
    extinct_date: Optional[datetime] = None
    content: str = ""

    @property
    def lifespan_days(self) -> float:
        """How long this artifact lived before going extinct."""
        if self.deposited_date and self.extinct_date:
            return (self.extinct_date - self.deposited_date).total_seconds() / 86400.0
        return -1.0  # still alive or dates unknown

    @property
    def is_extinct(self) -> bool:
        return bool(self.extinct_hash)


@dataclass
class GeologicalReport:
    """Summary geological report of a repository."""
    repo_path: str = ""
    age_days: float = 0.0
    total_strata: int = 0
    total_intrusions: int = 0
    unconformity_count: int = 0
    fossil_count: int = 0
    fault_count: int = 0
    mineral_composition: dict[str, int] = field(default_factory=dict)
    stability_breakdown: dict[str, int] = field(default_factory=dict)
    strata: List[Stratum] = field(default_factory=list)
    intrusions: List[Intrusion] = field(default_factory=list)
    unconformities: List[Unconformity] = field(default_factory=list)
    fossils: List[Fossil] = field(default_factory=list)
    faults: List[FaultLine] = field(default_factory=list)

    @property
    def fossil_density(self) -> float:
        """Fossils per 1000 lines of history."""
        if self.total_strata > 0:
            return (self.fossil_count / self.total_strata) * 1000
        return 0.0

    @property
    def dominant_mineral(self) -> str:
        if self.mineral_composition:
            return max(self.mineral_composition, key=self.mineral_composition.get)
        return "unknown"


def _ext_of(filepath: str) -> str:
    """Extract extension from a file path, including the dot."""
    import os
    _, ext = os.path.splitext(filepath)
    return ext
