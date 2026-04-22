"""Tests for the excretion module."""

import math

import pytest

from dosemate.excretion import ExcretionParams, compute_excretion
from dosemate.distribution import DistributionParams


class TestExcretionParams:
    """Tests for ExcretionParams dataclass."""

    def test_concentration_decay(self):
        """Concentration should decay exponentially."""
        params = ExcretionParams(CL=0.5, ke=0.1, t_half=6.93)
        c0 = 100.0
        # After one half-life, concentration should be ~50
        c_at_half = params.concentration_at_time(c0, params.t_half)
        assert abs(c_at_half - 50.0) < 1.0

    def test_concentration_always_positive(self):
        """Concentration should never be negative."""
        params = ExcretionParams(CL=0.5, ke=0.1, t_half=6.93)
        c0 = 100.0
        for t in range(0, 100):
            assert params.concentration_at_time(c0, t) >= 0

    def test_time_to_threshold(self):
        """Time to threshold should be correct."""
        params = ExcretionParams(CL=0.5, ke=0.1, t_half=6.93)
        c0 = 100.0
        threshold = 50.0
        t = params.time_to_threshold(c0, threshold)
        # Should be approximately t_half
        assert abs(t - params.t_half) < 1.0

    def test_time_to_threshold_above_c0(self):
        """If threshold >= C0, return infinity."""
        params = ExcretionParams(CL=0.5, ke=0.1, t_half=6.93)
        assert params.time_to_threshold(50.0, 100.0) == float('inf')

    def test_time_to_threshold_zero_ke(self):
        """If ke is 0, return infinity."""
        params = ExcretionParams(CL=0.5, ke=0, t_half=float('inf'))
        assert params.time_to_threshold(100.0, 50.0) == float('inf')

    def test_influence_remaining(self):
        """Influence remaining should decay from 1 to 0."""
        params = ExcretionParams(CL=0.5, ke=0.1, t_half=6.93)
        assert abs(params.influence_remaining(0) - 1.0) < 0.01
        assert params.influence_remaining(1000) < 0.01

    def test_influence_remaining_bounded(self):
        """Influence remaining should always be in [0, 1]."""
        params = ExcretionParams(CL=0.5, ke=0.1, t_half=6.93)
        for t in range(0, 200):
            val = params.influence_remaining(t)
            assert 0.0 <= val <= 1.0


class TestComputeExcretion:
    """Tests for compute_excretion function."""

    def test_half_life_positive(self):
        """Half-life should always be positive."""
        dist = DistributionParams(
            Vd=10.0, Kp=1.0, fu=0.5,
            total_dependent_modules=10,
            central_compartment_size=2,
            peripheral_compartment_size=8,
        )
        result = compute_excretion(dist)
        assert result.t_half > 0

    def test_ke_relationship(self):
        """ke = CL / Vd."""
        dist = DistributionParams(
            Vd=10.0, Kp=1.0, fu=0.5,
            total_dependent_modules=10,
            central_compartment_size=2,
            peripheral_compartment_size=8,
        )
        result = compute_excretion(dist, deprecated_lines_removed=5, total_deprecated_lines=100)
        assert abs(result.ke - result.CL / dist.Vd) < 0.001

    def test_half_life_formula(self):
        """t_half = 0.693 * Vd / CL."""
        dist = DistributionParams(
            Vd=20.0, Kp=1.0, fu=0.5,
            total_dependent_modules=20,
            central_compartment_size=5,
            peripheral_compartment_size=15,
        )
        result = compute_excretion(dist, deprecated_lines_removed=10, total_deprecated_lines=50)
        expected_t_half = 0.693 * dist.Vd / result.CL
        assert abs(result.t_half - expected_t_half) < 0.01

    def test_high_clearance_short_half_life(self):
        """High clearance should result in shorter half-life."""
        dist = DistributionParams(
            Vd=10.0, Kp=1.0, fu=0.5,
            total_dependent_modules=10,
            central_compartment_size=2,
            peripheral_compartment_size=8,
        )
        low_cl = compute_excretion(dist, deprecated_lines_removed=1, total_deprecated_lines=100)
        high_cl = compute_excretion(dist, deprecated_lines_removed=50, total_deprecated_lines=100)
        assert high_cl.t_half < low_cl.t_half

    def test_high_vd_long_half_life(self):
        """High Vd should result in longer half-life (all else equal)."""
        dist_low = DistributionParams(
            Vd=5.0, Kp=1.0, fu=0.5,
            total_dependent_modules=5,
            central_compartment_size=1,
            peripheral_compartment_size=4,
        )
        dist_high = DistributionParams(
            Vd=50.0, Kp=1.0, fu=0.5,
            total_dependent_modules=50,
            central_compartment_size=10,
            peripheral_compartment_size=40,
        )
        result_low = compute_excretion(dist_low, deprecated_lines_removed=5, total_deprecated_lines=50)
        result_high = compute_excretion(dist_high, deprecated_lines_removed=5, total_deprecated_lines=50)
        # Same CL fraction, but higher Vd → longer half-life
        assert result_high.t_half > result_low.t_half

    def test_observed_deprecation_rate_override(self):
        """Provided observed_deprecation_rate should override computed CL."""
        dist = DistributionParams(
            Vd=10.0, Kp=1.0, fu=0.5,
            total_dependent_modules=10,
            central_compartment_size=2,
            peripheral_compartment_size=8,
        )
        result = compute_excretion(dist, observed_deprecation_rate=0.5)
        assert result.CL == 0.5
