"""Tests for mint.models — Data models."""

import pytest
from datetime import datetime, timezone

from ussy_mint.models import (
    MintMark,
    DieVariety,
    Composition,
    DebasementCurve,
    Hoard,
    ProvenanceLink,
    ProvenanceChain,
    PackageInfo,
    ProvenanceLevel,
    get_grade_label,
    get_grade_category,
)


class TestMintMark:
    """Test MintMark dataclass."""

    def test_default_values(self):
        mm = MintMark()
        assert mm.registry == "unknown"
        assert mm.publisher == "unknown"
        assert mm.timestamp.tzinfo is not None  # timezone-aware

    def test_custom_values(self):
        now = datetime.now(timezone.utc)
        mm = MintMark(
            registry="npm",
            publisher="lodash-team",
            publisher_key="gpg-key-123",
            artifact_hash="sha512-abc",
            timestamp=now,
        )
        assert mm.registry == "npm"
        assert mm.publisher == "lodash-team"


class TestComposition:
    """Test Composition dataclass."""

    def test_default_values(self):
        comp = Composition()
        assert comp.own_code_ratio == 1.0
        assert comp.transitive_depth == 0
        assert comp.transitive_count == 0

    def test_custom_values(self):
        comp = Composition(
            own_code_ratio=0.75,
            transitive_depth=5,
            transitive_count=25,
            alloy_breakdown={"core": 10, "test": 5},
            maintainer_overlap=0.3,
            license_mix={"MIT": 20, "Apache-2.0": 5},
        )
        assert comp.own_code_ratio == 0.75
        assert comp.maintainer_overlap == 0.3


class TestProvenanceLevel:
    """Test ProvenanceLevel enum."""

    def test_level_values(self):
        assert ProvenanceLevel.UNVERIFIED == 0
        assert ProvenanceLevel.BUILD_SIGNED == 1
        assert ProvenanceLevel.SOURCE_LINKED == 2
        assert ProvenanceLevel.END_TO_END == 3

    def test_comparison(self):
        assert ProvenanceLevel.END_TO_END > ProvenanceLevel.SOURCE_LINKED
        assert ProvenanceLevel.BUILD_SIGNED < ProvenanceLevel.SOURCE_LINKED


class TestHoard:
    """Test Hoard dataclass."""

    def test_default_values(self):
        hoard = Hoard()
        assert hoard.name == ""
        assert hoard.packages == []
        assert hoard.contamination_risk == 0.0

    def test_custom_values(self):
        hoard = Hoard(
            name="React Ecosystem",
            packages=["react", "react-dom"],
            contamination_risk=0.45,
        )
        assert hoard.name == "React Ecosystem"
        assert len(hoard.packages) == 2


class TestPackageInfo:
    """Test PackageInfo dataclass."""

    def test_default_grade(self):
        pkg = PackageInfo(name="test")
        assert pkg.sheldon_grade == 0
        assert pkg.grade_label == ""

    def test_composition_included(self):
        pkg = PackageInfo(name="test")
        assert isinstance(pkg.composition, Composition)
        assert isinstance(pkg.mint_mark, MintMark)


class TestGetGradeLabel:
    """Test grade label mapping for edge cases."""

    def test_below_range(self):
        short, desc = get_grade_label(0)
        assert short == "P-1"  # Clamped to minimum

    def test_above_range(self):
        short, desc = get_grade_label(100)
        assert "MS" in short  # Maximum

    def test_all_valid_grades(self):
        """Every grade 1-70 should return a valid label."""
        for grade in range(1, 71):
            short, desc = get_grade_label(grade)
            assert short
            assert desc
