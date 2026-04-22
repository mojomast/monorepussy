"""Tests for the uncertainty classifier module."""

import math

import pytest

from ussy_calibre.classifier import (
    classify_test,
    compute_combined_ab_uncertainty,
    compute_type_a_uncertainty,
    compute_type_b_uncertainty_rectangular,
    compute_type_b_uncertainty_triangular,
    format_classification,
)
from ussy_calibre.models import TestResult, TestRun, UncertaintyType


class TestComputeTypeAUncertainty:
    def test_single_observation(self):
        assert compute_type_a_uncertainty([1.0]) == 0.0

    def test_empty(self):
        assert compute_type_a_uncertainty([]) == 0.0

    def test_multiple_observations(self):
        obs = [1.0, 0.9, 1.0, 0.9, 1.0]
        u_a = compute_type_a_uncertainty(obs)
        assert u_a > 0.0

    def test_identical_observations(self):
        obs = [1.0, 1.0, 1.0]
        u_a = compute_type_a_uncertainty(obs)
        assert u_a == 0.0

    def test_formula(self):
        """u_A = s(x) / sqrt(n)"""
        obs = [0.8, 0.9, 1.0]
        n = len(obs)
        mean = sum(obs) / n
        var = sum((x - mean) ** 2 for x in obs) / (n - 1)
        expected = (var ** 0.5) / (n ** 0.5)
        u_a = compute_type_a_uncertainty(obs)
        assert abs(u_a - expected) < 1e-10


class TestComputeTypeBUncertainty:
    def test_rectangular(self):
        """u_B = a / sqrt(3)"""
        result = compute_type_b_uncertainty_rectangular(1.0)
        assert abs(result - 1.0 / math.sqrt(3)) < 1e-10

    def test_triangular(self):
        """u_B = a / sqrt(6)"""
        result = compute_type_b_uncertainty_triangular(1.0)
        assert abs(result - 1.0 / math.sqrt(6)) < 1e-10

    def test_zero_half_width(self):
        assert compute_type_b_uncertainty_rectangular(0.0) == 0.0
        assert compute_type_b_uncertainty_triangular(0.0) == 0.0


class TestComputeCombinedABUncertainty:
    def test_zero_correlation(self):
        result = compute_combined_ab_uncertainty(0.3, 0.4, 0.0)
        expected = math.sqrt(0.09 + 0.16)
        assert abs(result - expected) < 1e-10

    def test_positive_correlation(self):
        result = compute_combined_ab_uncertainty(0.3, 0.4, 0.5)
        variance = 0.09 + 0.16 + 2 * 0.5 * 0.3 * 0.4
        expected = math.sqrt(variance)
        assert abs(result - expected) < 1e-10

    def test_zero_uncertainties(self):
        result = compute_combined_ab_uncertainty(0.0, 0.0, 0.0)
        assert result == 0.0


class TestClassifyTest:
    def test_no_data(self):
        result = classify_test([], "test_missing")
        assert result.test_name == "test_missing"
        assert "No data" in result.remediation

    def test_type_a_dominant(self):
        """Similar failure rates across environments → Type A."""
        runs = []
        for env in ["ci", "staging", "local"]:
            for i in range(10):
                result = TestResult.PASS if i % 4 != 0 else TestResult.FAIL
                runs.append(
                    TestRun(
                        test_name="test_race",
                        module="m", suite="s",
                        build_id="b1", environment=env, result=result,
                    )
                )
        classification = classify_test(runs, "test_race")
        # Failure rates are similar across envs → likely Type A
        assert classification.combined_uncertainty > 0.0

    def test_type_b_dominant(self):
        """One environment always fails → Type B."""
        runs = []
        for env in ["ci", "staging"]:
            for i in range(10):
                if env == "staging":
                    result = TestResult.FAIL
                else:
                    result = TestResult.PASS
                runs.append(
                    TestRun(
                        test_name="test_env_issue",
                        module="m", suite="s",
                        build_id="b1", environment=env, result=result,
                    )
                )
        classification = classify_test(runs, "test_env_issue")
        # Significant env difference → Type B should be dominant
        assert classification.type_b_uncertainty > 0.0
        assert classification.dominant_type == UncertaintyType.TYPE_B


class TestFormatClassification:
    def test_format(self):
        runs = [
            TestRun(
                test_name="test_fmt", module="m", suite="s",
                build_id="b1", environment="e", result=TestResult.PASS,
            ),
            TestRun(
                test_name="test_fmt", module="m", suite="s",
                build_id="b1", environment="e", result=TestResult.FAIL,
            ),
        ]
        classification = classify_test(runs, "test_fmt")
        output = format_classification(classification)
        assert "Uncertainty Classification" in output
        assert "Type A" in output
        assert "Type B" in output
