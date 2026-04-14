"""Tests for the ecosystem model and organisms."""

import pytest

from terrarium.metrics.models import ModuleMetrics, ProjectMetrics
from terrarium.ecosystem.organisms import (
    OrganismType, Vitality, ROLE_TO_ORGANISM,
    health_to_vitality, get_emoji,
)
from terrarium.ecosystem.model import (
    Organism, Ecosystem,
    compute_health_score, build_organism, build_ecosystem,
    CHURN_THRESHOLD, COMPLEXITY_THRESHOLD, COVERAGE_THRESHOLD,
)


class TestHealthToVitality:
    """Tests for health score to vitality conversion."""

    def test_thriving(self):
        assert health_to_vitality(100) == Vitality.THRIVING
        assert health_to_vitality(80) == Vitality.THRIVING

    def test_healthy(self):
        assert health_to_vitality(79) == Vitality.HEALTHY
        assert health_to_vitality(60) == Vitality.HEALTHY

    def test_stressed(self):
        assert health_to_vitality(59) == Vitality.STRESSED
        assert health_to_vitality(40) == Vitality.STRESSED

    def test_wilting(self):
        assert health_to_vitality(39) == Vitality.WILTING
        assert health_to_vitality(20) == Vitality.WILTING

    def test_dying(self):
        assert health_to_vitality(19) == Vitality.DYING
        assert health_to_vitality(1) == Vitality.DYING

    def test_dead(self):
        assert health_to_vitality(0) == Vitality.DEAD


class TestOrganismType:
    """Tests for organism type mapping."""

    def test_role_mapping(self):
        assert ROLE_TO_ORGANISM["entry_point"] == OrganismType.TREE
        assert ROLE_TO_ORGANISM["library"] == OrganismType.BUSH
        assert ROLE_TO_ORGANISM["config"] == OrganismType.MOSS
        assert ROLE_TO_ORGANISM["test"] == OrganismType.FLOWER
        assert ROLE_TO_ORGANISM["generated"] == OrganismType.FUNGUS
        assert ROLE_TO_ORGANISM["deprecated"] == OrganismType.DEAD_WOOD

    def test_get_emoji(self):
        """Emoji lookup works."""
        emoji = get_emoji(OrganismType.TREE, Vitality.THRIVING)
        assert emoji == "🌳"

    def test_get_emoji_unknown(self):
        """Unknown combinations return question mark."""
        # This should work for all valid combos
        for otype in OrganismType:
            for v in Vitality:
                emoji = get_emoji(otype, v)
                assert len(emoji) > 0


class TestOrganism:
    """Tests for the Organism dataclass."""

    def test_post_init_computes_vitality(self):
        """__post_init__ auto-computes vitality and emoji."""
        org = Organism(path="test.py", health=85, organism_type=OrganismType.TREE)
        assert org.vitality == Vitality.THRIVING
        assert org.emoji == "🌳"

    def test_post_init_stressed(self):
        """Stressed organism gets correct vitality."""
        org = Organism(path="test.py", health=45, organism_type=OrganismType.BUSH)
        assert org.vitality == Vitality.STRESSED

    def test_colored_name(self):
        """colored_name returns a string with ANSI codes."""
        org = Organism(path="test.py", health=90, organism_type=OrganismType.TREE)
        name = org.colored_name()
        assert "test.py" in name

    def test_default_stability_tier(self):
        """Default stability_tier is empty string."""
        org = Organism(path="test.py")
        assert org.stability_tier == ""


class TestComputeHealthScore:
    """Tests for health score computation."""

    def test_perfect_module(self):
        """A perfect module scores near 100."""
        m = ModuleMetrics(path="perfect.py", complexity=2, test_coverage=1.0,
                          churn_rate=0.5, bug_count=0, days_since_last_change=200)
        score = compute_health_score(m)
        assert score >= 80

    def test_high_churn_penalty(self):
        """High churn reduces health score."""
        good = ModuleMetrics(path="a.py", churn_rate=1.0, complexity=5, test_coverage=0.9)
        bad = ModuleMetrics(path="b.py", churn_rate=20.0, complexity=5, test_coverage=0.9)
        assert compute_health_score(good) > compute_health_score(bad)

    def test_high_complexity_penalty(self):
        """High complexity reduces health score."""
        good = ModuleMetrics(path="a.py", complexity=3, churn_rate=1.0, test_coverage=0.9)
        bad = ModuleMetrics(path="b.py", complexity=50, churn_rate=1.0, test_coverage=0.9)
        assert compute_health_score(good) > compute_health_score(bad)

    def test_low_coverage_penalty(self):
        """Low test coverage reduces health score."""
        good = ModuleMetrics(path="a.py", test_coverage=0.95, complexity=5, churn_rate=1.0)
        bad = ModuleMetrics(path="b.py", test_coverage=0.1, complexity=5, churn_rate=1.0)
        assert compute_health_score(good) > compute_health_score(bad)

    def test_dead_code_penalty(self):
        """Dead code has a significant penalty."""
        good = ModuleMetrics(path="a.py", is_dead=False, complexity=5, churn_rate=1.0)
        bad = ModuleMetrics(path="b.py", is_dead=True, complexity=5, churn_rate=1.0)
        assert compute_health_score(good) > compute_health_score(bad)

    def test_deprecated_penalty(self):
        """Deprecated code has a penalty."""
        good = ModuleMetrics(path="a.py", is_deprecated=False, complexity=5, churn_rate=1.0)
        bad = ModuleMetrics(path="b.py", is_deprecated=True, complexity=5, churn_rate=1.0)
        assert compute_health_score(good) > compute_health_score(bad)

    def test_score_bounds(self):
        """Health score is always between 0 and 100."""
        # Try extreme values
        m = ModuleMetrics(path="extreme.py", churn_rate=100, complexity=200,
                          bug_count=50, is_dead=True, is_deprecated=True)
        score = compute_health_score(m)
        assert 0 <= score <= 100


