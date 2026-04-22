"""Core data models for Endemic."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class PatternType(Enum):
    """Whether a pattern is a bad code smell or a good practice."""
    BAD = "bad"
    GOOD = "good"


class PatternStatus(Enum):
    """Epidemiological status of a pattern in the codebase."""
    SPREADING = "SPREADING"
    ENDEMIC = "ENDEMIC"
    DYING = "DYING"
    ELIMINATED = "ELIMINATED"


class Compartment(Enum):
    """SIR compartment for a module."""
    SUSCEPTIBLE = "S"
    INFECTED = "I"
    RECOVERED = "R"


class TransmissionVector(Enum):
    """How a pattern was transmitted between modules."""
    COPY_PASTE = "copy_paste"
    DEVELOPER_HABIT = "developer_habit"
    TEMPLATE_CODEGEN = "template_codegen"
    SHARED_MODULE = "shared_module"
    UNKNOWN = "unknown"


@dataclass
class Pattern:
    """A code pattern that can propagate through a codebase."""
    name: str
    pattern_type: PatternType = PatternType.BAD
    description: str = ""
    regex_pattern: str = ""
    r0: float = 0.0
    status: PatternStatus = PatternStatus.DYING
    prevalence_count: int = 0
    total_modules: int = 0
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(self.name.encode()).hexdigest()[:12]

    @property
    def prevalence_ratio(self) -> float:
        """Fraction of modules infected."""
        if self.total_modules == 0:
            return 0.0
        return self.prevalence_count / self.total_modules

    @property
    def is_spreading(self) -> bool:
        return self.r0 > 1.0


@dataclass
class Module:
    """A source code module in the repository."""
    path: str
    language: str = "python"
    domain: str = ""
    compartment: Compartment = Compartment.SUSCEPTIBLE
    patterns: list[str] = field(default_factory=list)
    developer_traffic: int = 0
    dependents: int = 0

    @property
    def filename(self) -> str:
        return self.path.rsplit("/", 1)[-1] if "/" in self.path else self.path

    @property
    def directory(self) -> str:
        return self.path.rsplit("/", 1)[0] if "/" in self.path else ""


@dataclass
class TransmissionEvent:
    """A single transmission of a pattern from one module to another."""
    pattern_name: str
    source_module: str
    target_module: str
    vector: TransmissionVector = TransmissionVector.UNKNOWN
    developer: str = ""
    timestamp: Optional[datetime] = None
    commit_hash: str = ""
    pr_number: Optional[int] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class TransmissionTree:
    """Tree representing the transmission history of a pattern."""
    pattern_name: str
    index_case: str = ""
    index_developer: str = ""
    index_timestamp: Optional[datetime] = None
    events: list[TransmissionEvent] = field(default_factory=list)

    def add_event(self, event: TransmissionEvent):
        self.events.append(event)

    @property
    def infected_modules(self) -> set[str]:
        modules = set()
        for e in self.events:
            modules.add(e.target_module)
            modules.add(e.source_module)
        return modules

    @property
    def generation_time_weeks(self) -> float:
        """Average time from infection to first transmission to a new module."""
        if not self.events:
            return 0.0
        # Group events by source module, find time gaps
        source_times: dict[str, list[datetime]] = {}
        for e in self.events:
            if e.source_module not in source_times:
                source_times[e.source_module] = []
            if e.timestamp:
                source_times[e.source_module].append(e.timestamp)

        if not source_times:
            return 0.0

        deltas = []
        for module, times in source_times.items():
            if len(times) >= 2:
                sorted_times = sorted(times)
                for i in range(1, len(sorted_times)):
                    delta = (sorted_times[i] - sorted_times[i - 1]).days / 7.0
                    deltas.append(delta)

        if not deltas:
            return 0.0
        return sum(deltas) / len(deltas)

    @property
    def vector_counts(self) -> dict[TransmissionVector, int]:
        counts: dict[TransmissionVector, int] = {}
        for e in self.events:
            counts[e.vector] = counts.get(e.vector, 0) + 1
        return counts


@dataclass
class DeveloperStats:
    """Statistics about a developer's role in pattern propagation."""
    email: str
    infections_caused: int = 0
    modules_infected: list[str] = field(default_factory=list)
    patterns_introduced: list[str] = field(default_factory=list)
    is_superspreader: bool = False

    @property
    def infection_count(self) -> int:
        return len(self.modules_infected)


@dataclass
class SIRState:
    """State of the SIR model at a given time step."""
    time: float
    s: int  # susceptible count
    i: int  # infected count
    r: int  # recovered count

    @property
    def n(self) -> int:
        return self.s + self.i + self.r


@dataclass
class SIRSimulation:
    """Results of an SIR simulation."""
    pattern_name: str
    r0: float
    beta: float
    gamma: float
    n: int
    states: list[SIRState] = field(default_factory=list)
    peak_infected: int = 0
    peak_time: float = 0.0
    final_infected: int = 0

    def __post_init__(self):
        if self.states and self.peak_infected == 0:
            peak_state = max(self.states, key=lambda s: s.i)
            self.peak_infected = peak_state.i
            self.peak_time = peak_state.time
            self.final_infected = self.states[-1].i if self.states else 0


@dataclass
class HerdImmunityResult:
    """Results of herd immunity calculation."""
    pattern_name: str
    r0: float
    threshold: float  # fraction needed for herd immunity
    current_immune_count: int = 0
    total_modules: int = 0
    modules_to_vaccinate: int = 0

    @property
    def threshold_pct(self) -> float:
        return self.threshold * 100

    @property
    def current_immune_pct(self) -> float:
        if self.total_modules == 0:
            return 0.0
        return (self.current_immune_count / self.total_modules) * 100

    @property
    def gap_pct(self) -> float:
        return max(0.0, self.threshold_pct - self.current_immune_pct)


@dataclass
class VaccinationStrategy:
    """A recommended refactoring action."""
    target: str  # module, developer, or area
    action: str
    prevented_infections: int = 0
    effort_hours: float = 0.0
    equivalent_random_vaccinations: int = 0
    rank: int = 1


@dataclass
class ZoonoticJump:
    """A pattern crossing an architectural boundary."""
    pattern_name: str
    origin_domain: str
    target_domain: str
    origin_module: str
    target_module: str
    vector: str = ""
    risk: str = "MEDIUM"
    recommendation: str = ""
    is_appropriate_in_origin: bool = True


@dataclass
class PromoteResult:
    """Result of good pathogen promotion analysis."""
    pattern_name: str
    current_r0: float
    current_prevalence: int = 0
    total_modules: int = 0
    optimal_seed_module: str = ""
    predicted_r0_increase: float = 0.0
    time_to_80pct_weeks: float = 0.0
    time_to_80pct_without_seeding_weeks: float = 0.0
    cross_protection: dict[str, float] = field(default_factory=dict)
