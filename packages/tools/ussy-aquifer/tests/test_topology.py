"""Tests for the topology module."""

import json
import os
import tempfile

import pytest

from ussy_aquifer.topology import (
    ServiceLayer,
    FlowConnection,
    Topology,
    load_topology,
    parse_topology,
    save_topology,
    create_sample_topology,
)


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


class TestServiceLayer:
    """Test ServiceLayer dataclass and computed fields."""

    def test_basic_creation(self):
        svc = ServiceLayer(name="test", hydraulic_conductivity=100.0)
        assert svc.name == "test"
        assert svc.hydraulic_conductivity == 100.0
        assert svc.specific_storage == 0.01  # default
        assert svc.replicas == 1  # default

    def test_transmissivity_computed(self):
        svc = ServiceLayer(name="test", hydraulic_conductivity=100.0, replicas=3)
        assert svc.transmissivity == 300.0

    def test_hydraulic_head_computed(self):
        svc = ServiceLayer(name="test", hydraulic_conductivity=100.0,
                          queue_depth=50, processing_latency=0.1)
        assert svc.hydraulic_head == 5.0  # 50 * 0.1

    def test_effective_K_computed(self):
        svc = ServiceLayer(name="test", hydraulic_conductivity=100.0, replicas=4)
        assert svc.effective_K == 400.0

    def test_zero_queue_depth(self):
        svc = ServiceLayer(name="test", hydraulic_conductivity=100.0, queue_depth=0)
        assert svc.hydraulic_head == 0.0

    def test_recharge_discharge_flags(self):
        svc = ServiceLayer(name="in", hydraulic_conductivity=100.0, is_recharge=True)
        assert svc.is_recharge is True
        assert svc.is_discharge is False

        svc2 = ServiceLayer(name="out", hydraulic_conductivity=100.0, is_discharge=True)
        assert svc2.is_discharge is True
        assert svc2.is_recharge is False

    def test_to_dict(self):
        svc = ServiceLayer(name="test", hydraulic_conductivity=100.0)
        d = svc.to_dict()
        assert d["name"] == "test"
        assert d["hydraulic_conductivity"] == 100.0
        assert "grid_x" in d

    def test_grid_position(self):
        svc = ServiceLayer(name="test", hydraulic_conductivity=100.0, grid_x=3, grid_y=5)
        assert svc.grid_x == 3
        assert svc.grid_y == 5


class TestFlowConnection:
    """Test FlowConnection dataclass."""

    def test_basic_creation(self):
        conn = FlowConnection(source="a", target="b")
        assert conn.source == "a"
        assert conn.target == "b"
        assert conn.connection_type == "porous"
        assert conn.bandwidth == 0.0

    def test_fracture_connection(self):
        conn = FlowConnection(source="a", target="b", connection_type="fracture")
        assert conn.connection_type == "fracture"

    def test_bandwidth_limit(self):
        conn = FlowConnection(source="a", target="b", bandwidth=100.0)
        assert conn.bandwidth == 100.0

    def test_to_dict(self):
        conn = FlowConnection(source="a", target="b", bandwidth=50.0)
        d = conn.to_dict()
        assert d["source"] == "a"
        assert d["bandwidth"] == 50.0


