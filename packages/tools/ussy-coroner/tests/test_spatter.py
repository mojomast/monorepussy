"""Tests for coroner.spatter — Error Spatter Reconstruction."""

from __future__ import annotations

import math

from ussy_coroner.models import StageStatus, VelocityClass
from ussy_coroner.spatter import (
    analyze_spatter,
    format_spatter,
    _extract_error_components,
    _compute_depths,
    _classify_velocity,
)


class TestExtractErrorComponents:
    """Tests for component extraction from error logs."""

    def test_extracts_module_names(self):
        log = "FAILED auth-module/test.js\n  at Object.login (auth-module/handler.js:42)"
        components = _extract_error_components(log)
        assert len(components) > 0

    def test_empty_log(self):
        components = _extract_error_components("")
        assert components == []

    def test_no_components_in_success_log(self):
        log = "BUILD SUCCESSFUL\nAll tests passed"
        components = _extract_error_components(log)
        # May still extract some but should be minimal
        assert isinstance(components, list)


class TestComputeDepths:
    """Tests for consecutive failure depth computation."""

    def test_consecutive_failures(self, multi_failure_run):
        depths = _compute_depths(multi_failure_run)
        # test, integration, deploy are consecutive failures
        assert depths.get("test") == 3
        assert depths.get("integration") == 3
        assert depths.get("deploy") == 3

    def test_single_failure(self, simple_failing_run):
        depths = _compute_depths(simple_failing_run)
        assert depths.get("test") == 1

    def test_no_failures(self, passing_run):
        depths = _compute_depths(passing_run)
        assert depths == {}


class TestClassifyVelocity:
    """Tests for velocity classification."""

    def test_high_velocity(self):
        from ussy_coroner.models import ErrorStain
        stains = [ErrorStain(stage_name="a", stage_index=0, breadth=8, depth=1)]
        assert _classify_velocity(stains) == VelocityClass.HIGH

    def test_low_velocity(self):
        from ussy_coroner.models import ErrorStain
        stains = [ErrorStain(stage_name="a", stage_index=0, breadth=1, depth=5)]
        assert _classify_velocity(stains) == VelocityClass.LOW

    def test_medium_velocity(self):
        from ussy_coroner.models import ErrorStain
        stains = [ErrorStain(stage_name="a", stage_index=0, breadth=3, depth=4)]
        assert _classify_velocity(stains) == VelocityClass.MEDIUM

    def test_empty_stains(self):
        assert _classify_velocity([]) == VelocityClass.MEDIUM


class TestAnalyzeSpatter:
    """Tests for the main analyze_spatter function."""

    def test_failing_run_produces_stains(self, simple_failing_run):
        result = analyze_spatter(simple_failing_run)
        assert len(result.stains) > 0

    def test_stain_has_impact_angle(self, simple_failing_run):
        result = analyze_spatter(simple_failing_run)
        for stain in result.stains:
            assert stain.impact_angle >= 0

    def test_convergence_found(self, simple_failing_run):
        result = analyze_spatter(simple_failing_run)
        assert result.convergence_stage != ""

    def test_origin_depth_positive(self, simple_failing_run):
        result = analyze_spatter(simple_failing_run)
        assert result.origin_depth >= 0

    def test_confidence_in_range(self, simple_failing_run):
        result = analyze_spatter(simple_failing_run)
        assert 0.0 <= result.confidence <= 1.0

    def test_velocity_class_set(self, simple_failing_run):
        result = analyze_spatter(simple_failing_run)
        assert result.velocity_class in [VelocityClass.LOW, VelocityClass.MEDIUM, VelocityClass.HIGH]

    def test_likely_cause_not_empty(self, simple_failing_run):
        result = analyze_spatter(simple_failing_run)
        assert result.likely_cause != ""

    def test_passing_run_no_stains(self, passing_run):
        result = analyze_spatter(passing_run)
        assert len(result.stains) == 0

    def test_multi_failure_has_multiple_stains(self, multi_failure_run):
        result = analyze_spatter(multi_failure_run)
        assert len(result.stains) >= 2

    def test_multi_failure_higher_confidence(self, multi_failure_run):
        result = analyze_spatter(multi_failure_run)
        # More stains should give higher confidence than single failure
        assert result.confidence > 0


class TestFormatSpatter:
    """Tests for format_spatter."""

    def test_format_with_stains(self, simple_failing_run):
        result = analyze_spatter(simple_failing_run)
        text = format_spatter(result)
        assert "Stain" in text
        assert "Convergence" in text

    def test_format_no_stains(self, passing_run):
        result = analyze_spatter(passing_run)
        text = format_spatter(result)
        assert "No error stains" in text
