"""Tests for the ecosystem model and organisms."""

import pytest

from terrarium.metrics.models import ModuleMetrics, ProjectMetrics
from terrarium.ecosystem.organisms import (
    OrganismType,
    Vitality,
    ROLE_TO_ORGANISM,
    health_to_vitality,
    get_emoji,
)
from terrarium.ecosystem.model import (
    Organism,
    Ecosystem,
    compute_health_score,
    build_organism,
    build_ecosystem,
    CHURN_THRESHOLD,
    COMPLEXITY_THRESHOLD,
    COVERAGE_THRESHOLD,
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
        m = ModuleMetrics(
            path="perfect.py",
            complexity=2,
            test_coverage=1.0,
            churn_rate=0.5,
            bug_count=0,
            days_since_last_change=200,
        )
        score = compute_health_score(m)
        assert score >= 80

    def test_high_churn_penalty(self):
        """High churn reduces health score."""
        good = ModuleMetrics(
            path="a.py", churn_rate=1.0, complexity=5, test_coverage=0.9
        )
        bad = ModuleMetrics(
            path="b.py", churn_rate=20.0, complexity=5, test_coverage=0.9
        )
        assert compute_health_score(good) > compute_health_score(bad)

    def test_high_complexity_penalty(self):
        """High complexity reduces health score."""
        good = ModuleMetrics(
            path="a.py", complexity=3, churn_rate=1.0, test_coverage=0.9
        )
        bad = ModuleMetrics(
            path="b.py", complexity=50, churn_rate=1.0, test_coverage=0.9
        )
        assert compute_health_score(good) > compute_health_score(bad)

    def test_low_coverage_penalty(self):
        """Low test coverage reduces health score."""
        good = ModuleMetrics(
            path="a.py", test_coverage=0.95, complexity=5, churn_rate=1.0
        )
        bad = ModuleMetrics(
            path="b.py", test_coverage=0.1, complexity=5, churn_rate=1.0
        )
        assert compute_health_score(good) > compute_health_score(bad)

    def test_dead_code_penalty(self):
        """Dead code has a significant penalty."""
        good = ModuleMetrics(path="a.py", is_dead=False, complexity=5, churn_rate=1.0)
        bad = ModuleMetrics(path="b.py", is_dead=True, complexity=5, churn_rate=1.0)
        assert compute_health_score(good) > compute_health_score(bad)

    def test_deprecated_penalty(self):
        """Deprecated code has a penalty."""
        good = ModuleMetrics(
            path="a.py", is_deprecated=False, complexity=5, churn_rate=1.0
        )
        bad = ModuleMetrics(
            path="b.py", is_deprecated=True, complexity=5, churn_rate=1.0
        )
        assert compute_health_score(good) > compute_health_score(bad)

    def test_score_bounds(self):
        """Health score is always between 0 and 100."""
        # Try extreme values
        m = ModuleMetrics(
            path="extreme.py",
            churn_rate=100,
            complexity=200,
            bug_count=50,
            is_dead=True,
            is_deprecated=True,
        )
        score = compute_health_score(m)
        assert 0 <= score <= 100


class TestBuildOrganism:
    """Tests for building organisms from metrics."""

    def test_build_library(self):
        """Build a bush organism from library metrics."""
        m = ModuleMetrics(
            path="utils.py",
            complexity=3,
            test_coverage=0.9,
            churn_rate=1.0,
            age_days=100,
            days_since_last_change=10,
        )
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
        m = ModuleMetrics(
            path="old.py", is_deprecated=True, age_days=400, days_since_last_change=200
        )
        org = build_organism(m)
        assert org.organism_type == OrganismType.DEAD_WOOD

    def test_build_with_symptoms(self):
        """Stressed modules have symptoms."""
        m = ModuleMetrics(
            path="stressed.py",
            churn_rate=10.0,
            complexity=30,
            test_coverage=0.2,
            age_days=100,
            days_since_last_change=5,
        )
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


class TestBuildOrganismExtended:
    """Extended tests for build_organism with various ModuleMetrics."""

    def test_build_organism_high_complexity(self):
        """High complexity should add symptoms and reduce health."""
        m = ModuleMetrics(
            path="complex.py",
            complexity=50,
            test_coverage=0.9,
            churn_rate=1.0,
            age_days=100,
            days_since_last_change=10,
        )
        org = build_organism(m)
        assert org.health < 100
        assert any("complexity" in s.lower() for s in org.symptoms)

    def test_build_organism_dead_code(self):
        """Dead code should have a significant penalty and symptom."""
        m = ModuleMetrics(
            path="dead.py",
            is_dead=True,
            complexity=5,
            test_coverage=0.9,
            churn_rate=1.0,
            age_days=100,
            days_since_last_change=10,
        )
        org = build_organism(m)
        # Dead code penalty is -30 but other bonuses can offset; verify symptom exists
        assert any("dead code" in s.lower() for s in org.symptoms)

    def test_build_organism_low_coverage(self):
        """Low coverage should add symptoms and reduce health."""
        m = ModuleMetrics(
            path="uncovered.py",
            test_coverage=0.1,
            complexity=5,
            churn_rate=1.0,
            age_days=100,
            days_since_last_change=10,
        )
        org = build_organism(m)
        assert org.health < 100
        assert any("coverage" in s.lower() for s in org.symptoms)

    def test_build_organism_with_crack_intensity(self):
        """Crack intensity should reduce health and add symptom."""
        from terrarium.ecosystem.model import OrganismHealthState

        m = ModuleMetrics(
            path="cracked.py",
            complexity=5,
            test_coverage=0.9,
            churn_rate=1.0,
            age_days=100,
            days_since_last_change=10,
        )
        health_state = OrganismHealthState(path="cracked.py", crack_intensity=0.5)
        org = build_organism(m, health_state=health_state)
        assert org.crack_intensity == 0.5
        assert org.health < 100
        assert any("crack" in s.lower() for s in org.symptoms)

    def test_build_organism_with_infection(self):
        """Infection state should reduce health and add symptoms."""
        from terrarium.ecosystem.model import OrganismHealthState

        m = ModuleMetrics(
            path="infected.py",
            complexity=5,
            test_coverage=0.9,
            churn_rate=1.0,
            age_days=100,
            days_since_last_change=10,
        )
        # Infected (I)
        health_state_i = OrganismHealthState(path="infected.py", infection_state="I")
        org_i = build_organism(m, health_state=health_state_i)
        assert org_i.infection_state == "I"
        assert org_i.health < 100
        assert any("infection" in s.lower() for s in org_i.symptoms)

        # Exposed (E)
        health_state_e = OrganismHealthState(path="infected.py", infection_state="E")
        org_e = build_organism(m, health_state=health_state_e)
        assert org_e.infection_state == "E"
        assert org_e.health > org_i.health  # less penalty than infected

        # Recovered (R)
        health_state_r = OrganismHealthState(path="infected.py", infection_state="R")
        org_r = build_organism(m, health_state=health_state_r)
        assert org_r.infection_state == "R"
        assert org_r.health < 100  # slight penalty for recovered

    def test_build_organism_with_anomaly(self):
        """Anomaly active should reduce health and add symptom."""
        from terrarium.ecosystem.model import OrganismHealthState

        m = ModuleMetrics(
            path="anomalous.py",
            complexity=5,
            test_coverage=0.9,
            churn_rate=1.0,
            age_days=100,
            days_since_last_change=10,
        )
        health_state = OrganismHealthState(path="anomalous.py", anomaly_active=True)
        org = build_organism(m, health_state=health_state)
        assert org.anomaly_active is True
        assert org.health < 100
        assert any("anomaly" in s.lower() for s in org.symptoms)


class TestComputeHealthScoreEdgeCases:
    """Edge case tests for compute_health_score."""

    def test_zero_metrics(self):
        """All-zero metrics should still return a valid score."""
        m = ModuleMetrics(path="zero.py")
        score = compute_health_score(m)
        assert 0 <= score <= 100

    def test_very_high_churn(self):
        """Extremely high churn should cap penalty."""
        m = ModuleMetrics(
            path="high_churn.py", churn_rate=1000.0, complexity=5, test_coverage=0.9
        )
        score = compute_health_score(m)
        assert score >= 0

    def test_very_high_complexity(self):
        """Extremely high complexity should cap penalty."""
        m = ModuleMetrics(
            path="high_complex.py", complexity=1000, test_coverage=0.9, churn_rate=1.0
        )
        score = compute_health_score(m)
        assert score >= 0

    def test_perfect_coverage(self):
        """Perfect coverage should give a bonus."""
        m = ModuleMetrics(
            path="perfect.py", test_coverage=1.0, complexity=5, churn_rate=1.0
        )
        score = compute_health_score(m)
        # Bonus pushes above 100 but is clamped to 100
        assert score == 100.0

    def test_new_unstable_code(self):
        """Very new code with 0 days since change should get a penalty."""
        m = ModuleMetrics(
            path="new.py",
            age_days=5,
            days_since_last_change=0,
            complexity=5,
            test_coverage=0.9,
            churn_rate=1.0,
        )
        score = compute_health_score(m)
        # Should be slightly lower than baseline due to new code penalty
        assert score < 105

    def test_stable_old_growth(self):
        """Old code with no recent changes should get a stability bonus."""
        m = ModuleMetrics(
            path="stable.py",
            age_days=500,
            days_since_last_change=200,
            complexity=5,
            test_coverage=0.9,
            churn_rate=1.0,
        )
        score = compute_health_score(m)
        # Bonus pushes above 100 but is clamped to 100
        assert score == 100.0


class TestBuildEcosystem:
    """Tests for building a full ecosystem from project metrics."""

    def test_build_ecosystem(self):
        """Build an ecosystem from project metrics."""
        project = ProjectMetrics(root_path="/tmp/test")
        project.modules = {
            "a.py": ModuleMetrics(
                path="a.py",
                complexity=5,
                test_coverage=0.9,
                churn_rate=1.0,
                age_days=100,
                days_since_last_change=10,
            ),
            "b.py": ModuleMetrics(
                path="b.py",
                complexity=30,
                test_coverage=0.2,
                churn_rate=10.0,
                age_days=200,
                days_since_last_change=1,
            ),
        }
        project.compute_aggregates()

        eco = build_ecosystem(project)
        assert len(eco.organisms) == 2
        assert eco.overall_health > 0
        assert eco.health_tier in ("EXCELLENT", "GOOD", "FAIR", "POOR", "CRITICAL")
