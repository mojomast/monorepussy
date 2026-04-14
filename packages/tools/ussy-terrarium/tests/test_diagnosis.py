"""Tests for the diagnosis engine."""

import pytest

from terrarium.ecosystem.organisms import OrganismType, Vitality
from terrarium.ecosystem.model import Organism
from terrarium.ecosystem.diagnosis import diagnose, Diagnosis


class TestDiagnose:
    """Tests for the diagnosis generator."""

    def test_thriving_module(self):
        """Healthy modules get a positive diagnosis."""
        org = Organism(
            path="utils.py",
            health=90,
            organism_type=OrganismType.BUSH,
            symptoms=[],
            strengths=["Good test coverage: 95%", "Low complexity"],
        )
        diag = diagnose(org)
        assert diag.vitality == Vitality.THRIVING
        assert "healthy" in diag.diagnosis_text.lower()
        assert diag.priority == "LOW"

    def test_stressed_module(self):
        """Stressed modules get a concerning diagnosis."""
        org = Organism(
            path="auth.py",
            health=45,
            organism_type=OrganismType.BUSH,
            symptoms=[
                "Churn rate 8.0x above threshold",
                "Test coverage: 42%",
            ],
        )
        diag = diagnose(org)
        assert diag.priority in ("MEDIUM", "HIGH")

    def test_dying_module(self):
        """Dying modules get a critical diagnosis."""
        org = Organism(
            path="legacy.py",
            health=15,
            organism_type=OrganismType.DEAD_WOOD,
            symptoms=["Module is deprecated", "Module appears to be dead code"],
        )
        diag = diagnose(org)
        assert diag.priority in ("HIGH", "CRITICAL")
        assert len(diag.treatment) > 0

    def test_overworked_module(self):
        """High churn + complexity + low coverage = overworked."""
        org = Organism(
            path="hotspot.py",
            health=30,
            organism_type=OrganismType.BUSH,
            symptoms=[
                "Churn rate 6.0x above threshold",
                "Cyclomatic complexity: 25",
                "Test coverage: 30%",
            ],
        )
        diag = diagnose(org)
        assert "overworked" in diag.diagnosis_text.lower() or "under-tested" in diag.diagnosis_text.lower()
        assert len(diag.treatment) > 0

    def test_format_report(self):
        """Report formatting produces readable output."""
        org = Organism(
            path="auth.py",
            health=35,
            organism_type=OrganismType.BUSH,
            symptoms=["High churn", "Low coverage"],
        )
        diag = diagnose(org)
        report = diag.format_report()
        assert "auth.py" in report
        assert "STRESSED" in report or "WILTING" in report
        assert "Symptoms:" in report

    def test_dead_code_diagnosis(self):
        """Dead code gets specific treatment advice."""
        org = Organism(
            path="old.py",
            health=5,
            organism_type=OrganismType.DEAD_WOOD,
            symptoms=["Module appears to be dead code"],
        )
        diag = diagnose(org)
        assert "dead code" in diag.diagnosis_text.lower()
        assert "remove" in diag.treatment.lower()

    def test_deprecated_diagnosis(self):
        """Deprecated modules get migration advice."""
        org = Organism(
            path="deprecated.py",
            health=20,
            organism_type=OrganismType.DEAD_WOOD,
            symptoms=["Module is deprecated"],
        )
        diag = diagnose(org)
        assert "deprecated" in diag.diagnosis_text.lower()

    def test_complexity_only_diagnosis(self):
        """Complexity-only issues get refactoring advice."""
        org = Organism(
            path="complex.py",
            health=55,
            organism_type=OrganismType.BUSH,
            symptoms=["Cyclomatic complexity: 25 (threshold: 15)"],
        )
        diag = diagnose(org)
        assert "complex" in diag.diagnosis_text.lower() or "refactor" in diag.treatment.lower()

    def test_coverage_only_diagnosis(self):
        """Low coverage gets testing advice."""
        org = Organism(
            path="untested.py",
            health=60,
            organism_type=OrganismType.BUSH,
            symptoms=["Test coverage: 40% (threshold: 80%)"],
        )
        diag = diagnose(org)
        assert "test" in diag.treatment.lower() or "coverage" in diag.diagnosis_text.lower()

    def test_churn_only_diagnosis(self):
        """High churn alone gets stability advice."""
        org = Organism(
            path="volatile.py",
            health=55,
            organism_type=OrganismType.BUSH,
            symptoms=["Churn rate 8.0x above threshold"],
        )
        diag = diagnose(org)
        assert "churn" in diag.diagnosis_text.lower() or "frequent" in diag.diagnosis_text.lower()
