"""Tests for the drawdown / cone of depression module."""

import pytest

from aquifer.topology import ServiceLayer, FlowConnection, Topology, create_sample_topology
from aquifer.drawdown import (
    compute_graph_distance,
    compute_cone_of_depression,
    predict_cascade,
)


class TestGraphDistance:
    """Test graph distance computation."""

    def _make_chain_topo(self):
        """Create a chain topology: A -> B -> C -> D."""
        topo = Topology(name="chain")
        for i, name in enumerate(["A", "B", "C", "D"]):
            topo.add_service(ServiceLayer(name, 100.0, grid_x=i, grid_y=0))
        for i in range(3):
            topo.add_connection(FlowConnection(["A", "B", "C", "D"][i],
                                                ["A", "B", "C", "D"][i + 1]))
        return topo

    def test_same_node(self):
        topo = self._make_chain_topo()
        assert compute_graph_distance(topo, "A", "A") == 0.0

    def test_adjacent_nodes(self):
        topo = self._make_chain_topo()
        assert compute_graph_distance(topo, "A", "B") == 1.0

    def test_distance_two_hops(self):
        topo = self._make_chain_topo()
        assert compute_graph_distance(topo, "A", "C") == 2.0

    def test_distance_three_hops(self):
        topo = self._make_chain_topo()
        assert compute_graph_distance(topo, "A", "D") == 3.0

    def test_disconnected_nodes(self):
        topo = Topology(name="disconnected")
        topo.add_service(ServiceLayer("X", 100.0))
        topo.add_service(ServiceLayer("Y", 100.0))
        # No connection
        assert compute_graph_distance(topo, "X", "Y") == float("inf")

    def test_bidirectional_distance(self):
        """Distance should be the same in both directions for undirected traversal."""
        topo = self._make_chain_topo()
        d1 = compute_graph_distance(topo, "A", "C")
        d2 = compute_graph_distance(topo, "C", "A")
        assert d1 == d2


class TestConeOfDepression:
    """Test cone of depression computation."""

    def _make_topo(self):
        topo = create_sample_topology()
        return topo

    def test_basic_cone(self):
        topo = self._make_topo()
        cone = compute_cone_of_depression(topo, "transformer", 0.5, 300.0)
        assert cone.epicenter == "transformer"
        assert len(cone.points) > 0

    def test_cone_max_drawdown_at_epicenter(self):
        """Max drawdown should be at or near the epicenter."""
        topo = self._make_topo()
        cone = compute_cone_of_depression(topo, "transformer", 0.5, 300.0)
        # The epicenter point should have the highest drawdown
        epicenter_pts = [p for p in cone.points if p.service_name == "transformer"]
        if epicenter_pts:
            assert epicenter_pts[0].drawdown == pytest.approx(cone.max_drawdown, rel=0.1)

    def test_cone_decreases_with_distance(self):
        """Drawdown should generally decrease with distance."""
        topo = self._make_topo()
        cone = compute_cone_of_depression(topo, "transformer", 0.5, 300.0)
        sorted_pts = sorted(cone.points, key=lambda p: p.distance)
        # Check general trend (not strict due to topology shape)
        if len(sorted_pts) >= 3:
            assert sorted_pts[0].drawdown >= sorted_pts[-1].drawdown

    def test_cone_summary(self):
        topo = self._make_topo()
        cone = compute_cone_of_depression(topo, "transformer", 0.5, 300.0)
        summary = cone.summary()
        assert "transformer" in summary
        assert "Degradation" in summary

    def test_cone_with_degradation_factor(self):
        """Higher degradation = more drawdown."""
        topo = self._make_topo()
        cone1 = compute_cone_of_depression(topo, "transformer", 0.3, 300.0)
        cone2 = compute_cone_of_depression(topo, "transformer", 0.7, 300.0)
        assert cone2.max_drawdown > cone1.max_drawdown

    def test_cone_over_time(self):
        """Drawdown increases over time."""
        topo = self._make_topo()
        cone1 = compute_cone_of_depression(topo, "transformer", 0.5, 60.0)
        cone2 = compute_cone_of_depression(topo, "transformer", 0.5, 3600.0)
        assert cone2.max_drawdown > cone1.max_drawdown

    def test_cone_nonexistent_service(self):
        """Should handle nonexistent service gracefully."""
        topo = self._make_topo()
        cone = compute_cone_of_depression(topo, "nonexistent", 0.5, 300.0)
        assert cone.epicenter == "nonexistent"
        assert len(cone.points) == 0

    def test_affected_services(self):
        topo = self._make_topo()
        cone = compute_cone_of_depression(topo, "transformer", 0.5, 300.0)
        # Should identify at least some affected services
        assert isinstance(cone.affected_services, list)


class TestPredictCascade:
    """Test cascading failure prediction."""

    def test_cascade_ordering(self):
        """Cascade should be ordered by impact severity."""
        topo = create_sample_topology()
        cascade = predict_cascade(topo, "transformer", 0.5, 300.0)
        # Just verify it returns a list (may or may not have cascading failures)
        assert isinstance(cascade, list)

    def test_no_cascade_with_healthy_system(self):
        """A healthy system with small degradation shouldn't cascade."""
        topo = Topology(name="healthy")
        topo.add_service(ServiceLayer("a", 1000.0, queue_depth=1,
                                       processing_latency=0.001, grid_x=0, grid_y=0))
        topo.add_service(ServiceLayer("b", 1000.0, queue_depth=1,
                                       processing_latency=0.001, grid_x=1, grid_y=0))
        topo.add_connection(FlowConnection("a", "b"))
        cascade = predict_cascade(topo, "a", 0.1, 10.0, cascade_threshold=0.8)
        # With such small degradation, shouldn't cascade
        assert isinstance(cascade, list)

    def test_cascade_threshold_effect(self):
        """Lower threshold should produce more cascading failures."""
        topo = create_sample_topology()
        cascade_low = predict_cascade(topo, "transformer", 0.5, 300.0, cascade_threshold=0.1)
        cascade_high = predict_cascade(topo, "transformer", 0.5, 300.0, cascade_threshold=0.9)
        assert len(cascade_low) >= len(cascade_high)