class TestBuildOrganism:
    """Tests for building organisms from metrics."""

    def test_build_library(self):
        """Build a bush organism from library metrics."""
        m = ModuleMetrics(path="utils.py", complexity=3, test_coverage=0.9,
                          churn_rate=1.0, age_days=100, days_since_last_change=10)
        org = build_organism(m)
        assert org.organism_type == OrganismType.BUSH
        assert org.health > 0

    def test_build_seedling(self):
        """New code is a seedling."""
        m = ModuleMetrics(path="new_feature.py", age_days=5, days_since_last_change=1)
        org = build_organism(m)
        assert org.organism_type == OrganismType.SEEDLING

    def test_build_deprecated(self):
        """Deprecated code is dead wood."""
        m = ModuleMetrics(path="old.py", is_deprecated=True, age_days=400,
                          days_since_last_change=200)
        org = build_organism(m)
        assert org.organism_type == OrganismType.DEAD_WOOD

    def test_build_with_symptoms(self):
        """Stressed modules have symptoms."""
        m = ModuleMetrics(path="stressed.py", churn_rate=10.0, complexity=30,
                          test_coverage=0.2, age_days=100, days_since_last_change=5)
        org = build_organism(m)
        assert len(org.symptoms) >= 2


class TestEcosystem:
    """Tests for the Ecosystem dataclass."""

    def test_compute_stats(self):
        """Ecosystem stats are computed correctly."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.organisms = {
            "a.py": Organism(path="a.py", health=90),
            "b.py": Organism(path="b.py", health=50),
        }
        eco.compute_stats()
        assert abs(eco.overall_health - 70.0) < 0.01
        assert eco.thriving_count == 1
        assert eco.stressed_count == 1

    def test_health_tier(self):
        """Health tier is determined correctly."""
        eco = Ecosystem(root_path="/tmp/test", overall_health=85)
        assert eco.health_tier == "EXCELLENT"
        eco.overall_health = 65
        assert eco.health_tier == "GOOD"
        eco.overall_health = 45
        assert eco.health_tier == "FAIR"
        eco.overall_health = 25
        assert eco.health_tier == "POOR"
        eco.overall_health = 10
        assert eco.health_tier == "CRITICAL"

    def test_most_critical(self):
        """most_critical returns the organism with lowest health."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.organisms = {
            "a.py": Organism(path="a.py", health=90),
            "b.py": Organism(path="b.py", health=20),
        }
        critical = eco.most_critical()
        assert critical is not None
        assert critical.path == "b.py"

    def test_healthiest(self):
        """healthiest returns the organism with highest health."""
        eco = Ecosystem(root_path="/tmp/test")
        eco.organisms = {
            "a.py": Organism(path="a.py", health=90),
            "b.py": Organism(path="b.py", health=20),
        }
        healthy = eco.healthiest()
        assert healthy is not None
        assert healthy.path == "a.py"

    def test_empty_ecosystem(self):
        """Empty ecosystem returns None for most_critical/healthiest."""
        eco = Ecosystem(root_path="/tmp/test")
        assert eco.most_critical() is None
        assert eco.healthiest() is None


class TestBuildEcosystem:
    """Tests for building a full ecosystem from project metrics."""

    def test_build_ecosystem(self):
        """Build an ecosystem from project metrics."""
        project = ProjectMetrics(root_path="/tmp/test")
        project.modules = {
            "a.py": ModuleMetrics(path="a.py", complexity=5, test_coverage=0.9,
                                   churn_rate=1.0, age_days=100, days_since_last_change=10),
            "b.py": ModuleMetrics(path="b.py", complexity=30, test_coverage=0.2,
                                   churn_rate=10.0, age_days=200, days_since_last_change=1),
        }
        project.compute_aggregates()

        eco = build_ecosystem(project)
        assert len(eco.organisms) == 2
        assert eco.overall_health > 0
        assert eco.health_tier in ("EXCELLENT", "GOOD", "FAIR", "POOR", "CRITICAL")
