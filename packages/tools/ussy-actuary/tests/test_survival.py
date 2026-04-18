"""Tests for actuary.survival — CVE Exploit Survival Table."""

import math
import pytest
from actuary.survival import (
    LifeTableRow,
    SurvivalTable,
    compute_life_table,
    whittaker_henderson_graduation,
    apply_graduation,
    format_life_table,
)


class TestLifeTableRow:
    """Tests for LifeTableRow dataclass."""

    def test_create_row(self):
        row = LifeTableRow(age_days=30, l_v=812, d_v=28, q_v=0.0345, mu_v=0.0351, e_v=142.7)
        assert row.age_days == 30
        assert row.l_v == 812
        assert row.q_v_graduated == 0.0

    def test_row_with_graduated(self):
        row = LifeTableRow(age_days=0, l_v=847, d_v=12, q_v=0.0142, mu_v=0.0143, e_v=287.3, q_v_graduated=0.0135)
        assert row.q_v_graduated == 0.0135


class TestSurvivalTable:
    """Tests for SurvivalTable."""

    def test_empty_table(self):
        table = SurvivalTable(cohort_id="test")
        assert len(table.rows) == 0

    def test_add_row(self):
        table = SurvivalTable(cohort_id="test")
        row = LifeTableRow(age_days=0, l_v=100, d_v=5, q_v=0.05, mu_v=0.0513, e_v=200.0)
        table.add_row(row)
        assert len(table.rows) == 1
        assert table.rows[0].age_days == 0

    def test_get_row(self):
        table = SurvivalTable(cohort_id="test")
        table.add_row(LifeTableRow(age_days=0, l_v=100, d_v=5, q_v=0.05, mu_v=0.0513, e_v=200.0))
        table.add_row(LifeTableRow(age_days=30, l_v=95, d_v=10, q_v=0.1053, mu_v=0.1111, e_v=100.0))
        row = table.get_row(30)
        assert row is not None
        assert row.l_v == 95

    def test_get_row_not_found(self):
        table = SurvivalTable(cohort_id="test")
        assert table.get_row(99) is None

    def test_survival_probability(self):
        table = SurvivalTable(cohort_id="test")
        table.add_row(LifeTableRow(age_days=0, l_v=100, d_v=5, q_v=0.05, mu_v=0.0513, e_v=200.0))
        table.add_row(LifeTableRow(age_days=30, l_v=80, d_v=10, q_v=0.125, mu_v=0.1333, e_v=100.0))
        prob = table.survival_probability(30)
        assert abs(prob - 0.8) < 1e-10

    def test_survival_probability_empty(self):
        table = SurvivalTable(cohort_id="test")
        assert table.survival_probability(0) == 0.0

    def test_hazard_at(self):
        table = SurvivalTable(cohort_id="test")
        table.add_row(LifeTableRow(age_days=0, l_v=100, d_v=5, q_v=0.05, mu_v=0.0513, e_v=200.0))
        assert abs(table.hazard_at(0) - 0.0513) < 1e-10

    def test_hazard_at_missing(self):
        table = SurvivalTable(cohort_id="test")
        assert table.hazard_at(99) == 0.0


