"""Tests for the flow optimizer instrument."""

import pytest

from gridiron.graph import DependencyGraph
from gridiron.instruments.flow_optimizer import FlowOptimizer
from gridiron.models import DependencyEdge, PackageInfo


def _make_simple_opf_graph():
    """Create a simple graph for OPF testing."""
    g = DependencyGraph()
    g.add_package(PackageInfo(name="app", is_direct=False, risk_weight=1.0))
    g.add_package(PackageInfo(name="low_risk", is_direct=True, risk_weight=0.5))
    g.add_package(PackageInfo(name="high_risk", is_direct=True, risk_weight=3.0))
    g.add_edge(DependencyEdge(source="app", target="low_risk"))
    g.add_edge(DependencyEdge(source="app", target="high_risk"))
    return g


def _make_congested_graph():
    """Create a graph with congested packages."""
    g = DependencyGraph()
    g.add_package(PackageInfo(name="app", is_direct=False, risk_weight=1.0))
    g.add_package(PackageInfo(name="bottleneck", is_direct=True, risk_weight=5.0,
                               backup_packages=["alternative"]))
    g.add_package(PackageInfo(name="alternative", is_direct=False, risk_weight=0.3))
    g.add_edge(DependencyEdge(source="app", target="bottleneck", coupling_strength=0.9))
    return g


class TestFlowOptimizer:
    """Tests for optimal dependency dispatch."""

    def test_optimize_basic(self):
        g = _make_simple_opf_graph()
        optimizer = FlowOptimizer(g)
        report = optimizer.optimize()
        assert report.total_risk >= 0
        assert len(report.dispatch) == 3

    def test_low_risk_gets_higher_weight(self):
        g = _make_simple_opf_graph()
        optimizer = FlowOptimizer(g)
        report = optimizer.optimize()
        # Low risk packages should get higher weight in greedy optimization
        dispatch_map = {d.package: d.optimal_weight for d in report.dispatch}
        assert dispatch_map["low_risk"] >= dispatch_map["high_risk"]

    def test_congested_packages_detected(self):
        g = _make_congested_graph()
        optimizer = FlowOptimizer(g)
        report = optimizer.optimize()
        assert "bottleneck" in report.congestion_bottlenecks

    def test_redispatch_recommendations(self):
        g = _make_congested_graph()
        optimizer = FlowOptimizer(g)
        report = optimizer.optimize()
        assert len(report.redispatch_recommendations) > 0

    def test_overcoupled_pairs(self):
        g = DependencyGraph()
        g.add_package(PackageInfo(name="app"))
        g.add_package(PackageInfo(name="lib"))
        g.add_edge(DependencyEdge(source="app", target="lib", coupling_strength=0.9))
        optimizer = FlowOptimizer(g, )
        report = optimizer.optimize(coupling_max=0.8)
        assert ("app", "lib") in report.overcoupled_pairs

    def test_total_risk_calculation(self):
        g = _make_simple_opf_graph()
        optimizer = FlowOptimizer(g)
        report = optimizer.optimize()
        # Total risk = sum of risk_weight * optimal_weight
        expected = sum(d.risk_contribution for d in report.dispatch)
        assert abs(report.total_risk - expected) < 0.01

    def test_line_flows(self):
        g = _make_simple_opf_graph()
        optimizer = FlowOptimizer(g)
        flows = optimizer.compute_line_flows()
        assert len(flows) > 0

    def test_empty_graph(self):
        g = DependencyGraph()
        optimizer = FlowOptimizer(g)
        report = optimizer.optimize()
        assert report.total_risk == 0
        assert len(report.dispatch) == 0
