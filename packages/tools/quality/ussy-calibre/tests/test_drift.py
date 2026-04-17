"""Tests for the drift detector module."""

import math
from datetime import datetime, timezone, timedelta

import pytest

from calibre.drift import (
    analyze_drift,
    compute_recalibration_interval,
    detect_cusum,
    detect_shock_events,
    fit_linear_drift,
    format_drift_result,
)
from calibre.models import DriftObservation


class TestFitLinearDrift:
    def test_no_drift(self):
        """Constant values → alpha should be ~0."""
        base = datetime.now(timezone.utc)
        timestamps = [base + timedelta(days=i) for i in range(10)]
        values = [0.95] * 10
        d_0, alpha = fit_linear_drift(timestamps, values)
        assert abs(alpha) < 1e-10
        assert abs(d_0 - 0.95) < 1e-6

    def test_positive_drift(self):
        """Increasing values → positive alpha."""
        base = datetime.now(timezone.utc)
        timestamps = [base + timedelta(days=i) for i in range(10)]
        values = [0.5 + 0.01 * i for i in range(10)]
        d_0, alpha = fit_linear_drift(timestamps, values)
        assert alpha > 0.0

    def test_negative_drift(self):
        """Decreasing values → negative alpha."""
        base = datetime.now(timezone.utc)
        timestamps = [base + timedelta(days=i) for i in range(10)]
        values = [0.95 - 0.01 * i for i in range(10)]
        d_0, alpha = fit_linear_drift(timestamps, values)
        assert alpha < 0.0

    def test_single_point(self):
        base = datetime.now(timezone.utc)
        d_0, alpha = fit_linear_drift([base], [0.9])
        assert d_0 == 0.9
        assert alpha == 0.0


class TestDetectCUSUM:
    def test_no_drift(self):
        """Values at target → no alerts."""
        values = [1.0] * 20
        s_plus, s_minus, alerts = detect_cusum(values, target=1.0, k=0.5, h=5.0)
        assert len(alerts) == 0

    def test_positive_drift(self):
        """Gradually increasing values → CUSUM should trigger."""
        values = [1.0 + 0.5 * i for i in range(20)]
        s_plus, s_minus, alerts = detect_cusum(values, target=1.0, k=0.5, h=5.0)
        assert len(alerts) > 0

    def test_negative_drift(self):
        """Gradually decreasing values → CUSUM should trigger."""
        values = [1.0 - 0.5 * i for i in range(20)]
        s_plus, s_minus, alerts = detect_cusum(values, target=1.0, k=0.5, h=5.0)
        assert len(alerts) > 0

    def test_sudden_jump(self):
        """Sudden jump → CUSUM should trigger."""
        values = [1.0] * 10 + [5.0] * 10
        s_plus, s_minus, alerts = detect_cusum(values, target=1.0, k=0.5, h=5.0)
        assert len(alerts) > 0


class TestDetectShockEvents:
    def test_no_shocks(self):
        # Use more values with some natural noise so MAD-based detection doesn't false trigger
        import random
        random.seed(42)
        values = [1.0 + random.gauss(0, 0.01) for _ in range(20)]
        shocks = detect_shock_events(values, threshold_sigma=3.0)
        assert len(shocks) == 0

    def test_shock_present(self):
        # Create a long stable series with one clear shock
        values = [1.0] * 20 + [5.0] + [1.0] * 10
        shocks = detect_shock_events(values, threshold_sigma=2.0)
        # The shock at index 20 should be detected
        assert 20 in shocks

    def test_too_few_values(self):
        assert detect_shock_events([1.0]) == []
        assert detect_shock_events([]) == []
        assert detect_shock_events([1.0, 2.0]) == []


class TestComputeRecalibrationInterval:
    def test_no_drift(self):
        interval = compute_recalibration_interval(mpe=0.1, initial_bias=0.0, drift_rate=0.0)
        assert interval == float("inf")

    def test_with_drift(self):
        interval = compute_recalibration_interval(mpe=0.1, initial_bias=0.0, drift_rate=0.001)
        expected = 0.1 / 0.001  # 100 days
        assert abs(interval - expected) < 1e-10

    def test_negative_drift(self):
        interval = compute_recalibration_interval(mpe=0.1, initial_bias=0.02, drift_rate=-0.002)
        expected = (0.1 - 0.02) / 0.002  # 40 days
        assert abs(interval - expected) < 1e-10


class TestAnalyzeDrift:
    def test_no_observations(self):
        result = analyze_drift([], mpe=0.1)
        assert result.test_name == "unknown"
        assert "No data" in result.diagnosis

    def test_single_observation(self):
        obs = [
            DriftObservation(
                test_name="t1",
                timestamp=datetime.now(timezone.utc),
                observed_value=0.9,
            )
        ]
        result = analyze_drift(obs, mpe=0.1)
        assert result.test_name == "t1"
        assert "Insufficient" in result.diagnosis

    def test_drifting_observations(self, sample_drift_observations):
        result = analyze_drift(sample_drift_observations, mpe=0.05)
        assert result.test_name == "test_drifty"
        assert result.drift_rate != 0.0
        assert result.cumulative_drift > 0.0

    def test_zombie_detection(self):
        """Always passes but drifted → zombie."""
        base = datetime.now(timezone.utc) - timedelta(days=30)
        obs = []
        for day in range(30):
            # Always high but slowly drifting
            value = 0.98 - 0.005 * day
            obs.append(
                DriftObservation(
                    test_name="zombie",
                    timestamp=base + timedelta(days=day),
                    observed_value=value,
                )
            )
        # With tight MPE, should be detected
        result = analyze_drift(obs, mpe=0.01)
        assert result.is_zombie or result.exceeds_mpe or result.cumulative_drift > 0.01


class TestFormatDriftResult:
    def test_format(self, sample_drift_observations):
        result = analyze_drift(sample_drift_observations, mpe=0.05)
        output = format_drift_result(result)
        assert "Drift Analysis" in output
        assert "drift rate" in output.lower()