class TestTopology:
    """Test Topology dataclass and methods."""

    def _make_simple_topo(self):
        topo = Topology(name="test")
        topo.add_service(ServiceLayer("a", 100.0, grid_x=0, grid_y=0))
        topo.add_service(ServiceLayer("b", 50.0, grid_x=1, grid_y=0))
        topo.add_connection(FlowConnection("a", "b"))
        return topo

    def test_add_service(self):
        topo = self._make_simple_topo()
        assert "a" in topo.services
        assert "b" in topo.services
        assert len(topo.services) == 2

    def test_add_connection(self):
        topo = self._make_simple_topo()
        assert len(topo.connections) == 1

    def test_grid_size(self):
        topo = self._make_simple_topo()
        assert topo.grid_width == 2
        assert topo.grid_height == 1

    def test_get_downstream(self):
        topo = self._make_simple_topo()
        assert topo.get_downstream("a") == ["b"]
        assert topo.get_downstream("b") == []

    def test_get_upstream(self):
        topo = self._make_simple_topo()
        assert topo.get_upstream("b") == ["a"]
        assert topo.get_upstream("a") == []

    def test_get_connection(self):
        topo = self._make_simple_topo()
        conn = topo.get_connection("a", "b")
        assert conn is not None
        assert conn.source == "a"
        assert topo.get_connection("b", "a") is None

    def test_validate_valid(self):
        topo = self._make_simple_topo()
        issues = topo.validate()
        assert len(issues) == 0

    def test_validate_zero_K(self):
        topo = Topology(name="bad")
        topo.add_service(ServiceLayer("bad_svc", 0.0))
        issues = topo.validate()
        assert any("K <= 0" in issue for issue in issues)

    def test_validate_negative_K(self):
        topo = Topology(name="bad")
        topo.add_service(ServiceLayer("bad_svc", -10.0))
        issues = topo.validate()
        assert any("K <= 0" in issue for issue in issues)

    def test_validate_missing_source(self):
        topo = Topology(name="bad")
        topo.add_service(ServiceLayer("a", 100.0))
        topo.add_connection(FlowConnection("a", "nonexistent"))
        issues = topo.validate()
        assert any("nonexistent" in issue for issue in issues)

    def test_validate_missing_target(self):
        topo = Topology(name="bad")
        topo.add_service(ServiceLayer("b", 100.0))
        topo.add_connection(FlowConnection("nonexistent", "b"))
        issues = topo.validate()
        assert any("nonexistent" in issue for issue in issues)

    def test_to_dict(self):
        topo = self._make_simple_topo()
        d = topo.to_dict()
        assert d["name"] == "test"
        assert "a" in d["services"]
        assert len(d["connections"]) == 1


class TestLoadSaveTopology:
    """Test loading and saving topology files."""

    def test_load_from_fixture(self):
        path = os.path.join(FIXTURES_DIR, "test_topology.json")
        topo = load_topology(path)
        assert topo.name == "test_pipeline"
        assert len(topo.services) == 7
        assert len(topo.connections) == 8

    def test_load_minimal(self):
        path = os.path.join(FIXTURES_DIR, "minimal_topology.json")
        topo = load_topology(path)
        assert len(topo.services) == 2
        assert len(topo.connections) == 1

    def test_save_and_load_roundtrip(self):
        topo = create_sample_topology()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_topology(topo, path)
            loaded = load_topology(path)
            assert loaded.name == topo.name
            assert set(loaded.services.keys()) == set(topo.services.keys())
            assert len(loaded.connections) == len(topo.connections)
        finally:
            os.unlink(path)

    def test_parse_topology(self):
        data = {
            "name": "parsed",
            "services": [{"name": "svc", "hydraulic_conductivity": 42.0}],
            "connections": [{"source": "svc", "target": "svc"}],
        }
        topo = parse_topology(data)
        assert topo.name == "parsed"
        assert "svc" in topo.services

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            load_topology("/nonexistent/path.json")

    def test_load_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{")
            path = f.name
        try:
            with pytest.raises(json.JSONDecodeError):
                load_topology(path)
        finally:
            os.unlink(path)


class TestSampleTopology:
    """Test the sample topology generator."""

    def test_create_sample(self):
        topo = create_sample_topology()
        assert topo.name == "sample_pipeline"
        assert len(topo.services) >= 5
        assert len(topo.connections) >= 5

    def test_sample_has_recharge(self):
        topo = create_sample_topology()
        recharges = [s for s in topo.services.values() if s.is_recharge]
        assert len(recharges) >= 1

    def test_sample_has_discharge(self):
        topo = create_sample_topology()
        discharges = [s for s in topo.services.values() if s.is_discharge]
        assert len(discharges) >= 1

    def test_sample_all_connections_valid(self):
        topo = create_sample_topology()
        issues = topo.validate()
        assert len(issues) == 0
