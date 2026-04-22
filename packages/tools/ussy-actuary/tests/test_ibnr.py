"""Tests for actuary.ibnr — IBNR Latent Vulnerability Estimation."""

import math
import pytest
from ussy_actuary.ibnr import (
    bornhuetter_ferguson,
    cape_cod,
    ibnr_from_density,
    format_ibnr,
)
from ussy_actuary.backlog import DevelopmentTriangle


@pytest.fixture
def sample_triangle():
    """Create a sample development triangle for IBNR testing."""
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


class TestBornhuetterFerguson:
    """Tests for bornhuetter_ferguson."""

    def test_basic_computation(self, sample_triangle):
        priors = {"Q2-2024": 65, "Q3-2024": 72, "Q4-2024": 58, "Q1-2025": 68}
        results = bornhuetter_ferguson(sample_triangle, priors)
        assert len(results) > 0

    def test_reserve_positive(self, sample_triangle):
        priors = {"Q2-2024": 65, "Q3-2024": 72, "Q4-2024": 58, "Q1-2025": 68}
        results = bornhuetter_ferguson(sample_triangle, priors)
        # At least one incomplete cohort should have positive reserve
        has_positive = any(r.bf_reserve > 0 for r in results)
        assert has_positive

    def test_ultimate_equals_reported_plus_reserve(self, sample_triangle):
        priors = {"Q2-2024": 65, "Q3-2024": 72, "Q4-2024": 58, "Q1-2025": 68}
        results = bornhuetter_ferguson(sample_triangle, priors)
        for r in results:
            assert abs(r.bf_ultimate - (r.reported_count + r.bf_reserve)) < 1e-6

    def test_method_is_bf(self, sample_triangle):
        priors = {"Q2-2024": 65, "Q3-2024": 72, "Q4-2024": 58, "Q1-2025": 68}
        results = bornhuetter_ferguson(sample_triangle, priors)
        for r in results:
            assert r.method == "bf"

    def test_spec_example(self):
        """Library released 6 months ago, 3 reported CVEs, density=20."""
        result = ibnr_from_density(
            reported_count=3,
            density_per_kloc=20,
            kloc=1.0,  # 1 KLOC, so prior_ultimate = 20
        )
        # BF_reserve = prior_ultimate * (1 - reported/prior)
        # = 20 * (1 - 3/20) = 20 * 0.85 = 17
        assert abs(result.bf_reserve - 17.0) < 1e-6
        assert abs(result.bf_ultimate - 20.0) < 1e-6


class TestCapeCod:
    """Tests for cape_cod."""

    def test_basic_computation(self, sample_triangle):
        results = cape_cod(sample_triangle)
        assert len(results) > 0

    def test_method_is_cape_cod(self, sample_triangle):
        results = cape_cod(sample_triangle)
        for r in results:
            assert r.method == "cape_cod"

    def test_cape_cod_prior_set(self, sample_triangle):
        results = cape_cod(sample_triangle)
        for r in results:
            assert r.cape_cod_prior is not None


class TestIBNRFromDensity:
    """Tests for ibnr_from_density."""

    def test_basic_density(self):
        result = ibnr_from_density(
            reported_count=3,
            density_per_kloc=15.0,
            kloc=10.0,
        )
        # prior_ultimate = 15 * 10 = 150
        assert result.prior_ultimate == 150.0
        # BF_reserve = 150 * (1 - 3/150) = 150 * 0.98 = 147
        assert abs(result.bf_reserve - 147.0) < 1e-6
        assert abs(result.bf_ultimate - 150.0) < 1e-6

    def test_zero_reported(self):
        result = ibnr_from_density(
            reported_count=0,
            density_per_kloc=15.0,
            kloc=10.0,
        )
        # All are latent
        assert abs(result.bf_reserve - 150.0) < 1e-6

    def test_full_reporting(self):
        result = ibnr_from_density(
            reported_count=150,
            density_per_kloc=15.0,
            kloc=10.0,
        )
        # No latent vulnerabilities
        assert abs(result.bf_reserve) < 1e-6

    def test_zero_density(self):
        result = ibnr_from_density(
            reported_count=5,
            density_per_kloc=0.0,
            kloc=10.0,
        )
        assert result.bf_reserve == 0.0


class TestFormatIBNR:
    """Tests for format_ibnr."""

    def test_format_output(self):
        results = [
            ibnr_from_density(reported_count=3, density_per_kloc=20.0, kloc=1.0)
        ]
        output = format_ibnr(results)
        assert "IBNR" in output
        assert "BF" in output
