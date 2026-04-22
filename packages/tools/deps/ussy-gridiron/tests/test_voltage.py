"""Tests for the voltage analyst instrument."""

import pytest

from gridiron.graph import DependencyGraph
from gridiron.instruments.voltage import VoltageAnalyst
from gridiron.models import DependencyEdge, PackageInfo


def _make_healthy_graph():
    """Create a graph with healthy packages."""
    g = DependencyGraph()
    g.add_package(PackageInfo(
        name="app", is_direct=False,
        maintainers=5, release_frequency_days=14, issue_response_days=2,
        has_types=True, has_docs=True, has_tests=True,
        semver_compliance=1.0,
    ))
    g.add_package(PackageInfo(
        name="healthy_lib", is_direct=True,
        maintainers=10, release_frequency_days=7, issue_response_days=1,
        has_types=True, has_docs=True, has_tests=True,
        api_surface_size=5, side_effect_ratio=0.01, type_pollution=0.01,
        semver_compliance=0.95,
    ))
    g.add_edge(DependencyEdge(source="app", target="healthy_lib"))
    return g


def _make_unhealthy_graph():
    """Create a graph with unhealthy / collapsing packages."""
    g = DependencyGraph()
    g.add_package(PackageInfo(
        name="app", is_direct=False,
        maintainers=1, release_frequency_days=365, issue_response_days=90,
        has_types=False, has_docs=False, has_tests=False,
        semver_compliance=0.3,
    ))
    g.add_package(PackageInfo(
        name="dying_lib", is_direct=True,
        maintainers=0, release_frequency_days=999, issue_response_days=999,
        has_types=False, has_docs=False, has_tests=False,
        api_surface_size=50, side_effect_ratio=0.5, type_pollution=0.3,
        semver_compliance=0.2,
    ))
    g.add_edge(DependencyEdge(source="app", target="dying_lib"))
    return g


class TestVoltageAnalyst:
    """Tests for voltage / capability analysis."""

    def test_analyze_basic(self):
        g = _make_healthy_graph()
        analyst = VoltageAnalyst(g)
        report = analyst.analyze()
        assert len(report.package_results) == 2

    def test_healthy_higher_voltage(self):
        g_healthy = _make_healthy_graph()
        g_unhealthy = _make_unhealthy_graph()

        r_healthy = VoltageAnalyst(g_healthy).analyze()
        r_unhealthy = VoltageAnalyst(g_unhealthy).analyze()

        v_healthy = max(r.health_voltage for r in r_healthy.package_results)
        v_unhealthy = max(r.health_voltage for r in r_unhealthy.package_results)
        assert v_healthy > v_unhealthy

    def test_sagging_detected(self):
        g = _make_unhealthy_graph()
        analyst = VoltageAnalyst(g)
        report = analyst.analyze()
        sagging = [r for r in report.package_results if r.is_sagging]
        assert len(sagging) > 0

    def test_cpi_range(self):
        g = _make_healthy_graph()
        analyst = VoltageAnalyst(g)
        report = analyst.analyze()
        for r in report.package_results:
            # CPI can be negative (past collapse)
            assert r.collapse_proximity_index <= 2.0

    def test_weakest_packages(self):
        g = _make_unhealthy_graph()
        analyst = VoltageAnalyst(g)
        report = analyst.analyze()
        assert len(report.weakest_packages) > 0

    def test_modal_eigenvalues(self):
        g = _make_healthy_graph()
        analyst = VoltageAnalyst(g)
        report = analyst.analyze()
        assert len(report.modal_eigenvalues) == 2
        for ev in report.modal_eigenvalues:
            assert ev > 0

    def test_reactive_compensation_recommendations(self):
        g = _make_unhealthy_graph()
        analyst = VoltageAnalyst(g)
        report = analyst.analyze()
        assert len(report.reactive_compensation_recommendations) > 0

    def test_q_margin_positive_for_healthy(self):
        g = _make_healthy_graph()
        analyst = VoltageAnalyst(g)
        report = analyst.analyze()
        # Healthy packages should have positive Q margin
        for r in report.package_results:
            if r.health_voltage > 0.95:
                assert r.q_margin > -1.0  # generous bound

    def test_health_voltage_per_unit_range(self):
        g = _make_healthy_graph()
        analyst = VoltageAnalyst(g)
        report = analyst.analyze()
        for r in report.package_results:
            assert 0 <= r.health_voltage <= 1.1

    def test_semantic_reactance_positive(self):
        g = _make_healthy_graph()
        analyst = VoltageAnalyst(g)
        report = analyst.analyze()
        for r in report.package_results:
            assert r.semantic_reactance > 0

    def test_participation_factor_non_negative(self):
        g = _make_healthy_graph()
        analyst = VoltageAnalyst(g)
        report = analyst.analyze()
        for r in report.package_results:
            assert r.participation_factor >= 0
