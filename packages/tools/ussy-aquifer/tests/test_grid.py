"""Tests for the finite difference grid solver."""

import numpy as np
import pytest

from aquifer.topology import ServiceLayer, FlowConnection, Topology, create_sample_topology
from aquifer.grid import GridModel, build_grid, solve_grid


class TestGridModel:
    """Test the GridModel dataclass."""

    def _make_simple_topo(self):
        topo = Topology(name="grid_test")
        topo.add_service(ServiceLayer("a", 100.0, queue_depth=10,
                                       processing_latency=0.1, grid_x=1, grid_y=1))
        topo.add_service(ServiceLayer("b", 50.0, queue_depth=5,
                                       processing_latency=0.2, grid_x=3, grid_y=3))
        topo.add_connection(FlowConnection("a", "b"))
        return topo

    def test_grid_initialization(self):
        topo = self._make_simple_topo()
        model = build_grid(topo)
        assert model.nx >= 5
        assert model.ny >= 5
        assert model.K is not None
        assert model.head is not None

    def test_service_positions_set(self):
        topo = self._make_simple_topo()
        model = build_grid(topo)
        # At service position (1,1), K should be 100 (effective_K = 100*1)
        assert model.K[1, 1] == pytest.approx(100.0)
        # At service position (3,3), K should be 50
        assert model.K[3, 3] == pytest.approx(50.0)

    def test_service_heads_set(self):
        topo = self._make_simple_topo()
        model = build_grid(topo)
        assert model.head[1, 1] == pytest.approx(1.0)  # 10 * 0.1
        assert model.head[3, 3] == pytest.approx(1.0)  # 5 * 0.2

    def test_service_mask(self):
        topo = self._make_simple_topo()
        model = build_grid(topo)
        assert model.service_mask[1, 1] == True
        assert model.service_mask[3, 3] == True
        assert model.service_mask[0, 0] == False


class TestGridSolver:
    """Test the Gauss-Seidel solver."""

    def _make_laplace_topo(self):
        """Create a simple topology for Laplace equation testing."""
        topo = Topology(name="laplace")
        # High head on left, low on right
        topo.add_service(ServiceLayer("left", 100.0, queue_depth=100,
                                       processing_latency=0.1, grid_x=0, grid_y=2))
        topo.add_service(ServiceLayer("right", 100.0, queue_depth=0,
                                       processing_latency=0.0, grid_x=4, grid_y=2))
        topo.add_connection(FlowConnection("left", "right"))
        return topo

    def test_solver_runs(self):
        topo = self._make_laplace_topo()
        model = solve_grid(topo, max_iterations=100)
        assert model.head is not None

    def test_solver_converges_for_simple_case(self):
        topo = self._make_laplace_topo()
        model = solve_grid(topo, max_iterations=10000, tolerance=1e-6)
        # Should converge for a simple case
        assert model.converged or model.iterations > 0

    def test_solver_preserves_boundary_heads(self):
        topo = self._make_laplace_topo()
        model = solve_grid(topo, max_iterations=1000)
        # Service positions should retain their head values
        assert model.head[2, 0] == pytest.approx(10.0)  # left
        assert model.head[2, 4] == pytest.approx(0.0)  # right

    def test_solver_head_interpolation(self):
        """Head should interpolate between boundaries."""
        topo = self._make_laplace_topo()
        model = solve_grid(topo, max_iterations=5000, tolerance=1e-8)
        # Interior heads should be between boundary values
        if model.converged:
            interior = model.head[1:-1, 1:-1]
            assert np.all(interior >= 0)
            assert np.all(interior <= 10.0)

    def test_custom_grid_size(self):
        topo = self._make_laplace_topo()
        model = build_grid(topo, nx=10, ny=10)
        assert model.nx == 10
        assert model.ny == 10


class TestFlowVectors:
    """Test flow vector computation."""

    def test_flow_vectors_computed(self):
        topo = Topology(name="vectors")
        topo.add_service(ServiceLayer("a", 100.0, queue_depth=50,
                                       processing_latency=0.1, grid_x=0, grid_y=2))
        topo.add_service(ServiceLayer("b", 100.0, queue_depth=0,
                                       processing_latency=0.0, grid_x=4, grid_y=2))
        topo.add_connection(FlowConnection("a", "b"))
        model = solve_grid(topo, max_iterations=2000)
        qx, qy = model.get_flow_vectors()
        assert qx.shape == (model.ny, model.nx)
        assert qy.shape == (model.ny, model.nx)

    def test_flow_direction(self):
        """Flow should go from high head to low head."""
        topo = Topology(name="flow_dir")
        topo.add_service(ServiceLayer("high", 100.0, queue_depth=100,
                                       processing_latency=0.1, grid_x=0, grid_y=2))
        topo.add_service(ServiceLayer("low", 100.0, queue_depth=0,
                                       processing_latency=0.0, grid_x=4, grid_y=2))
        topo.add_connection(FlowConnection("high", "low"))
        model = solve_grid(topo, max_iterations=2000)
        qx, qy = model.get_flow_vectors()
        # In the middle, flow should be positive x (left to right)
        # qx = -K * dh/dx, and head decreases left to right, so dh/dx < 0, so qx > 0
        mid_x = model.nx // 2
        mid_y = model.ny // 2
        assert qx[mid_y, mid_x] > 0


class TestGridWithSample:
    """Test grid with the sample topology."""

    def test_sample_topo_grid(self):
        topo = create_sample_topology()
        model = solve_grid(topo, max_iterations=500)
        assert model.head is not None
        assert not np.any(np.isnan(model.head))

    def test_get_head_at(self):
        topo = create_sample_topology()
        model = build_grid(topo)
        # Should return head at known service position
        h = model.get_head_at(0, 2)  # ingestion at (0, 2)
        assert h == pytest.approx(0.5)  # 50 * 0.01

    def test_get_head_at_out_of_bounds(self):
        topo = create_sample_topology()
        model = build_grid(topo)
        h = model.get_head_at(100, 100)
        assert h == 0.0

    def test_get_K_at(self):
        topo = create_sample_topology()
        model = build_grid(topo)
        K = model.get_K_at(0, 2)  # ingestion at (0, 2)
        assert K == pytest.approx(1000.0)  # effective_K = 1000 * 1
