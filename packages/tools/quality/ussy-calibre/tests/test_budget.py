"""Tests for the uncertainty budget module."""

import math

import pytest

from calibre.budget import (
    build_budget,
    budget_from_test_runs,
    compute_combined_uncertainty,
    compute_expanded_uncertainty,
    find_dominant_source,
    format_budget,
)
from calibre.models import (
    TestResult,
    TestRun,
    UncertaintyBudget,
    UncertaintySource,
)


class TestComputeCombinedUncertainty:
    def test_no_sources(self):
        assert compute_combined_uncertainty([]) == 0.0

    def test_single_source(self):
        sources = [
            UncertaintySource(name="s1", uncertainty_value=0.1, sensitivity_coefficient=1.0),
        ]
        result = compute_combined_uncertainty(sources)
        assert abs(result - 0.1) < 1e-10

    def test_two_uncorrelated_sources(self):
        sources = [
            UncertaintySource(name="s1", uncertainty_value=0.3, sensitivity_coefficient=1.0),
            UncertaintySource(name="s2", uncertainty_value=0.4, sensitivity_coefficient=1.0),
        ]
        result = compute_combined_uncertainty(sources)
        expected = math.sqrt(0.3**2 + 0.4**2)
        assert abs(result - expected) < 1e-10

    def test_correlated_sources(self):
        sources = [
            UncertaintySource(
                name="s1", uncertainty_value=0.3, sensitivity_coefficient=1.0,
                correlation_with="s2", correlation_coefficient=0.5,
            ),
            UncertaintySource(
                name="s2", uncertainty_value=0.4, sensitivity_coefficient=1.0,
            ),
        ]
        result = compute_combined_uncertainty(sources)
        # variance = 0.09 + 0.16 + 2*1*1*0.3*0.4*0.5 = 0.09+0.16+0.12 = 0.37
        expected = math.sqrt(0.37)
        assert abs(result - expected) < 1e-10


class TestComputeExpandedUncertainty:
    def test_k2(self):
        assert abs(compute_expanded_uncertainty(0.1, 2.0) - 0.2) < 1e-10

    def test_k3(self):
        assert abs(compute_expanded_uncertainty(0.1, 3.0) - 0.3) < 1e-10


class TestFindDominantSource:
    def test_empty(self):
        assert find_dominant_source([]) == ""

    def test_single(self):
        sources = [
            UncertaintySource(name="s1", uncertainty_value=0.5, sensitivity_coefficient=1.0),
        ]
        assert find_dominant_source(sources) == "s1"

    def test_dominant(self):
        sources = [
            UncertaintySource(name="small", uncertainty_value=0.01, sensitivity_coefficient=1.0),
            UncertaintySource(name="big", uncertainty_value=0.5, sensitivity_coefficient=2.0),
        ]
        assert find_dominant_source(sources) == "big"


class TestBuildBudget:
    def test_builds_complete_budget(self):
        sources = [
            UncertaintySource(name="s1", uncertainty_value=0.1, sensitivity_coefficient=1.0),
        ]
        budget = build_budget("test_measurand", sources)
        assert budget.measurand == "test_measurand"
        assert abs(budget.combined_uncertainty - 0.1) < 1e-10
        assert abs(budget.expanded_uncertainty - 0.2) < 1e-10
        assert budget.dominant_source == "s1"

    def test_empty_sources(self):
        budget = build_budget("empty", [])
        assert budget.combined_uncertainty == 0.0
        assert budget.dominant_source == ""


class TestBudgetFromTestRuns:
    def test_no_runs(self):
        budget = budget_from_test_runs("mod", [])
        assert budget.measurand == "mod"
        assert budget.combined_uncertainty == 0.0

    def test_with_runs(self, sample_test_runs):
        budget = budget_from_test_runs("auth", sample_test_runs)
        assert budget.measurand == "auth"
        assert budget.combined_uncertainty >= 0.0
        assert len(budget.sources) == 5
        assert budget.dominant_source != ""


class TestFormatBudget:
    def test_format_output(self):
        sources = [
            UncertaintySource(name="s1", uncertainty_value=0.1, sensitivity_coefficient=1.0),
        ]
        budget = build_budget("test", sources)
        output = format_budget(budget)
        assert "Uncertainty Budget" in output
        assert "s1" in output
        assert "Combined uncertainty" in output
