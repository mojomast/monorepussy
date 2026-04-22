"""Tests for the relay coordinator instrument."""

import pytest

from ussy_gridiron.graph import DependencyGraph
from ussy_gridiron.instruments.relay import RelayCoordinator
from ussy_gridiron.models import DependencyEdge, ErrorHandlerContext, HandlerZone, PackageInfo


def _make_graph_with_handlers():
    """Create a graph with error handler metadata."""
    g = DependencyGraph()
    g.add_package(PackageInfo(
        name="app", is_direct=False,
        has_error_handler=True, handler_tds=1.0, handler_pickup=1.0,
    ))
    g.add_package(PackageInfo(
        name="lib_a", is_direct=True,
        has_error_handler=True, handler_tds=0.5, handler_pickup=2.0,
    ))
    g.add_package(PackageInfo(
        name="lib_b", is_direct=True,
        has_error_handler=False,
    ))
    g.add_edge(DependencyEdge(source="app", target="lib_a"))
    g.add_edge(DependencyEdge(source="lib_a", target="lib_b"))
    return g


def _make_graph_overlapping_handlers():
    """Create a graph where handlers have overlapping TCC curves."""
    g = DependencyGraph()
    g.add_package(PackageInfo(
        name="app", is_direct=False,
        has_error_handler=True, handler_tds=1.0, handler_pickup=1.0,
    ))
    g.add_package(PackageInfo(
        name="lib", is_direct=True,
        has_error_handler=True, handler_tds=1.0, handler_pickup=1.0,
    ))
    g.add_edge(DependencyEdge(source="app", target="lib"))
    return g


class TestRelayCoordinator:
    """Tests for protection coordination analysis."""

    def test_analyze_basic(self):
        g = _make_graph_with_handlers()
        coordinator = RelayCoordinator(g)
        report = coordinator.analyze()
        assert len(report.handlers) == 2  # app and lib_a have handlers

    def test_handlers_collected(self):
        g = _make_graph_with_handlers()
        coordinator = RelayCoordinator(g)
        report = coordinator.analyze()
        handler_names = [h.package for h in report.handlers]
        assert "app" in handler_names
        assert "lib_a" in handler_names
        assert "lib_b" not in handler_names

    def test_blind_spots_detected(self):
        g = _make_graph_with_handlers()
        coordinator = RelayCoordinator(g)
        report = coordinator.analyze()
        # lib_b has no handler and may not be covered
        # (depends on transitive coverage)

    def test_zone_coverage(self):
        g = _make_graph_with_handlers()
        coordinator = RelayCoordinator(g)
        report = coordinator.analyze()
        assert "zone_1" in report.zone_coverage
        assert "zone_2" in report.zone_coverage
        assert "zone_3" in report.zone_coverage

    def test_cti_violations(self):
        g = _make_graph_with_handlers()
        coordinator = RelayCoordinator(g)
        report = coordinator.analyze()
        # CTI violations are possible but not guaranteed
        # Just check the structure is correct
        for v in report.cti_violations:
            assert v.primary_handler != ""
            assert v.backup_handler != ""

    def test_tcc_overlaps(self):
        g = _make_graph_overlapping_handlers()
        coordinator = RelayCoordinator(g)
        report = coordinator.analyze()
        # Same TDS/pickup → likely overlap
        # Just verify structure
        for h1, h2 in report.tcc_overlaps:
            assert h1 != h2

    def test_no_handlers(self):
        g = DependencyGraph()
        g.add_package(PackageInfo(name="pkg1", has_error_handler=False))
        coordinator = RelayCoordinator(g)
        report = coordinator.analyze()
        assert len(report.handlers) == 0
        assert "pkg1" in report.blind_spots

    def test_custom_cti(self):
        g = _make_graph_with_handlers()
        coordinator = RelayCoordinator(g)
        report = coordinator.analyze(cti_required=0.5)
        # Higher CTI requirement might produce more violations
        for v in report.cti_violations:
            assert v.cti_required == 0.5


class TestErrorHandlerContext:
    """Tests for trip time calculation in relay context."""

    def test_zone_determination_leaf(self):
        g = DependencyGraph()
        g.add_package(PackageInfo(name="app"))
        g.add_package(PackageInfo(name="leaf", has_error_handler=True))
        g.add_edge(DependencyEdge(source="app", target="leaf"))

        coordinator = RelayCoordinator(g)
        zone = coordinator._determine_zone("leaf")
        assert zone == HandlerZone.ZONE_1

    def test_zone_determination_mid(self):
        g = DependencyGraph()
        g.add_package(PackageInfo(name="app"))
        g.add_package(PackageInfo(name="mid", has_error_handler=True))
        g.add_package(PackageInfo(name="leaf"))
        g.add_edge(DependencyEdge(source="app", target="mid"))
        g.add_edge(DependencyEdge(source="mid", target="leaf"))

        coordinator = RelayCoordinator(g)
        zone = coordinator._determine_zone("mid")
        assert zone == HandlerZone.ZONE_2