class TestComputeLifeTable:
    """Tests for compute_life_table."""

    def test_basic_life_table(self):
        ages = [0, 30, 60, 90, 180, 365]
        l_values = [847, 812, 741, 634, 421, 198]
        d_values = [12, 28, 45, 38, 15, 4]

        table = compute_life_table(ages, l_values, d_values, cohort_id="Q1-2025")
        assert table.cohort_id == "Q1-2025"
        assert len(table.rows) == 6

    def test_q_v_computation(self):
        ages = [0, 30]
        l_values = [100, 90]
        d_values = [10, 5]

        table = compute_life_table(ages, l_values, d_values)
        assert abs(table.rows[0].q_v - 0.1) < 1e-10
        assert abs(table.rows[1].q_v - 5.0 / 90.0) < 1e-10

    def test_mu_v_computation(self):
        ages = [0, 30]
        l_values = [100, 90]
        d_values = [10, 5]

        table = compute_life_table(ages, l_values, d_values)
        # mu_v ≈ q_v / (1 - q_v/2)
        q = 0.1
        expected_mu = q / (1 - q / 2)
        assert abs(table.rows[0].mu_v - expected_mu) < 1e-10

    def test_e_v_positive(self):
        ages = [0, 30, 60]
        l_values = [100, 90, 80]
        d_values = [10, 10, 5]

        table = compute_life_table(ages, l_values, d_values)
        # e_v should be positive for surviving cohorts
        assert table.rows[0].e_v > 0
        assert table.rows[1].e_v > 0

    def test_zero_l_v(self):
        ages = [0, 30]
        l_values = [0, 0]
        d_values = [0, 0]

        table = compute_life_table(ages, l_values, d_values)
        assert table.rows[0].q_v == 0.0
        assert table.rows[0].mu_v == 0.0
        assert table.rows[0].e_v == 0.0

    def test_full_exploitation(self):
        ages = [0, 30]
        l_values = [100, 0]
        d_values = [100, 0]

        table = compute_life_table(ages, l_values, d_values)
        assert table.rows[0].q_v == 1.0
        assert table.rows[0].mu_v == float('inf')

    def test_spec_example_values(self):
        """Test with the exact values from the spec."""
        ages = [0, 30, 60, 90, 180, 365]
        l_values = [847, 812, 741, 634, 421, 198]
        d_values = [12, 28, 45, 38, 15, 4]

        table = compute_life_table(ages, l_values, d_values)
        # Check first row q_v
        assert abs(table.rows[0].q_v - 12 / 847) < 1e-6
        # Check that l_v values match
        for i, expected_l in enumerate(l_values):
            assert table.rows[i].l_v == expected_l


class TestWhittakerHenderson:
    """Tests for Whittaker-Henderson graduation."""

    def test_short_input(self):
        """Less than 3 values should return unchanged."""
        result = whittaker_henderson_graduation([0.1, 0.2])
        assert result == [0.1, 0.2]

    def test_no_smoothing(self):
        """Lambda=0 should return values close to original."""
        values = [0.01, 0.03, 0.06, 0.04, 0.02]
        result = whittaker_henderson_graduation(values, lambda_=0.0)
        for orig, smooth in zip(values, result):
            assert abs(orig - smooth) < 0.01

    def test_high_smoothing(self):
        """Large lambda should produce smoother (less variable) values."""
        values = [0.01, 0.08, 0.02, 0.09, 0.01]
        result = whittaker_henderson_graduation(values, lambda_=100.0)
        # Smoothed values should have less variance than original
        orig_var = sum((v - sum(values) / len(values)) ** 2 for v in values)
        smooth_var = sum((v - sum(result) / len(result)) ** 2 for v in result)
        assert smooth_var <= orig_var * 1.01  # Allow tiny numerical error

    def test_clamping(self):
        """Values should be clamped to [0, 1]."""
        values = [0.5, 0.6, 0.7, 0.8, 0.9]
        result = whittaker_henderson_graduation(values)
        for v in result:
            assert 0.0 <= v <= 1.0


class TestApplyGraduation:
    """Tests for apply_graduation."""

    def test_applies_graduation(self):
        ages = [0, 30, 60, 90]
        l_values = [100, 90, 80, 70]
        d_values = [10, 10, 10, 5]

        table = compute_life_table(ages, l_values, d_values)
        graduated = apply_graduation(table, lambda_=1.0)
        assert len(graduated.rows) == len(table.rows)
        # Graduated values should be set
        for row in graduated.rows:
            assert row.q_v_graduated >= 0.0


class TestFormatLifeTable:
    """Tests for format_life_table."""

    def test_format_output(self):
        ages = [0, 30]
        l_values = [100, 90]
        d_values = [10, 5]

        table = compute_life_table(ages, l_values, d_values, cohort_id="test")
        output = format_life_table(table)
        assert "Life Table for CVE Cohort: test" in output
        assert "100" in output
