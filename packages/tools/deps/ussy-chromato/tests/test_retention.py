"""Tests for chromato.retention — Retention time calculator."""

from datetime import datetime, timezone, timedelta

import pytest

from chromato.models import Dependency, DependencyGraph, Solvent
from chromato.retention import compute_retention_time, compute_all_retention_times


class TestComputeRetentionTime:
    def _make_graph(self) -> DependencyGraph:
        """Create a test graph with edges."""
        deps = [
            Dependency(name="util", version="1.0"),
            Dependency(name="framework", version="2.0", dependents=["app1", "app2", "app3"]),
            Dependency(name="deep", version="3.0"),
            Dependency(name="leaf", version="1.0"),
        ]
        edges = [
            ("deep", "framework"),
            ("framework", "util"),
            ("util", "leaf"),
        ]
        return DependencyGraph(dependencies=deps, edges=edges)

    def test_coupling_solvent(self):
        graph = self._make_graph()
        dep = graph.get("util")
        rt = compute_retention_time(dep, graph, Solvent.COUPLING)
        # util has depth=1 (-> leaf) and 1 dependent (framework)
        expected = 0.3 * 1 + 0.7 * 1
        assert abs(rt - expected) < 0.01

    def test_coupling_solvent_deep_dep(self):
        graph = self._make_graph()
        dep = graph.get("deep")
        rt = compute_retention_time(dep, graph, Solvent.COUPLING)
        # deep has depth=2 (-> framework -> util -> leaf) and 0 direct dependents
        # Wait: depth is 2 (deep->framework->util->leaf, so depth from deep = 2)
        # Actually: coupling_depth("deep") = 1 + coupling_depth("framework")
        #   coupling_depth("framework") = 1 + coupling_depth("util")
        #     coupling_depth("util") = 1 + coupling_depth("leaf")
        #       coupling_depth("leaf") = 0
        #   So depth = 3
        # dependent_count = 0
        expected = 0.3 * 3 + 0.7 * 0
        assert abs(rt - expected) < 0.01

    def test_risk_solvent(self):
        recent = datetime.now(timezone.utc) - timedelta(days=200)
        dep = Dependency(name="risky", version="1.0", advisory_count=5, last_updated=recent)
        graph = DependencyGraph(dependencies=[dep])
        rt = compute_retention_time(dep, graph, Solvent.RISK)
        # 0.5 * 5 + 0.005 * 200 = 2.5 + 1.0 = 3.5
        expected = 0.5 * 5 + 0.005 * 200
        assert abs(rt - expected) < 0.1

    def test_risk_solvent_no_advisories(self):
        recent = datetime.now(timezone.utc) - timedelta(days=10)
        dep = Dependency(name="safe", version="1.0", advisory_count=0, last_updated=recent)
        graph = DependencyGraph(dependencies=[dep])
        rt = compute_retention_time(dep, graph, Solvent.RISK)
        # 0.5 * 0 + 0.005 * 10 ≈ 0.05
        assert rt < 0.1

    def test_freshness_solvent(self):
        recent = datetime.now(timezone.utc) - timedelta(days=30)
        dep = Dependency(name="stale", version="1.0", last_updated=recent)
        graph = DependencyGraph(dependencies=[dep])
        rt = compute_retention_time(dep, graph, Solvent.FRESHNESS)
        assert 29 < rt < 31

    def test_freshness_solvent_unknown(self):
        dep = Dependency(name="unknown", version="1.0", last_updated=None)
        graph = DependencyGraph(dependencies=[dep])
        rt = compute_retention_time(dep, graph, Solvent.FRESHNESS)
        assert rt == 9999.0

    def test_license_solvent_mit(self):
        dep = Dependency(name="mit-pkg", version="1.0", license="MIT")
        graph = DependencyGraph(dependencies=[dep])
        rt = compute_retention_time(dep, graph, Solvent.LICENSE)
        assert rt == 0.1

    def test_license_solvent_gpl(self):
        dep = Dependency(name="gpl-pkg", version="1.0", license="GPL-3.0")
        graph = DependencyGraph(dependencies=[dep])
        rt = compute_retention_time(dep, graph, Solvent.LICENSE)
        assert rt > 0.5

    def test_license_solvent_unknown(self):
        dep = Dependency(name="unknown-pkg", version="1.0", license="UNKNOWN")
        graph = DependencyGraph(dependencies=[dep])
        rt = compute_retention_time(dep, graph, Solvent.LICENSE)
        assert rt == 0.6

    def test_retention_time_nonnegative(self):
        dep = Dependency(name="test", version="1.0")
        graph = DependencyGraph(dependencies=[dep])
        for solvent in Solvent:
            rt = compute_retention_time(dep, graph, solvent)
            assert rt >= 0.0


class TestComputeAllRetentionTimes:
    def test_all_deps_computed(self):
        deps = [
            Dependency(name="a", version="1.0"),
            Dependency(name="b", version="1.0"),
        ]
        graph = DependencyGraph(dependencies=deps, edges=[("a", "b")])
        results = compute_all_retention_times(graph, Solvent.COUPLING)
        assert "a" in results
        assert "b" in results
        assert len(results) == 2

    def test_empty_graph(self):
        graph = DependencyGraph()
        results = compute_all_retention_times(graph)
        assert len(results) == 0
