"""Tests for actuary.moral_hazard — Security Incentive Quantification."""

import math
import pytest
from actuary.moral_hazard import (
    compute_moral_hazard,
    analyze_sla,
    format_moral_hazard,
)


class TestComputeMoralHazard:
    """Tests for compute_moral_hazard."""

    def test_basic_computation(self):
        result = compute_moral_hazard(
            base_loss=1_000_000,
            base_probability=0.05,
            effort_cost=0.3,
            coverage_fraction=0.8,
            effort_elasticity=0.5,
        )
        assert result.optimal_effort_uncovered > 0
        assert result.optimal_effort_covered >= 0
        assert result.effort_reduction_pct == 80.0  # alpha = 0.8 → 80%

    def test_effort_reduction_equals_coverage(self):
        """Delta_e/e* = alpha (effort drops by coverage fraction)."""
        for alpha in [0.0, 0.25, 0.5, 0.75, 1.0]:
            result = compute_moral_hazard(
                base_loss=1_000_000,
                base_probability=0.05,
                effort_cost=0.3,
                coverage_fraction=alpha,
            )
            assert abs(result.effort_reduction - alpha) < 1e-10
            assert abs(result.effort_reduction_pct - alpha * 100) < 1e-10

    def test_welfare_loss_formula(self):
        """WL = alpha^2 * p0^2 * L^2 / (8c)."""
        result = compute_moral_hazard(
            base_loss=1_000_000,
            base_probability=0.05,
            effort_cost=0.3,
            coverage_fraction=0.8,
        )
        expected_wl = (0.8 ** 2 * 0.05 ** 2 * 1_000_000 ** 2) / (8 * 0.3)
        assert abs(result.welfare_loss - expected_wl) < 1e-6

    def test_no_coverage(self):
        """With alpha=0, effort should be unchanged."""
        result = compute_moral_hazard(
            base_loss=1_000_000,
            base_probability=0.05,
            effort_cost=0.3,
            coverage_fraction=0.0,
        )
        assert result.effort_reduction_pct == 0.0
        assert result.optimal_effort_covered == result.optimal_effort_uncovered
        assert result.welfare_loss == 0.0

    def test_full_coverage(self):
        """With alpha=1, effort should drop to zero."""
        result = compute_moral_hazard(
            base_loss=1_000_000,
            base_probability=0.05,
            effort_cost=0.3,
            coverage_fraction=1.0,
        )
        assert result.optimal_effort_covered == 0.0
        assert result.effort_reduction_pct == 100.0

    def test_optimal_coinsurance(self):
        """alpha* = 1 / (1 + p0*L/(2c) * eta)."""
        result = compute_moral_hazard(
            base_loss=1_000_000,
            base_probability=0.05,
            effort_cost=0.3,
            coverage_fraction=0.8,
            effort_elasticity=0.5,
        )
        e_star = result.optimal_effort_uncovered
        expected_alpha = 1.0 / (1.0 + e_star * 0.5)
        assert abs(result.optimal_coinsurance - expected_alpha) < 1e-6

    def test_covered_breach_probability(self):
        """p(e_hat) = p0 - eta * e_hat."""
        result = compute_moral_hazard(
            base_loss=1_000_000,
            base_probability=0.05,
            effort_cost=0.3,
            coverage_fraction=0.5,
            effort_elasticity=0.5,
        )
        # Covered effort is reduced, so breach probability increases
        assert result.covered_breach_probability >= 0

    def test_adverse_selection_default(self):
        result = compute_moral_hazard(
            base_loss=1_000_000,
            base_probability=0.05,
            effort_cost=0.3,
            coverage_fraction=0.8,
        )
        # Default ASR = 1 + alpha * 0.1 = 1.08
        assert abs(result.adverse_selection_ratio - 1.08) < 1e-10

    def test_custom_adverse_selection(self):
        result = compute_moral_hazard(
            base_loss=1_000_000,
            base_probability=0.05,
            effort_cost=0.3,
            coverage_fraction=0.8,
            adverse_selection_ratio=1.5,
        )
        assert result.adverse_selection_ratio == 1.5


class TestAnalyzeSLA:
    """Tests for analyze_sla."""

    def test_sla_analysis(self):
        result = analyze_sla(
            vendor_coverage=0.9,
            sla_penalty=100_000,
            base_loss=1_000_000,
            base_probability=0.05,
            effort_cost=0.3,
        )
        assert "vendor_coverage" in result
        assert "effort_reduction_pct" in result
        assert "welfare_loss" in result
        assert "recommendation" in result

    def test_sla_penalty_reduces_coverage(self):
        result = analyze_sla(
            vendor_coverage=0.9,
            sla_penalty=100_000,
            base_loss=1_000_000,
            base_probability=0.05,
            effort_cost=0.3,
        )
        # Effective coverage = 0.9 - 100000/1000000 = 0.8
        assert abs(result["effective_coverage"] - 0.8) < 1e-10

    def test_sla_recommendation_present(self):
        result = analyze_sla(
            vendor_coverage=0.9,
            sla_penalty=50000,
            base_loss=1_000_000,
            base_probability=0.05,
            effort_cost=0.3,
        )
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 0


class TestFormatMoralHazard:
    """Tests for format_moral_hazard."""

    def test_format_output(self):
        result = compute_moral_hazard(
            base_loss=1_000_000,
            base_probability=0.05,
            effort_cost=0.3,
            coverage_fraction=0.8,
        )
        output = format_moral_hazard(result)
        assert "Moral Hazard" in output
        assert "80.0%" in output
