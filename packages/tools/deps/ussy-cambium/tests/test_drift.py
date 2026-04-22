"""Tests for Cambium drift module."""

from __future__ import annotations

import pytest

from cambium.drift import (
    classify_drift_zone,
    compute_drift_debt,
    drift_forecast,
    format_drift_report,
)
from cambium.models import CompatibilityZone, DriftDebt


class TestComputeDriftDebt:
    """Tests for compute_drift_debt."""

    def test_basic_creation(self):
        dd = compute_drift_debt(
            delta_behavior=0.02,
            delta_contract=0.01,
            delta_environment=0.005,
        )
        assert dd.delta_0 == pytest.approx(0.035)

    def test_default_params(self):
        dd = compute_drift_debt()
        assert dd.delta_0 == pytest.approx(0.0)
        assert dd.lambda_s == 6.0
        assert dd.d_critical == 1.0


class TestClassifyDriftZone:
    """Tests for classify_drift_zone."""

    def test_safe_zone(self):
        dd = compute_drift_debt(
            delta_behavior=0.001,
            delta_contract=0.001,
            delta_environment=0.001,
            lambda_s=6.0,
            d_critical=1.0,
        )
        analysis = classify_drift_zone(dd)
        assert analysis["zone"] == "safe"
        assert analysis["breakage_time_months"] is None

    def test_doomed_zone(self):
        dd = compute_drift_debt(
            delta_behavior=0.1,
            delta_contract=0.1,
            delta_environment=0.1,
            lambda_s=6.0,
            d_critical=1.0,
        )
        analysis = classify_drift_zone(dd)
        assert analysis["zone"] == "doomed"
        assert analysis["breakage_time_months"] is not None
        assert analysis["breakage_time_months"] > 0


class TestDriftForecast:
    """Tests for drift_forecast."""

    def test_basic_forecast(self):
        dd = compute_drift_debt(
            delta_behavior=0.02,
            delta_contract=0.01,
            delta_environment=0.005,
        )
        forecast = drift_forecast(dd, months=12, step=3)
        assert len(forecast) == 5  # 0, 3, 6, 9, 12
        # Drift should be monotonically increasing
        for i in range(1, len(forecast)):
            assert forecast[i]["drift_debt"] >= forecast[i - 1]["drift_debt"]

    def test_zero_drift_forecast(self):
        dd = compute_drift_debt()
        forecast = drift_forecast(dd, months=6)
        for point in forecast:
            assert point["drift_debt"] == pytest.approx(0.0)


class TestFormatDriftReport:
    """Tests for format_drift_report."""

    def test_safe_report(self):
        dd = compute_drift_debt(
            delta_behavior=0.001,
            delta_contract=0.001,
            delta_environment=0.001,
        )
        report = format_drift_report(dd)
        assert "SAFE" in report

    def test_doomed_report(self):
        dd = compute_drift_debt(
            delta_behavior=0.1,
            delta_contract=0.1,
            delta_environment=0.1,
            lambda_s=6.0,
            d_critical=1.0,
        )
        report = format_drift_report(dd)
        assert "DOOMED" in report
        assert "Breakage predicted" in report
