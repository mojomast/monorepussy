"""Tests for capacity module."""

import math
import pytest

from telegrapha.capacity import (
    compute_snr,
    compute_shannon_capacity,
    compute_utilization,
    compute_statistical_multiplexing_gain,
    analyze_capacity,
    format_capacity_report,
    capacity_to_dict,
)


class TestComputeSNR:
    """Tests for Signal-to-Noise Ratio computation."""

    def test_basic_snr(self):
        assert compute_snr(420, 80) == pytest.approx(5.25)

    def test_zero_noise(self):
        assert compute_snr(420, 0) == float("inf")

    def test_high_noise(self):
        snr = compute_snr(100, 200)
        assert snr == pytest.approx(0.5)


class TestComputeShannonCapacity:
    """Tests for Shannon-Hartley capacity computation."""

    def test_basic_capacity(self):
        # C = 500 * log2(1 + 5.25) = 500 * log2(6.25)
        capacity = compute_shannon_capacity(500, 5.25)
        expected = 500 * math.log2(6.25)
        assert capacity == pytest.approx(expected, rel=1e-6)

    def test_zero_bandwidth(self):
        assert compute_shannon_capacity(0, 5.25) == pytest.approx(0.0)

    def test_zero_snr(self):
        assert compute_shannon_capacity(500, 0) == pytest.approx(0.0)

    def test_infinite_snr(self):
        # With infinite SNR, capacity is infinite
        capacity = compute_shannon_capacity(500, float("inf"))
        assert capacity == float("inf")


class TestComputeUtilization:
    """Tests for utilization computation."""

    def test_basic_utilization(self):
        util = compute_utilization(420, 1299)
        assert util == pytest.approx(420 / 1299 * 100, rel=1e-6)

    def test_full_utilization(self):
        assert compute_utilization(100, 100) == pytest.approx(100.0)

    def test_zero_capacity(self):
        assert compute_utilization(100, 0) == pytest.approx(0.0)


class TestStatisticalMultiplexingGain:
    """Tests for statistical multiplexing gain."""

    def test_single_worker(self):
        gain = compute_statistical_multiplexing_gain(100, 1, 0.6)
        assert gain >= 1.0

    def test_multiple_workers(self):
        gain = compute_statistical_multiplexing_gain(100, 50, 0.6)
        assert gain > 1.0

    def test_zero_utilization(self):
        gain = compute_statistical_multiplexing_gain(100, 10, 0.0)
        assert gain == 1.0

    def test_full_utilization(self):
        gain = compute_statistical_multiplexing_gain(100, 10, 1.0)
        assert gain == 1.0


class TestAnalyzeCapacity:
    """Tests for full capacity analysis."""

    def test_basic_analysis(self):
        result = analyze_capacity(
            bandwidth=500,
            signal_rate=420,
            noise_rate=80,
        )
        assert result.bandwidth == 500
        assert result.signal_rate == 420
        assert result.noise_rate == 80
        assert result.snr == pytest.approx(5.25)
        assert result.theoretical_ceiling > 0
        assert 0 < result.utilization_pct < 100

    def test_low_utilization_recommendation(self):
        result = analyze_capacity(
            bandwidth=10000,
            signal_rate=100,
            noise_rate=10,
        )
        assert result.utilization_pct < 40
        assert any("reducing" in r.lower() for r in result.recommendations)

    def test_high_utilization_warning(self):
        result = analyze_capacity(
            bandwidth=100,
            signal_rate=95,
            noise_rate=80,  # High noise → low capacity → high utilization
        )
        assert result.utilization_pct > 80

    def test_high_noise_warning(self):
        result = analyze_capacity(
            bandwidth=500,
            signal_rate=100,
            noise_rate=50,  # 50% of signal
        )
        assert any("noise" in r.lower() for r in result.recommendations)

    def test_zero_noise(self):
        result = analyze_capacity(500, 420, 0)
        assert result.snr == float("inf")
        assert result.theoretical_ceiling == float("inf")

    def test_with_workers_and_utilization(self):
        result = analyze_capacity(
            bandwidth=500,
            signal_rate=420,
            noise_rate=80,
            num_workers=50,
            avg_worker_utilization=0.6,
        )
        assert result.multiplexing_gain >= 1.0


class TestFormatReport:
    """Tests for report formatting."""

    def test_report_contains_capacity(self):
        result = analyze_capacity(500, 420, 80)
        report = format_capacity_report(result)
        assert "Shannon Capacity" in report
        assert "500" in report

    def test_report_json_serializable(self):
        import json
        result = analyze_capacity(500, 420, 80)
        data = capacity_to_dict(result)
        json_str = json.dumps(data)
        assert json_str


class TestCapacityToDict:
    """Tests for JSON serialization."""

    def test_dict_keys(self):
        result = analyze_capacity(500, 420, 80)
        data = capacity_to_dict(result)
        assert "bandwidth" in data
        assert "signal_rate" in data
        assert "noise_rate" in data
        assert "snr" in data
        assert "theoretical_ceiling" in data
        assert "utilization_pct" in data
