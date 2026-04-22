"""Tests for the contour map visualization module."""

import pytest

from ussy_aquifer.topology import ServiceLayer, FlowConnection, Topology, create_sample_topology
from ussy_aquifer.grid import solve_grid
from ussy_aquifer.contour import (
    head_to_char,
    flow_arrow,
    generate_head_contour,
    generate_flow_vector_map,
    generate_drawdown_map,
    generate_contour_report,
)


class TestHeadToChar:
    """Test head value to ASCII character mapping."""

    def test_min_value(self):
        char = head_to_char(0.0, 0.0, 10.0)
        assert char == " "

    def test_max_value(self):
        char = head_to_char(10.0, 0.0, 10.0)
        assert char == "@"

    def test_mid_value(self):
        char = head_to_char(5.0, 0.0, 10.0)
        assert char in " .:-=+*#%@"

    def test_equal_min_max(self):
        char = head_to_char(5.0, 5.0, 5.0)
        assert char == " "  # Default to first char when range is zero

    def test_negative_range(self):
        # Max < Min should still work
        char = head_to_char(5.0, 10.0, 0.0)
        assert isinstance(char, str)
        assert len(char) == 1


class TestFlowArrow:
    """Test flow vector to arrow character mapping."""

    def test_zero_flow(self):
        arrow = flow_arrow(0.0, 0.0)
        assert arrow == "·"

    def test_positive_x_flow(self):
        arrow = flow_arrow(10.0, 0.0)
        assert arrow == "→"

    def test_negative_x_flow(self):
        arrow = flow_arrow(-10.0, 0.0)
        assert arrow == "←"

    def test_positive_y_flow(self):
        arrow = flow_arrow(0.0, 10.0)
        assert arrow == "↓"

    def test_negative_y_flow(self):
        arrow = flow_arrow(0.0, -10.0)
        assert arrow == "↑"


class TestGenerateHeadContour:
    """Test head contour map generation."""

    def test_basic_contour(self):
        topo = create_sample_topology()
        grid = solve_grid(topo, max_iterations=100)
        contour = generate_head_contour(grid, width=40, height=10)
        assert "Hydraulic Head" in contour
        assert "Legend" in contour

    def test_contour_dimensions(self):
        topo = create_sample_topology()
        grid = solve_grid(topo, max_iterations=100)
        contour = generate_head_contour(grid, width=20, height=5)
        lines = contour.split("\n")
        # Should have header + legend + blank + map rows
        assert len(lines) >= 5

    def test_empty_grid(self):
        """Grid with no head data should handle gracefully."""
        from ussy_aquifer.grid import GridModel
        topo = Topology(name="empty")
        model = GridModel(topology=topo)
        contour = generate_head_contour(model)
        assert "No head data" in contour


class TestGenerateFlowVectorMap:
    """Test flow vector map generation."""

    def test_basic_vector_map(self):
        topo = create_sample_topology()
        grid = solve_grid(topo, max_iterations=100)
        vmap = generate_flow_vector_map(grid, width=40, height=10)
        assert "Flow Vector" in vmap

    def test_vector_map_with_empty_grid(self):
        from ussy_aquifer.grid import GridModel
        topo = Topology(name="empty")
        model = GridModel(topology=topo)
        vmap = generate_flow_vector_map(model)
        assert "No head data" in vmap


class TestGenerateDrawdownMap:
    """Test drawdown map generation."""

    def test_basic_drawdown_map(self):
        topo = create_sample_topology()
        dmap = generate_drawdown_map(topo, "transformer", time_seconds=300.0,
                                      width=40, height=10)
        assert "Drawdown Map" in dmap
        assert "transformer" in dmap

    def test_drawdown_map_with_impact(self):
        topo = create_sample_topology()
        dmap = generate_drawdown_map(topo, "transformer", time_seconds=3600.0)
        assert "Impact summary" in dmap


class TestGenerateContourReport:
    """Test full contour report generation."""

    def test_full_report(self):
        topo = create_sample_topology()
        report = generate_contour_report(topo, width=40, height=10)
        assert "AQUIFER" in report
        assert "Hydraulic Head" in report

    def test_report_has_conductivity(self):
        topo = create_sample_topology()
        report = generate_contour_report(topo, width=40, height=10)
        assert "Conductivity Profile" in report

    def test_report_has_bottleneck_section(self):
        topo = create_sample_topology()
        report = generate_contour_report(topo, width=40, height=10)
        # Should have either "Bottleneck" or "No significant bottlenecks"
        assert "bottleneck" in report.lower()
