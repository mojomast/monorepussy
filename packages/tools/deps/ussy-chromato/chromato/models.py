"""Core data models for Chromato."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


class PeakShape(enum.Enum):
    """Peak shape classifications for dependency health diagnosis."""

    NARROW_TALL = "narrow_tall"      # Focused + popular (healthy)
    WIDE_SHORT = "wide_short"        # Bloated: does too much
    SHOULDER = "shoulder"            # Transition: version split
    TAILING = "tailing"              # Drag: backward compat burden
    SYMMETRIC = "symmetric"          # Normal


class EntanglementKind(enum.Enum):
    """Types of dependency entanglement detected via co-elution."""

    CIRCULAR = "circular"            # Circular dependency
    CONFLICT = "conflict"            # Version conflict
    MUTUAL = "mutual"                # Mutual coupling


class Solvent(enum.Enum):
    """Analysis solvents (gradient elution modes)."""

    COUPLING = "coupling"            # Separates by import coupling strength
    RISK = "risk"                    # Separates by vulnerability/advisory count
    FRESHNESS = "freshness"          # Separates by last-update recency
    LICENSE = "license"              # Separates by license compatibility


# License restrictiveness scale (0 = permissive, high = restrictive)
LICENSE_RESTRICTIVENESS: dict[str, float] = {
    "MIT": 0.1,
    "Apache-2.0": 0.2,
    "BSD-2-Clause": 0.1,
    "BSD-3-Clause": 0.15,
    "ISC": 0.1,
    "0BSD": 0.1,
    "Unlicense": 0.0,
    "LGPL-2.1": 0.5,
    "LGPL-3.0": 0.5,
    "MPL-2.0": 0.4,
    "EPL-1.0": 0.45,
    "GPL-2.0": 0.8,
    "GPL-3.0": 0.8,
    "AGPL-3.0": 0.9,
    "SSPL-1.0": 0.95,
    "BSL-1.1": 0.9,
    "Proprietary": 1.0,
    "Commercial": 1.0,
    "UNKNOWN": 0.6,
}


@dataclass
class Dependency:
    """A single dependency (analogous to a chemical analyte)."""

    name: str
    version: str = "0.0.0"
    license: str = "UNKNOWN"
    advisory_count: int = 0
    last_updated: Optional[datetime] = None
    concerns: int = 1                    # Number of distinct purposes/concerns
    is_dev: bool = False                 # Dev-only dependency?
    is_optional: bool = False            # Optional dependency?
    has_major_version_gap: bool = False  # Version split across majors?
    has_deprecated_apis: bool = False    # Backward-compat drag?
    dependents: list[str] = field(default_factory=list)  # What depends on this

    @property
    def dependent_count(self) -> int:
        return len(self.dependents)

    def days_since_update(self) -> float:
        """Days since last update. Returns 9999 if unknown."""
        if self.last_updated is None:
            return 9999.0
        now = datetime.now(timezone.utc)
        delta = now - self.last_updated
        return max(0.0, delta.total_seconds() / 86400.0)


@dataclass
class DependencyGraph:
    """The full dependency graph (analogous to the chemical mixture)."""

    dependencies: list[Dependency] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)  # (from, to) dependency edges

    def get(self, name: str) -> Optional[Dependency]:
        """Look up a dependency by name."""
        for dep in self.dependencies:
            if dep.name == name:
                return dep
        return None

    def coupling_depth(self, dep: Dependency) -> int:
        """Compute how deeply coupled a dependency is (transitive depth)."""
        visited: set[str] = set()
        return self._coupling_depth_impl(dep.name, visited)

    def _coupling_depth_impl(self, name: str, visited: set[str]) -> int:
        """Recursive coupling depth computation."""
        if name in visited:
            return 0
        visited.add(name)
        children = [to for frm, to in self.edges if frm == name]
        if not children:
            return 0
        return 1 + max(self._coupling_depth_impl(c, visited) for c in children)

    def dependent_count(self, dep: Dependency) -> int:
        """Count how many dependencies depend on this one."""
        return sum(1 for frm, to in self.edges if to == dep.name)

    def has_circular(self, dep_a: str, dep_b: str) -> bool:
        """Check if two dependencies form a circular reference."""
        return self._has_path(dep_a, dep_b) and self._has_path(dep_b, dep_a)

    def _has_path(self, start: str, target: str, visited: Optional[set[str]] = None) -> bool:
        """DFS path check."""
        if visited is None:
            visited = set()
        if start == target:
            return True
        if start in visited:
            return False
        visited.add(start)
        for frm, to in self.edges:
            if frm == start and self._has_path(to, target, visited):
                return True
        return False


@dataclass
class Peak:
    """A peak in the chromatogram representing a dependency cluster."""

    dep: Dependency
    retention_time: float = 0.0
    area: float = 0.0       # Dependency "mass"
    width: float = 0.0      # Dependency "purity" (narrow = focused)
    height: float = 0.0
    shape: PeakShape = PeakShape.SYMMETRIC


@dataclass
class Coelution:
    """Two overlapping peaks = entangled dependencies."""

    dep_a: Dependency
    dep_b: Dependency
    overlap: float = 0.0
    kind: EntanglementKind = EntanglementKind.MUTUAL


@dataclass
class ChromatogramResult:
    """Complete chromatogram result from a scan."""

    source: str = ""
    solvent: Solvent = Solvent.COUPLING
    peaks: list[Peak] = field(default_factory=list)
    coelutions: list[Coelution] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
