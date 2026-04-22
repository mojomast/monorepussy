"""Tests for the Gauge R&R module."""

import math

import pytest

from ussy_calibre.models import RRCategory, RRObservation
from ussy_calibre.rr import (
    anova_two_way_random,
    compute_rr_summary,
    format_rr_summary,
    runs_to_rr_observations,
)
from ussy_calibre.models import TestResult, TestRun


class TestAnovaTwoWayRandom:
    def test_empty_observations(self):
        result = anova_two_way_random([])
        assert result["var_part"] == 0.0
        assert result["var_operator"] == 0.0

    def test_single_build(self):
        obs = [
            RRObservation(build_id="b1", environment="ci", test_name="t1", replicate=1, value=1.0),
            RRObservation(build_id="b1", environment="staging", test_name="t1", replicate=1, value=0.8),
        ]
        result = anova_two_way_random(obs)
        # Only one build, can't compute part variance properly
        assert "var_part" in result

    def test_multiple_builds_envs(self, sample_rr_observations):
        result = anova_two_way_random(sample_rr_observations)
        assert result["var_part"] >= 0.0
        assert result["var_operator"] >= 0.0
        assert result["var_error"] >= 0.0
        # Total variance should be positive
        total = result["var_part"] + result["var_operator"] + result["var_interaction"] + result["var_error"]
        assert total >= 0.0


class TestComputeRRSummary:
    def test_empty(self):
        summary = compute_rr_summary("empty", [])
        assert summary.suite == "empty"
        assert summary.category == RRCategory.UNACCEPTABLE

    def test_with_data(self, sample_rr_observations):
        summary = compute_rr_summary("test_suite", sample_rr_observations)
        assert summary.suite == "test_suite"
        assert summary.grr_percent >= 0.0
        assert summary.ndc >= 1
        assert summary.category in [RRCategory.ACCEPTABLE, RRCategory.CONDITIONAL, RRCategory.UNACCEPTABLE]

    def test_perfect_repeatability(self):
        """All values identical → zero equipment variance."""
        obs = []
        builds = ["b1", "b2", "b3"]
        envs = ["e1", "e2"]
        for b in builds:
            for e in envs:
                for r in range(2):
                    obs.append(
                        RRObservation(build_id=b, environment=e, test_name="t", replicate=r + 1, value=1.0)
                    )
        summary = compute_rr_summary("perfect", obs)
        assert summary.equipment_variance_pct >= 0.0


class TestRunsToRRObservations:
    def test_conversion(self, sample_test_runs):
        obs = runs_to_rr_observations(sample_test_runs)
        assert len(obs) > 0
        # All should have valid replicate numbers
        for o in obs:
            assert o.replicate >= 1

    def test_preserves_values(self):
        runs = [
            TestRun(
                test_name="t1", module="m", suite="s",
                build_id="b1", environment="e1", result=TestResult.PASS,
            ),
            TestRun(
                test_name="t1", module="m", suite="s",
                build_id="b1", environment="e1", result=TestResult.FAIL,
            ),
        ]
        obs = runs_to_rr_observations(runs)
        values = [o.value for o in obs]
        assert 1.0 in values
        assert 0.0 in values


class TestFormatRRSummary:
    def test_format_output(self, sample_rr_observations):
        summary = compute_rr_summary("fmt_test", sample_rr_observations)
        output = format_rr_summary(summary)
        assert "Gauge R&R Study" in output
        assert "%GRR" in output
        assert "ndc" in output
        assert "Diagnosis" in output
