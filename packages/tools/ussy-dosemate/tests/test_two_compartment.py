"""Tests for the two-compartment model."""

import math

import pytest

from ussy_dosemate.two_compartment import TwoCompartmentParams, compute_two_compartment, compute_propagation_curve
from ussy_dosemate.distribution import DistributionParams


class TestTwoCompartmentParams:
    """Tests for TwoCompartmentParams dataclass."""

    def test_concentration_at_time_zero(self):
        """At t=0, concentration should be A + B (total dose)."""
        params = TwoCompartmentParams(
            alpha=0.5, beta=0.05, A=0.6, B=0.4,
            alpha_half_life_hours=1.39, beta_half_life_days=13.86,
        )
        c0 = params.concentration(0)
        assert abs(c0 - 1.0) < 0.01

    def test_concentration_decreasing(self):
        """Concentration should decrease over time."""
        params = TwoCompartmentParams(
            alpha=0.5, beta=0.05, A=0.6, B=0.4,
            alpha_half_life_hours=1.39, beta_half_life_days=13.86,
        )
        c0 = params.concentration(0)
        c1 = params.concentration(1)
        c10 = params.concentration(10)
        c100 = params.concentration(100)
        assert c0 > c1 > c10 > c100

    def test_concentration_always_positive(self):
        """Concentration should always be non-negative."""
        params = TwoCompartmentParams(
            alpha=0.5, beta=0.05, A=0.6, B=0.4,
            alpha_half_life_hours=1.39, beta_half_life_days=13.86,
        )
        for t in [0, 1, 10, 100, 1000]:
            assert params.concentration(t) >= 0

    def test_phase_dominant_early_alpha(self):
        """At early times, alpha phase should dominate."""
        params = TwoCompartmentParams(
            alpha=0.5, beta=0.05, A=0.6, B=0.4,
            alpha_half_life_hours=1.39, beta_half_life_days=13.86,
        )
        phase = params.phase_dominant_at(0.1)
        assert "alpha" in phase.lower()

    def test_phase_dominant_late_beta(self):
        """At late times, beta phase should dominate (the slow tail)."""
        params = TwoCompartmentParams(
            alpha=0.5, beta=0.01, A=0.3, B=0.7,
            alpha_half_life_hours=1.39, beta_half_life_days=69.3,
        )
        # After alpha phase has decayed significantly
        phase = params.phase_dominant_at(100.0)
        assert "beta" in phase.lower()


class TestComputeTwoCompartment:
    """Tests for compute_two_compartment function."""

    def test_alpha_faster_than_beta(self):
        """Alpha rate should be faster than beta rate."""
        dist = DistributionParams(
            Vd=10.0, Kp=1.0, fu=0.5,
            total_dependent_modules=10,
            central_compartment_size=2,
            peripheral_compartment_size=8,
        )
        result = compute_two_compartment(dist)
        assert result.alpha > result.beta

    def test_alpha_half_life_reasonable(self):
        """Alpha half-life should be in hours range."""
        dist = DistributionParams(
            Vd=10.0, Kp=1.0, fu=0.5,
            total_dependent_modules=10,
            central_compartment_size=2,
            peripheral_compartment_size=8,
        )
        result = compute_two_compartment(dist, avg_direct_adoption_hours=4.0)
        assert 0.1 < result.alpha_half_life_hours < 100

    def test_beta_half_life_reasonable(self):
        """Beta half-life should be in days range."""
        dist = DistributionParams(
            Vd=10.0, Kp=1.0, fu=0.5,
            total_dependent_modules=10,
            central_compartment_size=2,
            peripheral_compartment_size=8,
        )
        result = compute_two_compartment(dist, avg_transitive_adoption_days=14.0)
        assert 1 < result.beta_half_life_days < 200

    def test_coefficients_sum_to_one(self):
        """A + B should equal 1 (normalized dose)."""
        dist = DistributionParams(
            Vd=10.0, Kp=1.0, fu=0.5,
            total_dependent_modules=10,
            central_compartment_size=3,
            peripheral_compartment_size=7,
        )
        result = compute_two_compartment(dist)
        assert abs(result.A + result.B - 1.0) < 0.01

    def test_more_central_higher_A(self):
        """More central compartment modules should mean higher A coefficient."""
        dist_more_central = DistributionParams(
            Vd=10.0, Kp=1.0, fu=0.5,
            total_dependent_modules=10,
            central_compartment_size=8,
            peripheral_compartment_size=2,
        )
        dist_less_central = DistributionParams(
            Vd=10.0, Kp=1.0, fu=0.5,
            total_dependent_modules=10,
            central_compartment_size=2,
            peripheral_compartment_size=8,
        )
        result_more = compute_two_compartment(dist_more_central)
        result_less = compute_two_compartment(dist_less_central)
        assert result_more.A > result_less.A


class TestPropagationCurve:
    """Tests for compute_propagation_curve function."""

    def test_curve_decreasing(self):
        """Propagation curve should be monotonically decreasing."""
        dist = DistributionParams(
            Vd=10.0, Kp=1.0, fu=0.5,
            total_dependent_modules=10,
            central_compartment_size=2,
            peripheral_compartment_size=8,
        )
        params = compute_two_compartment(dist)
        time_points = [0, 1, 5, 10, 50, 100, 500]
        curve = compute_propagation_curve(params, time_points)
        
        for i in range(1, len(curve)):
            assert curve[i][1] <= curve[i-1][1]

    def test_curve_correct_length(self):
        """Curve should have same length as input time points."""
        dist = DistributionParams(
            Vd=10.0, Kp=1.0, fu=0.5,
            total_dependent_modules=10,
            central_compartment_size=2,
            peripheral_compartment_size=8,
        )
        params = compute_two_compartment(dist)
        time_points = [0, 1, 2, 3, 4, 5]
        curve = compute_propagation_curve(params, time_points)
        assert len(curve) == len(time_points)
