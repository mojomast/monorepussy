"""Tests for the Darcy engine module."""

import pytest

from ussy_aquifer.topology import ServiceLayer, FlowConnection, Topology
from ussy_aquifer.darcy import (
    compute_darcy_flux,
    compute_hydraulic_gradient,
    analyze_flow,
    find_bottlenecks,
    compute_conductivity_map,
)


class TestDarcyFlux:
    """Test Darcy's Law computation: q = -K * (dh/dl)."""

    def test_basic_flux(self):
        # K=100, head_source=10, head_target=0, distance=1
        # q = 100 * (10-0)/1 = 1000
        q = compute_darcy_flux(100.0, 10.0, 0.0, 1.0)
        assert q == pytest.approx(1000.0)

    def test_zero_gradient(self):
        # No head difference = no flow
        q = compute_darcy_flux(100.0, 5.0, 5.0, 1.0)
        assert q == pytest.approx(0.0)

    def test_negative_gradient_no_reverse_flow(self):
        # If target has higher head than source, flow is 0 (clamped)
        q = compute_darcy_flux(100.0, 0.0, 10.0, 1.0)
        assert q == pytest.approx(0.0)

    def test_distance_effect(self):
        # Double distance = half the gradient = half the flow
        q1 = compute_darcy_flux(100.0, 10.0, 0.0, 1.0)
        q2 = compute_darcy_flux(100.0, 10.0, 0.0, 2.0)
        assert q2 == pytest.approx(q1 / 2.0)

    def test_K_scaling(self):
        # Double K = double flow
        q1 = compute_darcy_flux(100.0, 10.0, 0.0, 1.0)
        q2 = compute_darcy_flux(200.0, 10.0, 0.0, 1.0)
        assert q2 == pytest.approx(2.0 * q1)

    def test_zero_distance(self):
        # Zero distance should return 0 (avoid division by zero)
        q = compute_darcy_flux(100.0, 10.0, 0.0, 0.0)
        assert q == 0.0

    def test_negative_distance(self):
        # Negative distance should return 0
        q = compute_darcy_flux(100.0, 10.0, 0.0, -1.0)
        assert q == 0.0


class TestHydraulicGradient:
    """Test hydraulic gradient computation."""

    def test_positive_gradient(self):
        grad = compute_hydraulic_gradient(10.0, 0.0, 1.0)
        assert grad == pytest.approx(10.0)

    def test_zero_gradient(self):
        grad = compute_hydraulic_gradient(5.0, 5.0, 1.0)
        assert grad == pytest.approx(0.0)

    def test_negative_gradient(self):
        grad = compute_hydraulic_gradient(0.0, 10.0, 1.0)
        assert grad == pytest.approx(-10.0)

    def test_distance_scaling(self):
        grad = compute_hydraulic_gradient(10.0, 0.0, 2.0)
        assert grad == pytest.approx(5.0)


class TestFlowAnalysis:
    """Test complete flow analysis."""

    def _make_bottleneck_topo(self):
        """Create a topology with a clear bottleneck."""
        topo = Topology(name="bottleneck_test")
        # High-K source, low-K middle, high-K sink
        topo.add_service(ServiceLayer("source", 1000.0, queue_depth=100,
                                       processing_latency=0.1, grid_x=0, grid_y=0))
        topo.add_service(ServiceLayer("bottleneck", 50.0, queue_depth=500,
                                       processing_latency=0.5, grid_x=1, grid_y=0))
        topo.add_service(ServiceLayer("sink", 800.0, queue_depth=10,
                                       processing_latency=0.01, grid_x=2, grid_y=0))
        topo.add_connection(FlowConnection("source", "bottleneck"))
        topo.add_connection(FlowConnection("bottleneck", "sink"))
        return topo

    def _make_healthy_topo(self):
        """Create a healthy topology with no bottlenecks."""
        topo = Topology(name="healthy_test")
        topo.add_service(ServiceLayer("source", 100.0, queue_depth=5,
                                       processing_latency=0.01, grid_x=0, grid_y=0))
        topo.add_service(ServiceLayer("sink", 100.0, queue_depth=0,
                                       processing_latency=0.01, grid_x=1, grid_y=0))
        topo.add_connection(FlowConnection("source", "sink"))
        return topo

    def test_analysis_returns_flows(self):
        topo = self._make_healthy_topo()
        analysis = analyze_flow(topo)
        assert len(analysis.flows) == 1

    def test_analysis_finds_max_pressure(self):
        topo = self._make_bottleneck_topo()
        analysis = analyze_flow(topo)
        assert analysis.max_pressure_service == "bottleneck"
        assert analysis.max_pressure_head == 250.0  # 500 * 0.5

    def test_analysis_total_flow(self):
        topo = self._make_healthy_topo()
        analysis = analyze_flow(topo)
        assert analysis.total_system_flow > 0

    def test_bottleneck_detection(self):
        topo = self._make_bottleneck_topo()
        bottlenecks = find_bottlenecks(topo, threshold=0.8)
        assert len(bottlenecks) >= 1

    def test_healthy_no_bottleneck(self):
        topo = self._make_healthy_topo()
        analysis = analyze_flow(topo)
        # With equal K and small head, should have minimal bottlenecks
        assert len(analysis.bottlenecks) <= 1

    def test_pressure_gradients_computed(self):
        topo = self._make_healthy_topo()
        analysis = analyze_flow(topo)
        assert "source" in analysis.pressure_gradients
        assert "sink" in analysis.pressure_gradients

    def test_analysis_summary(self):
        topo = self._make_healthy_topo()
        analysis = analyze_flow(topo)
        summary = analysis.summary()
        assert "Flow Analysis" in summary
        assert "Total system flow" in summary


class TestConductivityMap:
    """Test conductivity map computation."""

    def test_conductivity_map(self):
        topo = Topology(name="kmap")
        topo.add_service(ServiceLayer("a", 100.0))
        topo.add_service(ServiceLayer("b", 200.0, replicas=2))
        k_map = compute_conductivity_map(topo)
        assert k_map["a"] == pytest.approx(100.0)
        assert k_map["b"] == pytest.approx(400.0)  # 200 * 2

    def test_conductivity_map_empty(self):
        topo = Topology(name="empty")
        k_map = compute_conductivity_map(topo)
        assert len(k_map) == 0
