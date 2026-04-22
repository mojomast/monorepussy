"""Tests for actuary.credibility — Bühlmann Credibility."""

import math
import pytest
from ussy_actuary.credibility import (
    compute_epv,
    compute_vhm,
    compute_credibility,
    credibility_from_params,
    format_credibility,
)


class TestComputeEPV:
    """Tests for compute_epv (Expected Process Variance)."""

    def test_single_group(self):
        groups = [[0.1, 0.2, 0.15, 0.25]]
        epv = compute_epv(groups)
        # Variance of [0.1, 0.2, 0.15, 0.25]
        mean = sum(groups[0]) / 4
        var = sum((x - mean) ** 2 for x in groups[0]) / 3
        assert abs(epv - var) < 1e-10

    def test_multiple_groups(self):
        groups = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]
        epv = compute_epv(groups)
        # Should be average of within-group variances
        var1 = sum((x - 0.2) ** 2 for x in groups[0]) / 2
        var2 = sum((x - 0.5) ** 2 for x in groups[1]) / 2
        expected = (var1 + var2) / 2
        assert abs(epv - expected) < 1e-10

    def test_empty_input(self):
        assert compute_epv([]) == 0.0

    def test_single_element_groups(self):
        groups = [[0.5], [0.3]]
        # Groups with <2 elements have no variance, so EPV = 0
        epv = compute_epv(groups)
        assert epv == 0.0


class TestComputeVHM:
    """Tests for compute_vhm (Variance of Hypothetical Means)."""

    def test_identical_means(self):
        # All groups have same mean → VHM should be 0
        means = [0.5, 0.5, 0.5]
        vhm = compute_vhm(means, epv=0.01, group_sizes=[10, 10, 10])
        assert vhm == 0.0

    def test_different_means(self):
        means = [0.1, 0.5, 0.9]
        vhm = compute_vhm(means, epv=0.01, group_sizes=[10, 10, 10])
        assert vhm > 0

    def test_vhm_non_negative(self):
        means = [0.1, 0.2]
        vhm = compute_vhm(means, epv=0.5, group_sizes=[3, 3])
        assert vhm >= 0

    def test_fewer_than_two_means(self):
        assert compute_vhm([0.5], epv=0.01, group_sizes=[10]) == 0.0


class TestComputeCredibility:
    """Tests for compute_credibility (full Bühlmann)."""

    def test_zero_observations(self):
        """With no internal data, Z should be 0 (pure population)."""
        result = compute_credibility(
            org_id="test",
            n_obs=0,
            internal_data=[],
            all_groups_data=[[0.1, 0.2], [0.3, 0.4]],
        )
        assert result.Z == 0.0
        assert result.blended_mean == result.population_mean

    def test_many_observations(self):
        """With many observations, Z should approach 1."""
        # Create data where one org has lots of observations
        internal = [0.05] * 100
        result = compute_credibility(
            org_id="test",
            n_obs=100,
            internal_data=internal,
            all_groups_data=[[0.1, 0.2], [0.3, 0.4], internal],
        )
        assert result.Z > 0.5  # High credibility with lots of data

    def test_blended_between_internal_and_population(self):
        """Blended mean should be between internal and population means."""
        result = compute_credibility(
            org_id="test",
            n_obs=10,
            internal_data=[0.1] * 10,
            all_groups_data=[[0.3, 0.4, 0.5], [0.1] * 10],
            population_mean=0.5,
        )
        min_val = min(result.internal_mean, result.population_mean)
        max_val = max(result.internal_mean, result.population_mean)
        assert min_val <= result.blended_mean <= max_val

    def test_credibility_formula(self):
        """Z = n / (n + K) where K = EPV/VHM."""
        result = compute_credibility(
            org_id="test",
            n_obs=10,
            internal_data=[0.05] * 10,
            all_groups_data=[[0.1, 0.2], [0.05] * 10],
        )
        if result.K != float('inf') and result.K > 0:
            expected_Z = 10 / (10 + result.K)
            assert abs(result.Z - expected_Z) < 1e-6


class TestCredibilityFromParams:
    """Tests for credibility_from_params."""

    def test_direct_computation(self):
        result = credibility_from_params(
            org_id="test",
            n_obs=52,
            epv=0.01,
            vhm=0.001,
            internal_mean=0.05,
            population_mean=0.03,
        )
        K = 0.01 / 0.001  # = 10
        expected_Z = 52 / (52 + 10)
        assert abs(result.Z - expected_Z) < 1e-6

    def test_zero_vhm(self):
        result = credibility_from_params(
            org_id="test",
            n_obs=10,
            epv=0.01,
            vhm=0.0,
            internal_mean=0.05,
            population_mean=0.03,
        )
        assert result.Z == 0.0

    def test_spec_example_z_95(self):
        """Org with 52 weeks internal data → Z ≈ 0.95."""
        # Z = n/(n + K), for Z ≈ 0.95: K = n * (1-Z)/Z = 52 * 0.05/0.95 ≈ 2.74
        result = credibility_from_params(
            org_id="test",
            n_obs=52,
            epv=0.1,
            vhm=0.1 / 2.74,  # K = 2.74
            internal_mean=0.05,
            population_mean=0.03,
        )
        assert abs(result.Z - 0.95) < 0.02

    def test_spec_example_z_57(self):
        """Org with 4 weeks internal data → Z ≈ 0.57."""
        # K = 52 * 0.05/0.95 ≈ 2.74 (same org, less data)
        result = credibility_from_params(
            org_id="test",
            n_obs=4,
            epv=0.1,
            vhm=0.1 / 2.74,
            internal_mean=0.05,
            population_mean=0.03,
        )
        assert abs(result.Z - 0.57) < 0.05


class TestFormatCredibility:
    """Tests for format_credibility."""

    def test_format_output(self):
        result = credibility_from_params(
            org_id="myorg",
            n_obs=10,
            epv=0.01,
            vhm=0.001,
            internal_mean=0.05,
            population_mean=0.03,
        )
        output = format_credibility(result)
        assert "myorg" in output
        assert "Credibility Z" in output
