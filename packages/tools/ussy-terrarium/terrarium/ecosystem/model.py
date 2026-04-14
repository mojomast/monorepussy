"""Ecosystem model — maps metrics to biological properties."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..metrics.models import ModuleMetrics, ProjectMetrics
from .organisms import (
    OrganismType, Vitality, ROLE_TO_ORGANISM,
    health_to_vitality, get_emoji, VITALITY_COLORS, ANSI_RESET, ANSI_BOLD,
)


# Health score weights
CHURN_PENALTY_WEIGHT = 0.25
COMPLEXITY_PENALTY_WEIGHT = 0.20
COVERAGE_BONUS_WEIGHT = 0.20
BUG_PENALTY_WEIGHT = 0.15
STABILITY_BONUS_WEIGHT = 0.10
DEAD_PENALTY_WEIGHT = 0.10

# Thresholds
COMPLEXITY_THRESHOLD = 15
CHURN_THRESHOLD = 5.0  # commits per month
COVERAGE_THRESHOLD = 0.80


@dataclass
class Organism:
    """A living organism representing a code module."""

    path: str
    organism_type: OrganismType = OrganismType.BUSH
    health: float = 0.0
    vitality: Vitality = Vitality.HEALTHY
    stability_tier: str = ""
    age_tier: str = ""
    emoji: str = ""
    symptoms: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Compute derived fields."""
        self.vitality = health_to_vitality(self.health)
        self.emoji = get_emoji(self.organism_type, self.vitality)

    def colored_name(self) -> str:
        """Return the organism's path with ANSI color based on vitality."""
        color = VITALITY_COLORS.get(self.vitality, "")
        return f"{color}{self.emoji} {self.path}{ANSI_RESET}"


@dataclass
class Ecosystem:
    """The full ecosystem representing a project."""

    root_path: str
    organisms: Dict[str, Organism] = field(default_factory=dict)
    overall_health: float = 0.0
    thriving_count: int = 0
    healthy_count: int = 0
    stressed_count: int = 0
    critical_count: int = 0
    dead_count: int = 0

    def compute_stats(self) -> None:
        """Compute aggregate ecosystem statistics."""
        if not self.organisms:
            return

        self.overall_health = sum(o.health for o in self.organisms.values()) / len(self.organisms)

        self.thriving_count = sum(1 for o in self.organisms.values() if o.vitality == Vitality.THRIVING)
        self.healthy_count = sum(1 for o in self.organisms.values() if o.vitality == Vitality.HEALTHY)
        self.stressed_count = sum(1 for o in self.organisms.values() if o.vitality == Vitality.STRESSED)
        self.critical_count = sum(
            1 for o in self.organisms.values() if o.vitality in (Vitality.WILTING, Vitality.DYING)
        )
        self.dead_count = sum(1 for o in self.organisms.values() if o.vitality == Vitality.DEAD)

    @property
    def health_tier(self) -> str:
        """Human-readable health tier."""
        if self.overall_health >= 80:
            return "EXCELLENT"
        elif self.overall_health >= 60:
            return "GOOD"
        elif self.overall_health >= 40:
            return "FAIR"
        elif self.overall_health >= 20:
            return "POOR"
        else:
            return "CRITICAL"

    def most_critical(self) -> Optional[Organism]:
        """Return the organism with the lowest health."""
        if not self.organisms:
            return None
        return min(self.organisms.values(), key=lambda o: o.health)

    def healthiest(self) -> Optional[Organism]:
        """Return the organism with the highest health."""
        if not self.organisms:
            return None
        return max(self.organisms.values(), key=lambda o: o.health)


