"""Tests for the frequency monitor instrument."""

import pytest

from ussy_gridiron.graph import DependencyGraph
from ussy_gridiron.instruments.frequency import FrequencyMonitor, _bump_major
from ussy_gridiron.models import DependencyEdge, PackageInfo, VersionShock


def _make_graph_with_rigid():
    """Create a graph with a mix of rigid and flexible packages."""
    g = DependencyGraph()
    g.add_package(PackageInfo(name="app", is_direct=False, version_rigidity=0.3))
    g.add_package(PackageInfo(name="flexible", is_direct=True, version_rigidity=0.2))
    g.add_package(PackageInfo(name="rigid", is_direct=True, version_rigidity=0.9))
    g.add_package(PackageInfo(name="medium", is_direct=True, version_rigidity=0.5))
    g.add_edge(DependencyEdge(source="app", target="flexible"))
    g.add_edge(DependencyEdge(source="app", target="rigid"))
    g.add_edge(DependencyEdge(source="app", target="medium"))
    return g


class TestFrequencyMonitor:
    """Tests for frequency regulation analysis."""

    def test_analyze_shock_basic(self):
        g = _make_graph_with_rigid()
        monitor = FrequencyMonitor(g)
        shock = VersionShock(package="rigid", severity=0.5, is_breaking=True)
        result = monitor.analyze_shock(shock)

        assert result.frequency_deviation > 0
        assert result.shock.package == "rigid"

    def test_breaking_shock_worse_than_nonbreaking(self):
        g = _make_graph_with_rigid()
        monitor = FrequencyMonitor(g)

        breaking = VersionShock(package="flexible", severity=0.8, is_breaking=True)
        non_breaking = VersionShock(package="flexible", severity=0.3, is_breaking=False)

        result_break = monitor.analyze_shock(breaking)
        result_non = monitor.analyze_shock(non_breaking)

        # Breaking shock should have larger deviation or more tertiary need
        assert result_break.frequency_deviation >= result_non.frequency_deviation or \
               result_break.tertiary_needed >= result_non.tertiary_needed

    def test_rigid_transmitters_detected(self):
        g = _make_graph_with_rigid()
        monitor = FrequencyMonitor(g)
        report = monitor.analyze()
        # "rigid" package has rigidity 0.9, should be flagged
        # Check that some rigid transmitters are identified
        all_rigid = []
        for result in report.results:
            all_rigid.extend(result.rigid_transmitters)
        assert "rigid" in all_rigid

    def test_droop_response_computed(self):
        g = _make_graph_with_rigid()
        monitor = FrequencyMonitor(g)
        shock = VersionShock(package="flexible", severity=0.5)
        result = monitor.analyze_shock(shock)
        # Each package should have a droop response value
        assert len(result.droop_response) == 4
        # Flexible package should have higher 1/Rv than rigid
        assert result.droop_response["flexible"] > result.droop_response["rigid"]

    def test_primary_recovery_fraction(self):
        g = _make_graph_with_rigid()
        monitor = FrequencyMonitor(g)
        shock = VersionShock(package="flexible", severity=0.3, is_breaking=False)
        result = monitor.analyze_shock(shock)
        assert 0 <= result.primary_recovery <= 1.0

    def test_agc_time_positive(self):
        g = _make_graph_with_rigid()
        monitor = FrequencyMonitor(g)
        shock = VersionShock(package="rigid", severity=1.0, is_breaking=True)
        result = monitor.analyze_shock(shock)
        assert result.agc_equivalency_time > 0

    def test_analyze_auto_generates_shocks(self):
        g = _make_graph_with_rigid()
        monitor = FrequencyMonitor(g)
        report = monitor.analyze()
        # Should generate shocks for direct dependencies
        assert len(report.results) > 0

    def test_average_deviation_computed(self):
        g = _make_graph_with_rigid()
        monitor = FrequencyMonitor(g)
        report = monitor.analyze()
        assert report.average_deviation >= 0

    def test_worst_deviation_computed(self):
        g = _make_graph_with_rigid()
        monitor = FrequencyMonitor(g)
        report = monitor.analyze()
        assert report.worst_deviation >= report.average_deviation


class TestBumpMajor:
    """Tests for the _bump_major utility."""

    def test_basic(self):
        assert _bump_major("1.2.3") == "2.0.0"

    def test_zero(self):
        assert _bump_major("0.0.0") == "1.0.0"

    def test_large_version(self):
        assert _bump_major("99.0.0") == "100.0.0"
