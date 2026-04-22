"""Tests for the metabolism module."""

import math

import pytest

from ussy_dosemate.metabolism import MetabolismParams, compute_metabolism
from ussy_dosemate.ci_collector import CIMetrics


class TestMetabolismParams:
    """Tests for MetabolismParams dataclass."""

    def test_michaelis_menten_rate_low_substrate(self):
        """At low [S], rate should be approximately (Vmax/Km) * [S]."""
        params = MetabolismParams(
            first_pass_effect=0.3,
            bioavailability_F=0.5,
            ci_saturation_fraction=0.1,
            Vmax=15.0,
            Km=800.0,
            processing_rate=1.5,
        )
        # At very low substrate, first-order approximation
        S = 10.0
        rate = params.michaelis_menten_rate(S)
        expected_approx = (params.Vmax / params.Km) * S
        assert abs(rate - expected_approx) / expected_approx < 0.05

    def test_michaelis_menten_rate_high_substrate(self):
        """At high [S], rate should approach Vmax."""
        params = MetabolismParams(
            first_pass_effect=0.3,
            bioavailability_F=0.5,
            ci_saturation_fraction=0.9,
            Vmax=15.0,
            Km=800.0,
            processing_rate=14.0,
        )
        S = 100000.0  # very high
        rate = params.michaelis_menten_rate(S)
        assert abs(rate - params.Vmax) / params.Vmax < 0.01

    def test_michaelis_menten_at_km(self):
        """At [S] = Km, rate should be Vmax/2."""
        params = MetabolismParams(
            first_pass_effect=0.3,
            bioavailability_F=0.5,
            ci_saturation_fraction=0.5,
            Vmax=15.0,
            Km=800.0,
            processing_rate=7.5,
        )
        rate = params.michaelis_menten_rate(800.0)
        assert abs(rate - params.Vmax / 2) < 0.01

    def test_michaelis_menten_zero_substrate(self):
        """At [S] = 0, rate should be 0."""
        params = MetabolismParams(
            first_pass_effect=0.3, bioavailability_F=0.5,
            ci_saturation_fraction=0.1, Vmax=15.0, Km=800.0, processing_rate=0,
        )
        assert params.michaelis_menten_rate(0) == 0.0

    def test_saturation_diagnosis_levels(self):
        """Diagnosis should change based on saturation fraction."""
        for fraction, expected_keyword in [
            (0.3, "comfortably"),
            (0.6, "moderately"),
            (0.8, "heavily"),
            (0.95, "near saturation"),
        ]:
            params = MetabolismParams(
                first_pass_effect=0.3, bioavailability_F=0.5,
                ci_saturation_fraction=fraction, Vmax=15.0, Km=800.0,
                processing_rate=fraction * 15.0,
            )
            diagnosis = params.saturation_diagnosis()
            assert expected_keyword.lower() in diagnosis.lower()


class TestComputeMetabolism:
    """Tests for compute_metabolism function."""

    def test_bioavailability_bounded(self):
        """Bioavailability F should be in [0, 1]."""
        ci = CIMetrics(
            pr_arrival_rate=5.0,
            max_ci_capacity=15.0,
            half_saturation_size=800.0,
            ci_thoroughness=5.0,
            avg_pr_size_lines=200.0,
            avg_review_time_hours=24.0,
            merge_rate=0.8,
            lint_pass_rate=0.85,
            review_survival_rate=0.78,
        )
        result = compute_metabolism(ci)
        assert 0.0 <= result.bioavailability_F <= 1.0

    def test_strict_ci_low_hepatic(self):
        """Strict CI (high thoroughness) should result in low F_hepatic."""
        ci_strict = CIMetrics(
            pr_arrival_rate=2.0,
            max_ci_capacity=15.0,
            half_saturation_size=800.0,
            ci_thoroughness=20.0,  # very strict
            avg_pr_size_lines=200.0,
            avg_review_time_hours=48.0,
            merge_rate=0.5,
            lint_pass_rate=0.7,
            review_survival_rate=0.6,
        )
        ci_permissive = CIMetrics(
            pr_arrival_rate=2.0,
            max_ci_capacity=15.0,
            half_saturation_size=800.0,
            ci_thoroughness=1.0,  # permissive
            avg_pr_size_lines=200.0,
            avg_review_time_hours=6.0,
            merge_rate=0.95,
            lint_pass_rate=0.95,
            review_survival_rate=0.95,
        )
        strict_result = compute_metabolism(ci_strict)
        permissive_result = compute_metabolism(ci_permissive)
        # Strict CI should have higher first-pass effect (more "metabolized")
        assert strict_result.first_pass_effect > permissive_result.first_pass_effect

    def test_first_pass_effect_bounded(self):
        """First-pass effect should be in [0, 1]."""
        ci = CIMetrics(
            pr_arrival_rate=5.0, max_ci_capacity=15.0,
            half_saturation_size=800.0, ci_thoroughness=5.0,
            avg_pr_size_lines=200.0, avg_review_time_hours=24.0,
            merge_rate=0.8, lint_pass_rate=0.85, review_survival_rate=0.78,
        )
        result = compute_metabolism(ci)
        assert 0.0 <= result.first_pass_effect <= 1.0

    def test_ci_saturation_bounded(self):
        """CI saturation fraction should be in [0, 1]."""
        ci = CIMetrics(
            pr_arrival_rate=5.0, max_ci_capacity=15.0,
            half_saturation_size=800.0, ci_thoroughness=5.0,
            avg_pr_size_lines=200.0, avg_review_time_hours=24.0,
            merge_rate=0.8, lint_pass_rate=0.85, review_survival_rate=0.78,
        )
        result = compute_metabolism(ci)
        assert 0.0 <= result.ci_saturation_fraction <= 1.0

    def test_bioavailability_product(self):
        """Bioavailability F should be f_absorption * f_lint * f_review."""
        ci = CIMetrics(
            pr_arrival_rate=5.0, max_ci_capacity=15.0,
            half_saturation_size=800.0, ci_thoroughness=5.0,
            avg_pr_size_lines=200.0, avg_review_time_hours=24.0,
            merge_rate=0.8, lint_pass_rate=0.9, review_survival_rate=0.8,
        )
        f_absorption = 0.85
        result = compute_metabolism(ci, fraction_absorbed=f_absorption)
        expected_F = f_absorption * 0.9 * 0.8
        assert abs(result.bioavailability_F - expected_F) < 0.01