def compute_health_score(metrics: ModuleMetrics, avg_churn: float = 5.0) -> float:
    """Compute a health score (0-100) from module metrics.

    Args:
        metrics: Module metrics to evaluate.
        avg_churn: Average churn rate for the project (for relative scoring).

    Returns:
        Health score from 0 to 100.
    """
    score = 100.0

    # Churn penalty: high churn = stressed
    if metrics.churn_rate > CHURN_THRESHOLD:
        churn_penalty = min((metrics.churn_rate - CHURN_THRESHOLD) / CHURN_THRESHOLD, 1.0)
        score -= churn_penalty * 25 * CHURN_PENALTY_WEIGHT / 0.25
    else:
        # Bonus for low churn
        score += 0  # No bonus, just no penalty

    # Complexity penalty
    if metrics.complexity > COMPLEXITY_THRESHOLD:
        complexity_penalty = min((metrics.complexity - COMPLEXITY_THRESHOLD) / COMPLEXITY_THRESHOLD, 1.0)
        score -= complexity_penalty * 25 * COMPLEXITY_PENALTY_WEIGHT / 0.20
    elif metrics.complexity <= 5:
        # Bonus for low complexity
        score += 5

    # Coverage bonus/penalty
    if metrics.test_coverage >= COVERAGE_THRESHOLD:
        coverage_bonus = (metrics.test_coverage - COVERAGE_THRESHOLD) / (1.0 - COVERAGE_THRESHOLD)
        score += coverage_bonus * 10
    else:
        coverage_penalty = (COVERAGE_THRESHOLD - metrics.test_coverage) / COVERAGE_THRESHOLD
        score -= coverage_penalty * 20

    # Bug penalty
    score -= min(metrics.bug_count * 5, 25)

    # Stability bonus: old-growth is good
    if metrics.days_since_last_change > 180 and not metrics.is_dead:
        # Stable and maintained
        score += 5
    elif metrics.days_since_last_change == 0 and metrics.age_days < 30:
        # Very new, might be unstable
        score -= 5

    # Dead code penalty
    if metrics.is_dead:
        score -= 30

    # Deprecated penalty
    if metrics.is_deprecated:
        score -= 15

    return max(0.0, min(100.0, score))


def build_organism(metrics: ModuleMetrics, avg_churn: float = 5.0) -> Organism:
    """Build an Organism from module metrics.

    Args:
        metrics: Module metrics to convert.
        avg_churn: Average churn for the project.

    Returns:
        An Organism with computed health and type.
    """
    from ..metrics.stability import classify_stability, classify_age

    # Determine organism type
    if metrics.age_days < 30 and not metrics.is_deprecated:
        organism_type = OrganismType.SEEDLING
    else:
        organism_type = ROLE_TO_ORGANISM.get(metrics.module_role, OrganismType.BUSH)

    # Compute health
    health = compute_health_score(metrics, avg_churn)

    # Collect symptoms and strengths
    symptoms = []
    strengths = []

    if metrics.churn_rate > CHURN_THRESHOLD:
        symptoms.append(f"Churn rate {metrics.churn_rate:.1f}x above threshold (>{CHURN_THRESHOLD}/month)")
    elif metrics.churn_rate < 1.0 and metrics.commit_count > 0:
        strengths.append("Low churn — stable and predictable")

    if metrics.complexity > COMPLEXITY_THRESHOLD:
        symptoms.append(f"Cyclomatic complexity: {metrics.complexity} (threshold: {COMPLEXITY_THRESHOLD})")
    elif metrics.complexity <= 5 and metrics.complexity > 0:
        strengths.append("Low complexity — easy to understand")

    if metrics.test_coverage < COVERAGE_THRESHOLD and not metrics.is_test:
        symptoms.append(f"Test coverage: {metrics.test_coverage:.0%} (threshold: {COVERAGE_THRESHOLD:.0%})")
    elif metrics.test_coverage >= COVERAGE_THRESHOLD:
        strengths.append(f"Good test coverage: {metrics.test_coverage:.0%}")

    if metrics.bug_count > 0:
        symptoms.append(f"{metrics.bug_count} open bug(s) assigned")

    if metrics.is_dead:
        symptoms.append("Module appears to be dead code")

    if metrics.is_deprecated:
        symptoms.append("Module is deprecated")

    stability_tier = classify_stability(metrics.days_since_last_change)
    age_tier = classify_age(metrics.age_days)

    return Organism(
        path=metrics.path,
        organism_type=organism_type,
        health=health,
        stability_tier=stability_tier,
        age_tier=age_tier,
        symptoms=symptoms,
        strengths=strengths,
    )


def build_ecosystem(project: ProjectMetrics) -> Ecosystem:
    """Build a full Ecosystem from project metrics.

    Args:
        project: ProjectMetrics from the metrics engine.

    Returns:
        An Ecosystem with all organisms and aggregate stats.
    """
    ecosystem = Ecosystem(root_path=project.root_path)

    avg_churn = project.avg_churn if project.avg_churn > 0 else 5.0

    for path, metrics in project.modules.items():
        organism = build_organism(metrics, avg_churn)
        ecosystem.organisms[path] = organism

    ecosystem.compute_stats()
    return ecosystem
