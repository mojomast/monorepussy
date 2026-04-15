"""Tests for the Paris' Law calibration module."""

import math
import pytest

from fatigue.paris import (
    paris_law,
    log_paris_law,
    calibrate_material_constants,
    calibrate_from_history,
    calibrate_per_module,
    estimate_endurance_limit,
    estimate_fracture_toughness,
)
from fatigue.models import MaterialConstants


class TestParisLaw:
    """Tests for the Paris' Law equation."""

    def test_basic_growth_rate(self):
        """Test basic crack growth rate calculation."""
        # da/dN = C * (ΔK)^m
        rate = paris_law(10.0, C=0.01, m=2.0)
        # 0.01 * 10^2 = 0.01 * 100 = 1.0
        assert rate == pytest.approx(1.0)

    def test_zero_delta_K(self):
        """Test that zero ΔK produces zero growth."""
        rate = paris_law(0.0, C=0.01, m=2.0)
        assert rate == 0.0

    def test_negative_delta_K(self):
        """Test that negative ΔK produces zero growth."""
        rate = paris_law(-5.0, C=0.01, m=2.0)
        assert rate == 0.0

    def test_higher_m_exponential_effect(self):
        """Test that higher m exponent causes exponential growth."""
        rate_low_m = paris_law(10.0, C=0.01, m=2.0)
        rate_high_m = paris_law(10.0, C=0.01, m=4.0)
        # Higher m should give much higher growth rate
        assert rate_high_m > rate_low_m * 10

    def test_higher_C_linear_effect(self):
        """Test that higher C proportionally increases growth."""
        rate_low_C = paris_law(10.0, C=0.01, m=2.0)
        rate_high_C = paris_law(10.0, C=0.02, m=2.0)
        assert rate_high_C == pytest.approx(rate_low_C * 2.0)

    def test_delta_K_1(self):
        """Test with ΔK = 1 (growth rate equals C)."""
        rate = paris_law(1.0, C=0.015, m=2.5)
        assert rate == pytest.approx(0.015)


class TestLogParisLaw:
    """Tests for log-transformed Paris' Law."""

    def test_log_transform(self):
        """Test log-transformed calculation."""
        log_rate = log_paris_law(math.log(10.0), math.log(0.01), 2.0)
        # log(C) + m * log(ΔK) = log(0.01) + 2 * log(10)
        expected = math.log(0.01) + 2.0 * math.log(10.0)
        assert log_rate == pytest.approx(expected)


class TestCalibrateMaterialConstants:
    """Tests for material constant calibration."""

    def test_basic_calibration(self, calibration_data):
        """Test basic calibration with sample data."""
        delta_K_values = [d['delta_K'] for d in calibration_data]
        growth_rates = [d['growth_rate'] for d in calibration_data]

        material = calibrate_material_constants(delta_K_values, growth_rates)

        assert material.C > 0
        assert material.m > 0
        assert material.r_squared > 0

    def test_calibration_perfect_fit(self):
        """Test calibration with data that perfectly fits Paris' Law."""
        C_true = 0.005
        m_true = 2.0

        delta_K_values = [5.0, 10.0, 15.0, 20.0, 25.0]
        growth_rates = [C_true * (dk ** m_true) for dk in delta_K_values]

        material = calibrate_material_constants(delta_K_values, growth_rates)

        assert material.C == pytest.approx(C_true, rel=0.01)
        assert material.m == pytest.approx(m_true, rel=0.01)
        assert material.r_squared > 0.99

    def test_calibration_insufficient_data(self):
        """Test calibration with insufficient data points."""
        delta_K_values = [10.0]
        growth_rates = [1.0]

        material = calibrate_material_constants(delta_K_values, growth_rates)
        # Should return defaults
        assert material.C == 0.015
        assert material.m == 2.5

    def test_calibration_zero_values_filtered(self):
        """Test that zero values are filtered during calibration."""
        delta_K_values = [0.0, 10.0, 0.0, 20.0, 15.0]
        growth_rates = [0.0, 0.5, 0.0, 2.0, 1.0]

        material = calibrate_material_constants(delta_K_values, growth_rates)
        # Should still calibrate from valid data points
        assert material.C > 0
        assert material.m > 0

    def test_calibration_r_squared_range(self, calibration_data):
        """Test that R² is between 0 and 1."""
        delta_K_values = [d['delta_K'] for d in calibration_data]
        growth_rates = [d['growth_rate'] for d in calibration_data]

        material = calibrate_material_constants(delta_K_values, growth_rates)
        assert 0.0 <= material.r_squared <= 1.0

    def test_calibration_custom_thresholds(self, calibration_data):
        """Test calibration with custom K_Ic and K_e."""
        delta_K_values = [d['delta_K'] for d in calibration_data]
        growth_rates = [d['growth_rate'] for d in calibration_data]

        material = calibrate_material_constants(
            delta_K_values, growth_rates,
            K_Ic=35.0, K_e=10.0,
        )
        assert material.K_Ic == 35.0
        assert material.K_e == 10.0


