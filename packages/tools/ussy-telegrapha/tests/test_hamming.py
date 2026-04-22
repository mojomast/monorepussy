"""Tests for hamming module."""

import math
import pytest

from ussy_telegrapha.hamming import (
    compute_arq_metrics,
    compute_fec_metrics,
    compute_break_even_error_rate,
    compute_hamming_distance,
    compute_correction_capacity,
    analyze_hamming,
    format_hamming_report,
    hamming_to_dict,
)


class TestComputeARQMetrics:
    """Tests for ARQ metrics computation."""

    def test_low_error_rate(self):
        expected, latency, bw = compute_arq_metrics(0.03, 6)
        assert expected == pytest.approx(1.0 / 0.97, rel=1e-4)
        assert latency == pytest.approx(6 * 1.0 / 0.97, rel=1e-4)
        assert bw == pytest.approx(3.0)

    def test_zero_error_rate(self):
        expected, latency, bw = compute_arq_metrics(0.0, 6)
        assert expected == pytest.approx(1.0)
        assert latency == pytest.approx(6.0)
        assert bw == pytest.approx(0.0)

    def test_high_error_rate(self):
        expected, latency, bw = compute_arq_metrics(0.5, 1)
        assert expected == pytest.approx(2.0)
        assert bw == pytest.approx(50.0)

    def test_full_error_rate(self):
        expected, latency, bw = compute_arq_metrics(1.0, 1)
        assert expected == float("inf")


class TestComputeFECMetrics:
    """Tests for FEC metrics computation."""

    def test_32_code(self):
        p_fail, latency, bw = compute_fec_metrics(0.03, 3, 2)
        # P(failure) = C(3,0)*(0.03)^3 + C(3,1)*(0.03)^2*(0.97) ... no wait
        # P(failure) = P(fewer than 2 succeed) = P(0 succeed) + P(1 succeed)
        # P(0 succeed) = (0.03)^3
        # P(1 succeed) = C(3,1) * (0.97) * (0.03)^2
        p_0 = 0.03 ** 3
        p_1 = 3 * 0.97 * (0.03 ** 2)
        expected_pfail = p_0 + p_1
        assert p_fail == pytest.approx(expected_pfail, rel=1e-4)
        assert latency == 3.0
        assert bw == pytest.approx(50.0)

    def test_zero_error_rate(self):
        p_fail, latency, bw = compute_fec_metrics(0.0, 3, 2)
        assert p_fail == pytest.approx(0.0)
        assert latency == 3.0

    def test_high_error_rate(self):
        p_fail, latency, bw = compute_fec_metrics(0.5, 3, 2)
        assert p_fail > 0
        assert p_fail < 1.0


class TestComputeHammingDistance:
    """Tests for schema Hamming distance."""

    def test_identical_schemas(self):
        dist = compute_hamming_distance(["a", "b", "c"], ["a", "b", "c"])
        assert dist == 0

    def test_one_field_diff(self):
        dist = compute_hamming_distance(["a", "b", "c"], ["a", "b", "d"])
        assert dist == 2  # c removed, d added

    def test_extra_fields(self):
        dist = compute_hamming_distance(["a", "b"], ["a", "b", "c"])
        assert dist == 1  # c added

    def test_completely_different(self):
        dist = compute_hamming_distance(["a", "b"], ["c", "d"])
        assert dist == 4  # a,b removed; c,d added


class TestComputeCorrectionCapacity:
    """Tests for correction capacity computation."""

    def test_dmin3(self):
        assert compute_correction_capacity(3) == 1

    def test_dmin5(self):
        assert compute_correction_capacity(5) == 2

    def test_dmin7(self):
        assert compute_correction_capacity(7) == 3

    def test_dmin1(self):
        assert compute_correction_capacity(1) == 0

    def test_dmin2(self):
        assert compute_correction_capacity(2) == 0


class TestAnalyzeHamming:
    """Tests for full Hamming analysis."""

    def test_low_error_arq_preferred(self):
        result = analyze_hamming(
            error_rate=0.03,
            pipeline_length=6,
            target_reliability=0.999,
        )
        assert result.preferred == "ARQ"
        assert result.arq_expected_transmissions > 1.0

    def test_fec_failure_prob(self):
        result = analyze_hamming(error_rate=0.03, pipeline_length=6)
        assert result.fec_failure_prob < 0.01  # Should be very low

    def test_schema_drift_within_capacity(self):
        result = analyze_hamming(
            error_rate=0.03,
            pipeline_length=6,
            schema_drift_distance=1,
            min_hamming_distance=3,
        )
        assert result.correction_capacity == 1
        assert any("within correction" in r.lower() for r in result.recommendations)

    def test_schema_drift_at_limit(self):
        result = analyze_hamming(
            error_rate=0.03,
            pipeline_length=6,
            schema_drift_distance=2,
            min_hamming_distance=3,
        )
        assert any("limit" in r.lower() or "warning" in r.lower()
                    for r in result.recommendations)

    def test_schema_drift_exceeds_capacity(self):
        result = analyze_hamming(
            error_rate=0.03,
            pipeline_length=6,
            schema_drift_distance=3,
            min_hamming_distance=3,
        )
        assert any("critical" in r.lower() for r in result.recommendations)

    def test_break_even_exists(self):
        result = analyze_hamming(error_rate=0.03, pipeline_length=6)
        assert result.break_even_error_rate > 0


class TestFormatReport:
    """Tests for report formatting."""

    def test_report_contains_decision(self):
        result = analyze_hamming(error_rate=0.03, pipeline_length=6)
        report = format_hamming_report(result)
        assert "ARQ" in report
        assert "FEC" in report
        assert "Decision" in report

    def test_report_with_drift(self):
        result = analyze_hamming(
            error_rate=0.03, pipeline_length=6, schema_drift_distance=2
        )
        report = format_hamming_report(result)
        assert "schema drift" in report.lower()


class TestHammingToDict:
    """Tests for JSON serialization."""

    def test_dict_keys(self):
        result = analyze_hamming(error_rate=0.03, pipeline_length=6)
        data = hamming_to_dict(result)
        assert "arq" in data
        assert "fec" in data
        assert "preferred" in data
        assert "error_rate" in data
