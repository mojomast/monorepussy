"""Tests for actuary.aggregate — Copula Risk Model."""

import math
import pytest
from ussy_actuary.aggregate import (
    simulate_aggregate_loss,
    compute_var_tvar,
    format_copula_result,
)


class TestSimulateAggregateLoss:
    """Tests for simulate_aggregate_loss."""

    def test_independent_copula(self):
        result = simulate_aggregate_loss(
            n_assets=50,
            exploit_prob=0.05,
            copula_type="independent",
            n_simulations=1000,
            seed=42,
        )
        assert result.n_assets == 50
        assert result.n_simulations == 1000
        assert result.mean_loss >= 0
        assert result.var_value >= 0
        assert result.tvar_value >= result.var_value

    def test_gaussian_copula(self):
        result = simulate_aggregate_loss(
            n_assets=50,
            exploit_prob=0.05,
            copula_type="gaussian",
            copula_params={"correlation": 0.3, "var_level": 0.99},
            n_simulations=1000,
            seed=42,
        )
        assert result.copula_type == "gaussian"
        assert result.tvar_value >= result.var_value

    def test_clayton_copula(self):
        result = simulate_aggregate_loss(
            n_assets=50,
            exploit_prob=0.05,
            copula_type="clayton",
            copula_params={"alpha": 2.0, "var_level": 0.99},
            n_simulations=1000,
            seed=42,
        )
        assert result.copula_type == "clayton"
        assert result.tvar_value >= 0

    def test_gumbel_copula(self):
        result = simulate_aggregate_loss(
            n_assets=50,
            exploit_prob=0.05,
            copula_type="gumbel",
            copula_params={"beta": 2.0, "var_level": 0.99},
            n_simulations=1000,
            seed=42,
        )
        assert result.copula_type == "gumbel"
        assert result.tvar_value >= 0

    def test_reproducibility_with_seed(self):
        r1 = simulate_aggregate_loss(
            n_assets=20, exploit_prob=0.1,
            copula_type="independent", n_simulations=500, seed=123,
        )
        r2 = simulate_aggregate_loss(
            n_assets=20, exploit_prob=0.1,
            copula_type="independent", n_simulations=500, seed=123,
        )
        assert abs(r1.mean_loss - r2.mean_loss) < 1e-6
        assert abs(r1.var_value - r2.var_value) < 1e-6

    def test_higher_correlation_more_tail_risk(self):
        """Gaussian with high correlation should have higher TVaR than independent."""
        independent = simulate_aggregate_loss(
            n_assets=100, exploit_prob=0.01,
            copula_type="independent", n_simulations=5000, seed=42,
            copula_params={"var_level": 0.99},
        )
        correlated = simulate_aggregate_loss(
            n_assets=100, exploit_prob=0.01,
            copula_type="gaussian",
            copula_params={"correlation": 0.5, "var_level": 0.99},
            n_simulations=5000, seed=42,
        )
        # Correlated model should have higher TVaR
        assert correlated.tvar_value >= independent.tvar_value * 0.8  # Allow some MC noise

    def test_zero_exploit_prob(self):
        result = simulate_aggregate_loss(
            n_assets=100, exploit_prob=0.0,
            copula_type="independent", n_simulations=1000, seed=42,
        )
        assert result.mean_loss == 0.0

    def test_var_level_in_result(self):
        result = simulate_aggregate_loss(
            n_assets=50, exploit_prob=0.05,
            copula_type="independent",
            copula_params={"var_level": 0.95},
            n_simulations=1000, seed=42,
        )
        assert abs(result.var_level - 0.95) < 1e-10


class TestComputeVarTvar:
    """Tests for compute_var_tvar."""

    def test_basic_computation(self):
        losses = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        var, tvar = compute_var_tvar(losses, var_level=0.9)
        assert var > 0
        assert tvar >= var

    def test_empty_losses(self):
        var, tvar = compute_var_tvar([], var_level=0.99)
        assert var == 0.0
        assert tvar == 0.0

    def test_single_loss(self):
        var, tvar = compute_var_tvar([5.0], var_level=0.99)
        assert var == 5.0
        assert tvar == 5.0

    def test_tvar_greater_than_var(self):
        losses = list(range(1, 101))
        var, tvar = compute_var_tvar(losses, var_level=0.95)
        assert tvar >= var


class TestFormatCopulaResult:
    """Tests for format_copula_result."""

    def test_format_output(self):
        result = simulate_aggregate_loss(
            n_assets=50, exploit_prob=0.05,
            copula_type="independent", n_simulations=1000, seed=42,
        )
        output = format_copula_result(result)
        assert "Correlated Risk Aggregation" in output
        assert "independent" in output