class TestCalibrateFromHistory:
    """Tests for calibration from historical data."""

    def test_from_history(self, calibration_data):
        """Test calibration from historical data list."""
        material = calibrate_from_history(calibration_data)
        assert material.C > 0
        assert material.m > 0

    def test_from_history_empty(self):
        """Test calibration from empty history."""
        material = calibrate_from_history([])
        assert material.C == 0.015  # Default

    def test_from_history_missing_keys(self):
        """Test calibration with data missing required keys."""
        data = [{"delta_K": 10.0}, {"growth_rate": 1.0}]
        material = calibrate_from_history(data)
        # Should use defaults since no valid pairs
        assert material.C == 0.015


class TestCalibratePerModule:
    """Tests for per-module calibration."""

    def test_per_module(self):
        """Test per-module calibration."""
        module_data = {
            "core": [
                {"delta_K": 5.0, "growth_rate": 0.05},
                {"delta_K": 10.0, "growth_rate": 0.15},
                {"delta_K": 15.0, "growth_rate": 0.30},
            ],
            "payments": [
                {"delta_K": 20.0, "growth_rate": 2.0},
                {"delta_K": 30.0, "growth_rate": 8.0},
                {"delta_K": 40.0, "growth_rate": 25.0},
            ],
        }

        result = calibrate_per_module(module_data)

        assert "core" in result
        assert "payments" in result
        # Payments module should be more brittle (higher m)
        assert result["payments"].m >= result["core"].m


class TestEstimateEnduranceLimit:
    """Tests for endurance limit estimation."""

    def test_basic_estimation(self):
        """Test basic endurance limit estimation."""
        delta_K_values = [5.0, 10.0, 15.0, 20.0]
        growth_rates = [0.0, 0.1, 0.5, 2.0]

        K_e = estimate_endurance_limit(delta_K_values, growth_rates)
        # Should be below the minimum ΔK with positive growth
        assert K_e < 10.0

    def test_no_positive_growth(self):
        """Test when there's no positive growth."""
        delta_K_values = [5.0, 10.0]
        growth_rates = [0.0, 0.0]

        K_e = estimate_endurance_limit(delta_K_values, growth_rates)
        assert K_e == 8.2  # Default


class TestEstimateFractureToughness:
    """Tests for fracture toughness estimation."""

    def test_basic_estimation(self):
        """Test basic fracture toughness estimation."""
        delta_K_values = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0]
        growth_rates = [0.05, 0.1, 0.2, 0.4, 0.8, 2.0, 8.0]

        K_Ic = estimate_fracture_toughness(delta_K_values, growth_rates)
        assert K_Ic > 0

    def test_insufficient_data(self):
        """Test with insufficient data."""
        delta_K_values = [10.0]
        growth_rates = [1.0]

        K_Ic = estimate_fracture_toughness(delta_K_values, growth_rates)
        assert K_Ic == 28.0  # Default

    def test_no_data(self):
        """Test with no data."""
        K_Ic = estimate_fracture_toughness([], [])
        assert K_Ic == 28.0  # Default
