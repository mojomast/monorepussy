"""Tests for the what-if engine module."""

import pytest

from ussy_aquifer.topology import ServiceLayer, FlowConnection, Topology, create_sample_topology
from ussy_aquifer.whatif import (
    drill_well,
    add_fracture,
    remove_confining_layer,
)


class TestDrillWell:
    """Test 'drill a well' what-if scenario."""

    def _make_topo(self):
        topo = Topology(name="drill_test")
        topo.add_service(ServiceLayer("src", 1000.0, queue_depth=100,
                                       processing_latency=0.1, grid_x=0, grid_y=0))
        topo.add_service(ServiceLayer("mid", 50.0, queue_depth=500,
                                       processing_latency=0.5, grid_x=1, grid_y=0))
        topo.add_service(ServiceLayer("snk", 800.0, queue_depth=10,
                                       processing_latency=0.01, grid_x=2, grid_y=0))
        topo.add_connection(FlowConnection("src", "mid"))
        topo.add_connection(FlowConnection("mid", "snk"))
        return topo

    def test_drill_adds_replicas(self):
        topo = self._make_topo()
        result = drill_well(topo, "mid", additional_replicas=2)
        assert result.scenario == "drill_well"
        assert result.modified_topology is not None
        # Check the modified topology has increased replicas
        mod_svc = result.modified_topology.services["mid"]
        assert mod_svc.replicas == 3  # 1 + 2

    def test_drill_increases_flow(self):
        topo = self._make_topo()
        result = drill_well(topo, "mid", additional_replicas=3)
        assert result.new_flow >= result.original_flow

    def test_drill_nonexistent_service(self):
        topo = self._make_topo()
        result = drill_well(topo, "nonexistent")
        assert result.new_flow == result.original_flow  # No change

    def test_drill_adds_K(self):
        topo = self._make_topo()
        result = drill_well(topo, "mid", additional_K=200.0)
        assert result.modified_topology is not None
        mod_svc = result.modified_topology.services["mid"]
        assert mod_svc.hydraulic_conductivity == pytest.approx(250.0)

    def test_drill_summary(self):
        topo = self._make_topo()
        result = drill_well(topo, "mid", additional_replicas=1)
        summary = result.summary()
        assert "drill_well" in summary

    def test_drill_does_not_modify_original(self):
        topo = self._make_topo()
        original_K = topo.services["mid"].hydraulic_conductivity
        drill_well(topo, "mid", additional_K=100.0)
        assert topo.services["mid"].hydraulic_conductivity == original_K

    def test_drill_drawdown_details(self):
        topo = self._make_topo()
        result = drill_well(topo, "mid", additional_replicas=2)
        assert "old_max_drawdown" in result.details
        assert "new_max_drawdown" in result.details


class TestAddFracture:
    """Test 'add fracture' what-if scenario."""

    def _make_topo(self):
        topo = Topology(name="fracture_test")
        topo.add_service(ServiceLayer("a", 100.0, queue_depth=50,
                                       processing_latency=0.1, grid_x=0, grid_y=0))
        topo.add_service(ServiceLayer("b", 100.0, queue_depth=10,
                                       processing_latency=0.05, grid_x=1, grid_y=0))
        topo.add_service(ServiceLayer("c", 100.0, queue_depth=5,
                                       processing_latency=0.01, grid_x=2, grid_y=0))
        topo.add_connection(FlowConnection("a", "b"))
        topo.add_connection(FlowConnection("b", "c"))
        return topo

    def test_add_fracture(self):
        topo = self._make_topo()
        result = add_fracture(topo, "a", "c")
        assert result.scenario == "add_fracture"
        assert result.modified_topology is not None
        assert len(result.modified_topology.connections) == 3

    def test_fracture_is_bypass(self):
        topo = self._make_topo()
        result = add_fracture(topo, "a", "c")
        # New connection should be fracture type
        new_conn = result.modified_topology.get_connection("a", "c")
        assert new_conn is not None
        assert new_conn.connection_type == "fracture"

    def test_fracture_does_not_modify_original(self):
        topo = self._make_topo()
        original_conns = len(topo.connections)
        add_fracture(topo, "a", "c")
        assert len(topo.connections) == original_conns

    def test_fracture_summary(self):
        topo = self._make_topo()
        result = add_fracture(topo, "a", "c")
        summary = result.summary()
        assert "fracture" in summary


class TestRemoveConfiningLayer:
    """Test 'remove confining layer' what-if scenario."""

    def _make_topo(self):
        topo = Topology(name="confine_test")
        topo.add_service(ServiceLayer("limited", 50.0, queue_depth=200,
                                       processing_latency=0.3, grid_x=0, grid_y=0))
        topo.add_service(ServiceLayer("sink", 500.0, queue_depth=10,
                                       processing_latency=0.01, grid_x=1, grid_y=0))
        topo.add_connection(FlowConnection("limited", "sink"))
        return topo

    def test_remove_confining_doubles_K(self):
        topo = self._make_topo()
        result = remove_confining_layer(topo, "limited")
        assert result.modified_topology is not None
        mod_svc = result.modified_topology.services["limited"]
        assert mod_svc.hydraulic_conductivity == pytest.approx(100.0)  # 50 * 2

    def test_remove_confining_increases_flow(self):
        topo = self._make_topo()
        result = remove_confining_layer(topo, "limited")
        assert result.new_flow >= result.original_flow

    def test_remove_confining_nonexistent(self):
        topo = self._make_topo()
        result = remove_confining_layer(topo, "nonexistent")
        assert result.new_flow == result.original_flow

    def test_remove_confining_summary(self):
        topo = self._make_topo()
        result = remove_confining_layer(topo, "limited")
        summary = result.summary()
        assert "remove_confining_layer" in summary or "rate limit" in summary.lower()
