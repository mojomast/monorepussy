"""Tests for actuary.backlog — Chain Ladder Vulnerability Backlog Projection."""

import math
import pytest
from actuary.backlog import (
    DevelopmentTriangle,
    compute_age_to_age_factors,
    compute_mack_variance,
    project_triangle,
    compute_reserve,
    chain_ladder_analysis,
    format_triangle,
)


@pytest.fixture
def sample_triangle():
    """Create the spec's example development triangle."""
    triangle = DevelopmentTriangle(repo_id="test-repo")
    data = [
        ("Q1-2024", 0, 12), ("Q1-2024", 1, 28), ("Q1-2024", 2, 41),
        ("Q1-2024", 3, 48), ("Q1-2024", 4, 52),
        ("Q2-2024", 0, 15), ("Q2-2024", 1, 33), ("Q2-2024", 2, 49),
        ("Q2-2024", 3, 57),
        ("Q3-2024", 0, 18), ("Q3-2024", 1, 39), ("Q3-2024", 2, 56),
        ("Q4-2024", 0, 21), ("Q4-2024", 1, 44),
        ("Q1-2025", 0, 24),
    ]
    for cohort, dev_q, count in data:
        triangle.set_value(cohort, dev_q, count)
    return triangle


class TestDevelopmentTriangle:
    """Tests for DevelopmentTriangle."""

    def test_create(self):
        triangle = DevelopmentTriangle(repo_id="test")
        assert triangle.repo_id == "test"

    def test_set_and_get(self):
        triangle = DevelopmentTriangle(repo_id="test")
        triangle.set_value("Q1-2024", 0, 12)
        assert triangle.get_value("Q1-2024", 0) == 12

    def test_get_missing(self):
        triangle = DevelopmentTriangle(repo_id="test")
        assert triangle.get_value("Q1-2024", 5) is None

    def test_max_dev(self, sample_triangle):
        assert sample_triangle.max_dev == 4

    def test_cohorts_list(self, sample_triangle):
        assert len(sample_triangle.cohorts) == 5


class TestAgeToAgeFactors:
    """Tests for compute_age_to_age_factors."""

    def test_factors_computed(self, sample_triangle):
        factors = compute_age_to_age_factors(sample_triangle)
        assert len(factors) == sample_triangle.max_dev
        # All factors should be positive
        for f in factors:
            assert f > 0

    def test_factor_values_reasonable(self, sample_triangle):
        factors = compute_age_to_age_factors(sample_triangle)
        # Age-to-age factors should be > 1 (more vulns found over time)
        for f in factors:
            assert f >= 1.0

    def test_spec_example_factor(self, sample_triangle):
        """First factor should be close to spec example."""
        factors = compute_age_to_age_factors(sample_triangle)
        # f_0 = sum(C_{i,1}) / sum(C_{i,0})
        # = (28+33+39+44) / (12+15+18+21) = 144/66 ≈ 2.182
        expected = (28 + 33 + 39 + 44) / (12 + 15 + 18 + 21)
        assert abs(factors[0] - expected) < 1e-6


class TestMackVariance:
    """Tests for compute_mack_variance."""

    def test_variance_computed(self, sample_triangle):
        factors = compute_age_to_age_factors(sample_triangle)
        variances = compute_mack_variance(sample_triangle, factors)
        assert len(variances) == len(factors)

    def test_variance_non_negative(self, sample_triangle):
        factors = compute_age_to_age_factors(sample_triangle)
        variances = compute_mack_variance(sample_triangle, factors)
        for v in variances:
            assert v >= 0


class TestProjectTriangle:
    """Tests for project_triangle."""

    def test_projection_fills_gaps(self, sample_triangle):
        factors = compute_age_to_age_factors(sample_triangle)
        projected = project_triangle(sample_triangle, factors)
        # Q1-2025 should have projected values for all quarters
        for j in range(5):
            assert j in projected["Q1-2025"]

    def test_known_values_preserved(self, sample_triangle):
        factors = compute_age_to_age_factors(sample_triangle)
        projected = project_triangle(sample_triangle, factors)
        # Known values should be unchanged
        assert projected["Q1-2024"][0] == 12.0
        assert projected["Q1-2024"][4] == 52.0

    def test_projected_values_greater(self, sample_triangle):
        factors = compute_age_to_age_factors(sample_triangle)
        projected = project_triangle(sample_triangle, factors)
        # Projected values should be >= last known value
        q1_2025_ultimate = projected["Q1-2025"][4]
        assert q1_2025_ultimate >= 24.0


class TestReserve:
    """Tests for compute_reserve."""

    def test_reserve_positive(self, sample_triangle):
        factors = compute_age_to_age_factors(sample_triangle)
        projected = project_triangle(sample_triangle, factors)
        reserve = compute_reserve(projected, sample_triangle)
        assert reserve > 0

    def test_reserve_is_ultimate_minus_current(self, sample_triangle):
        factors = compute_age_to_age_factors(sample_triangle)
        projected = project_triangle(sample_triangle, factors)
        reserve = compute_reserve(projected, sample_triangle)
        # Reserve should be sum of (ultimate - current) for each cohort
        total = 0.0
        for cohort in sample_triangle.cohorts:
            max_dev = 4
            ultimate = projected.get(cohort, {}).get(max_dev, 0.0)
            last_known_j = max(
                j for j in range(max_dev + 1)
                if sample_triangle.get_value(cohort, j) is not None
            )
            current = float(sample_triangle.get_value(cohort, last_known_j) or 0)
            total += ultimate - current
        assert abs(reserve - total) < 1e-6


class TestChainLadderAnalysis:
    """Tests for chain_ladder_analysis (full pipeline)."""

    def test_full_analysis(self, sample_triangle):
        result = chain_ladder_analysis(sample_triangle)
        assert result.total_reserve > 0
        assert len(result.age_to_age_factors) > 0
        assert result.confidence_lower <= result.total_reserve
        assert result.confidence_upper >= result.total_reserve

    def test_confidence_interval(self, sample_triangle):
        result = chain_ladder_analysis(sample_triangle, confidence_level=0.95)
        assert result.confidence_lower >= 0
        assert result.confidence_upper > result.confidence_lower

    def test_99_percent_ci(self, sample_triangle):
        result = chain_ladder_analysis(sample_triangle, confidence_level=0.99)
        result_95 = chain_ladder_analysis(sample_triangle, confidence_level=0.95)
        # 99% CI should be wider than 95% CI
        assert (result.confidence_upper - result.confidence_lower) >= \
               (result_95.confidence_upper - result_95.confidence_lower) * 0.99


class TestFormatTriangle:
    """Tests for format_triangle."""

    def test_format_output(self, sample_triangle):
        result = chain_ladder_analysis(sample_triangle)
        output = format_triangle(sample_triangle, result)
        assert "Vulnerability Development Triangle" in output
        assert "test-repo" in output
        assert "Age-to-age factors" in output

    def test_format_without_result(self, sample_triangle):
        output = format_triangle(sample_triangle)
        assert "Vulnerability Development Triangle" in output
