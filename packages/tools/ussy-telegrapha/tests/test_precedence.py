"""Tests for precedence module."""

import pytest

from ussy_telegrapha.models import PrecedenceClass
from ussy_telegrapha.precedence import (
    compute_mg1_avg_wait,
    compute_system_stability,
    compute_residual_service_time,
    find_optimal_class_count,
    analyze_precedence,
    format_precedence_report,
    precedence_to_dict,
)


@pytest.fixture
def standard_classes():
    """Standard 4-class precedence system (stable: rho < 1.0)."""
    return [
        PrecedenceClass(
            name="circuit-breaker signals",
            label="FLASH",
            arrival_rate=0.5 / 60.0,
            service_time=0.050,
            preemption_overhead=0.003,
        ),
        PrecedenceClass(
            name="payment processing",
            label="IMMEDIATE",
            arrival_rate=30.0 / 60.0,
            service_time=0.200,
        ),
        PrecedenceClass(
            name="user-facing requests",
            label="PRIORITY",
            arrival_rate=100.0 / 60.0,
            service_time=0.100,
        ),
        PrecedenceClass(
            name="batch analytics",
            label="ROUTINE",
            arrival_rate=10.0 / 60.0,
            service_time=0.500,
        ),
    ]


@pytest.fixture
def unstable_classes():
    """Classes that make the system unstable (rho >= 1)."""
    return [
        PrecedenceClass(
            name="heavy-load",
            label="ROUTINE",
            arrival_rate=100.0,
            service_time=0.02,
        ),
    ]


class TestComputeMG1AvgWait:
    """Tests for M/G/1 average wait computation."""

    def test_basic_wait(self):
        wait = compute_mg1_avg_wait(
            arrival_rate=1.0,
            service_time=0.1,
            higher_class_load=0.0,
            residual_service=0.01,
        )
        assert wait > 0

    def test_higher_load_increases_wait(self):
        wait_low = compute_mg1_avg_wait(1.0, 0.1, 0.0, 0.01)
        wait_high = compute_mg1_avg_wait(1.0, 0.1, 0.5, 0.01)
        assert wait_high > wait_low

    def test_unstable_system(self):
        wait = compute_mg1_avg_wait(1.0, 0.1, 1.0, 0.01)
        assert wait == float("inf")


class TestComputeSystemStability:
    """Tests for system stability computation."""

    def test_stable_system(self, standard_classes):
        rho = compute_system_stability(standard_classes)
        assert rho < 1.0

    def test_unstable_system(self, unstable_classes):
        rho = compute_system_stability(unstable_classes)
        assert rho >= 1.0

    def test_empty_system(self):
        rho = compute_system_stability([])
        assert rho == 0.0


class TestComputeResidualServiceTime:
    """Tests for residual service time computation."""

    def test_nonzero_residual(self, standard_classes):
        r = compute_residual_service_time(standard_classes)
        assert r > 0

    def test_empty_classes(self):
        r = compute_residual_service_time([])
        assert r == 0.0


class TestFindOptimalClassCount:
    """Tests for optimal class count finder."""

    def test_with_standard_classes(self, standard_classes):
        count = find_optimal_class_count(standard_classes)
        assert count >= 1

    def test_single_class(self):
        classes = [PrecedenceClass(name="only", label="ROUTINE", arrival_rate=1.0, service_time=0.5)]
        count = find_optimal_class_count(classes)
        assert count >= 1

    def test_marginal_threshold(self, standard_classes):
        count = find_optimal_class_count(standard_classes, marginal_threshold=0.5)
        # With high threshold, fewer classes are optimal
        assert count >= 1


class TestAnalyzePrecedence:
    """Tests for full precedence analysis."""

    def test_standard_analysis(self, standard_classes):
        result = analyze_precedence(standard_classes)
        assert result.is_stable is True
        assert result.system_stability < 1.0
        assert result.optimal_class_count >= 1

    def test_unstable_analysis(self, unstable_classes):
        result = analyze_precedence(unstable_classes)
        assert result.is_stable is False

    def test_wait_times_computed(self, standard_classes):
        result = analyze_precedence(standard_classes)
        for cls in result.classes:
            assert cls.avg_wait >= 0

    def test_recommendations(self, standard_classes):
        result = analyze_precedence(standard_classes)
        # Should have some recommendations
        assert isinstance(result.recommendations, list)

    def test_flash_preemption(self):
        classes = [
            PrecedenceClass(
                name="critical-signal",
                label="FLASH",
                arrival_rate=0.01,
                service_time=0.010,
                preemption_overhead=0.001,
            ),
            PrecedenceClass(
                name="normal",
                label="ROUTINE",
                arrival_rate=1.0,
                service_time=0.5,
            ),
        ]
        result = analyze_precedence(classes)
        assert any("preemption" in r.lower() for r in result.recommendations)


class TestFormatReport:
    """Tests for report formatting."""

    def test_report_contains_classes(self, standard_classes):
        result = analyze_precedence(standard_classes)
        report = format_precedence_report(result)
        assert "FLASH" in report
        assert "IMMEDIATE" in report
        assert "PRIORITY" in report
        assert "ROUTINE" in report

    def test_report_contains_stability(self, standard_classes):
        result = analyze_precedence(standard_classes)
        report = format_precedence_report(result)
        assert "stability" in report.lower()


class TestPrecedenceToDict:
    """Tests for JSON serialization."""

    def test_dict_keys(self, standard_classes):
        result = analyze_precedence(standard_classes)
        data = precedence_to_dict(result)
        assert "classes" in data
        assert "optimal_class_count" in data
        assert "system_stability" in data
        assert "is_stable" in data

    def test_classes_serialized(self, standard_classes):
        result = analyze_precedence(standard_classes)
        data = precedence_to_dict(result)
        assert len(data["classes"]) == 4
        for cls_data in data["classes"]:
            assert "name" in cls_data
            assert "label" in cls_data
            assert "arrival_rate" in cls_data
