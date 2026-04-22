"""Tests for mint.sheldon — Sheldon grading system."""

import pytest
from ussy_mint.sheldon import (
    sheldon_grade,
    grade_package,
    grade_breakdown,
    compute_strike_quality,
    compute_surface_preservation,
    compute_luster,
    compute_eye_appeal,
)
from ussy_mint.models import PackageInfo, get_grade_label, get_grade_category


class TestSheldonGrade:
    """Test the core Sheldon grade calculation."""

    def test_perfect_scores(self):
        """All 1.0 inputs should give MS-70."""
        grade = sheldon_grade(1.0, 1.0, 1.0, 1.0)
        assert grade == 70

    def test_zero_scores_clamped(self):
        """Zero inputs are clamped to 0.001, giving a very low grade."""
        grade = sheldon_grade(0.001, 0.001, 0.001, 0.001)
        assert grade >= 1
        assert grade <= 5

    def test_midrange_scores(self):
        """0.5 across the board should give a midrange grade."""
        grade = sheldon_grade(0.5, 0.5, 0.5, 0.5)
        assert 30 <= grade <= 40

    def test_harmonic_mean_penalizes_weakness(self):
        """One low score should drag down the grade significantly."""
        grade_balanced = sheldon_grade(0.8, 0.8, 0.8, 0.8)
        grade_weak = sheldon_grade(0.8, 0.8, 0.8, 0.1)
        assert grade_balanced > grade_weak

    def test_grade_bounded_1_to_70(self):
        """Grade must always be between 1 and 70."""
        for strike in [0.001, 0.1, 0.5, 0.9, 1.0]:
            for surface in [0.001, 0.1, 0.5, 0.9, 1.0]:
                grade = sheldon_grade(strike, surface, 0.5, 0.5)
                assert 1 <= grade <= 70

    def test_high_scores_high_grade(self):
        """High scores should produce a Mint State grade."""
        grade = sheldon_grade(0.9, 0.9, 0.9, 0.9)
        assert grade >= 60  # MS-60 or higher

    def test_low_scores_low_grade(self):
        """Low scores should produce a Poor/Fair grade."""
        grade = sheldon_grade(0.05, 0.05, 0.05, 0.05)
        assert grade <= 10


class TestGradeLabel:
    """Test grade label mapping."""

    def test_grade_70(self):
        short, desc = get_grade_label(70)
        assert short == "MS-70"
        assert desc == "Mint State"

    def test_grade_1(self):
        short, desc = get_grade_label(1)
        assert short == "P-1"
        assert desc == "Poor"

    def test_grade_65(self):
        short, desc = get_grade_label(65)
        assert short == "MS-65"

    def test_grade_50(self):
        short, desc = get_grade_label(50)
        assert short == "AU-50"

    def test_grade_40(self):
        short, desc = get_grade_label(40)
        assert short == "XF-40"


class TestGradeCategory:
    """Test broad grade categories."""

    def test_mint_state(self):
        assert get_grade_category(65) == "Mint State"

    def test_about_uncirculated(self):
        assert get_grade_category(55) == "About Uncirculated"

    def test_extremely_fine(self):
        assert get_grade_category(42) == "Extremely Fine"

    def test_very_fine(self):
        assert get_grade_category(30) == "Very Fine"

    def test_fine(self):
        assert get_grade_category(12) == "Fine"

    def test_very_good(self):
        assert get_grade_category(8) == "Very Good"

    def test_good(self):
        assert get_grade_category(4) == "Good"

    def test_poor(self):
        assert get_grade_category(1) == "Poor"


class TestGradePackage:
    """Test the grade_package function."""

    def test_grade_package_populates_fields(self):
        pkg = PackageInfo(
            name="test-pkg",
            strike_quality=0.8,
            surface_preservation=0.7,
            luster=0.75,
            eye_appeal=0.65,
        )
        result = grade_package(pkg)
        assert result.sheldon_grade >= 1
        assert result.sheldon_grade <= 70
        assert result.grade_label  # Non-empty label

    def test_grade_package_returns_same_object(self):
        pkg = PackageInfo(name="test")
        result = grade_package(pkg)
        assert result is pkg


class TestGradeBreakdown:
    """Test detailed grade breakdown."""

    def test_breakdown_structure(self):
        bd = grade_breakdown(0.8, 0.7, 0.75, 0.65)
        assert "grade" in bd
        assert "label" in bd
        assert "category" in bd
        assert "strike_70" in bd
        assert "surface_70" in bd
        assert "luster_70" in bd
        assert "eye_appeal_70" in bd

    def test_sub_grades_in_range(self):
        bd = grade_breakdown(0.5, 0.5, 0.5, 0.5)
        for key in ["strike_70", "surface_70", "luster_70", "eye_appeal_70"]:
            assert 1 <= bd[key] <= 70


class TestComputeStrikeQuality:
    """Test strike quality computation."""

    def test_perfect_build(self):
        score = compute_strike_quality(
            reproducible_build=True,
            api_surface_match=1.0,
            type_coverage=1.0,
        )
        assert score == 1.0

    def test_no_reproducible_build(self):
        score = compute_strike_quality(reproducible_build=False)
        assert score < 0.7

    def test_low_type_coverage(self):
        score = compute_strike_quality(type_coverage=0.0)
        assert score < 0.8


class TestComputeSurfacePreservation:
    """Test surface preservation computation."""

    def test_well_maintained(self):
        score = compute_surface_preservation(
            deprecated_ratio=0.0,
            avg_issue_age_days=7,
            pr_merge_latency_days=2,
            changelog_completeness=1.0,
        )
        assert score > 0.9

    def test_poorly_maintained(self):
        score = compute_surface_preservation(
            deprecated_ratio=0.5,
            avg_issue_age_days=300,
            pr_merge_latency_days=60,
            changelog_completeness=0.1,
        )
        assert score < 0.5


class TestComputeLuster:
    """Test luster (documentation quality) computation."""

    def test_excellent_docs(self):
        score = compute_luster(
            doc_freshness=1.0,
            type_def_coverage=1.0,
            example_completeness=1.0,
            readme_quality=1.0,
        )
        assert score == 1.0

    def test_poor_docs(self):
        score = compute_luster(
            doc_freshness=0.0,
            type_def_coverage=0.0,
            example_completeness=0.0,
            readme_quality=0.0,
        )
        assert score == 0.0


class TestComputeEyeAppeal:
    """Test eye appeal (developer experience) computation."""

    def test_great_dx(self):
        score = compute_eye_appeal(
            install_size_efficiency=1.0,
            startup_time=1.0,
            import_clarity=1.0,
            error_message_quality=1.0,
        )
        assert score == 1.0

    def test_terrible_dx(self):
        score = compute_eye_appeal(
            install_size_efficiency=0.0,
            startup_time=0.0,
            import_clarity=0.0,
            error_message_quality=0.0,
        )
        assert score == 0.0
