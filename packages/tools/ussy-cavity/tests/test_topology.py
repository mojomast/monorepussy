"""Tests for cavity.topology module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from ussy_cavity.topology import Lock, PipelineTopology, Stage


# ---------------------------------------------------------------------------
# Stage / Lock dataclass tests
# ---------------------------------------------------------------------------


class TestStage:
    def test_stage_defaults(self):
        s = Stage(name="test", rate=100.0, buffer=50)
        assert s.name == "test"
        assert s.rate == 100.0
        assert s.buffer == 50
        assert s.depends_on == []
        assert s.locks == []

    def test_stage_with_deps(self):
        s = Stage(name="b", rate=50.0, buffer=20, depends_on=["a"], locks=["lock1"])
        assert s.depends_on == ["a"]
        assert s.locks == ["lock1"]


class TestLock:
    def test_lock_exclusive(self):
        l = Lock(name="mutex", lock_type="exclusive", holders=["w1", "w2"])
        assert l.lock_type == "exclusive"
        assert l.holders == ["w1", "w2"]
        assert l.capacity is None

    def test_lock_semaphore(self):
        l = Lock(name="pool", lock_type="semaphore", holders=["w1"], capacity=10)
        assert l.capacity == 10


# ---------------------------------------------------------------------------
# PipelineTopology construction
# ---------------------------------------------------------------------------


class TestPipelineTopologyFromDict:
    def test_minimal(self, minimal_dict):
        topo = PipelineTopology.from_dict(minimal_dict)
        assert "a" in topo.stages
        assert "b" in topo.stages
        assert "lock1" in topo.locks

    def test_stage_properties(self, minimal_dict):
        topo = PipelineTopology.from_dict(minimal_dict)
        assert topo.stages["a"].rate == 100
        assert topo.stages["b"].rate == 50
        assert topo.stages["b"].buffer == 20

    def test_lock_properties(self, minimal_dict):
        topo = PipelineTopology.from_dict(minimal_dict)
        lock = topo.locks["lock1"]
        assert lock.lock_type == "exclusive"
        assert lock.holders == ["b"]

    def test_cyclic_topology(self, cyclic_dict):
        topo = PipelineTopology.from_dict(cyclic_dict)
        assert len(topo.stages) == 2
        assert len(topo.locks) == 2
        assert topo.locks["lock_x"].holders == ["worker_a", "worker_b"]

    def test_empty_dict(self):
        topo = PipelineTopology.from_dict({})
        assert len(topo.stages) == 0
        assert len(topo.locks) == 0
        assert topo.adjacency_matrix.shape == (0, 0)

    def test_missing_optional_fields(self):
        data = {
            "stages": {
                "s1": {"rate": 10},  # buffer, depends_on, locks omitted
            }
        }
        topo = PipelineTopology.from_dict(data)
        assert topo.stages["s1"].buffer == 0
        assert topo.stages["s1"].depends_on == []
        assert topo.stages["s1"].locks == []


class TestPipelineTopologyFromFile:
    def test_load_yaml(self, simple_yaml_path):
        topo = PipelineTopology.from_file(simple_yaml_path)
        assert "producer" in topo.stages
        assert "consumer" in topo.stages

    def test_load_json(self, simple_json_path):
        topo = PipelineTopology.from_file(simple_json_path)
        assert "producer" in topo.stages

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            PipelineTopology.from_file("/nonexistent/path.yaml")

    def test_load_complex_yaml(self, complex_yaml_path):
        topo = PipelineTopology.from_file(complex_yaml_path)
        assert len(topo.stages) == 7
        assert len(topo.locks) == 5


# ---------------------------------------------------------------------------
# Adjacency matrix
# ---------------------------------------------------------------------------


class TestAdjacencyMatrix:
    def test_shape(self, minimal_dict):
        topo = PipelineTopology.from_dict(minimal_dict)
        n = len(topo.stages) + len(topo.locks)
        assert topo.adjacency_matrix.shape == (n, n)

    def test_dependency_edge(self, minimal_dict):
        topo = PipelineTopology.from_dict(minimal_dict)
        A = topo.adjacency_matrix
        bi = topo.get_node_index("b")
        ai = topo.get_node_index("a")
        assert A[bi][ai] == 1.0  # b depends on a

    def test_acquisition_edge(self, minimal_dict):
        topo = PipelineTopology.from_dict(minimal_dict)
        A = topo.adjacency_matrix
        bi = topo.get_node_index("b")
        li = topo.get_node_index("lock1")
        assert A[bi][li] == 1.0  # b acquires lock1

    def test_holding_edge(self, minimal_dict):
        topo = PipelineTopology.from_dict(minimal_dict)
        A = topo.adjacency_matrix
        li = topo.get_node_index("lock1")
        bi = topo.get_node_index("b")
        assert A[li][bi] == 1.0  # lock1 held by b

    def test_complex_topology_edges(self, complex_topology):
        A = complex_topology.adjacency_matrix
        # merger depends on producer_a and producer_b
        mi = complex_topology.get_node_index("merger")
        pai = complex_topology.get_node_index("producer_a")
        pbi = complex_topology.get_node_index("producer_b")
        assert A[mi][pai] == 1.0
        assert A[mi][pbi] == 1.0


# ---------------------------------------------------------------------------
# Helper methods
# ---------------------------------------------------------------------------


class TestHelperMethods:
    def test_node_names(self, simple_topology):
        names = simple_topology.node_names
        assert "producer" in names
        assert "consumer" in names

    def test_node_count(self, simple_topology):
        n = simple_topology.node_count
        assert n == len(simple_topology.stages) + len(simple_topology.locks)

    def test_stage_impedance(self, simple_topology):
        z = simple_topology.stage_impedance("producer")
        assert z == 1000 * 500  # rate * buffer

    def test_stage_pairs(self, simple_topology):
        pairs = simple_topology.stage_pairs()
        assert ("producer", "transformer") in pairs
        assert ("transformer", "consumer") in pairs

    def test_lock_shared_stages(self, simple_topology):
        stages = simple_topology.lock_shared_stages("schema_mutex")
        assert "transformer" in stages
        assert "validator" in stages

    def test_to_dict_roundtrip(self, minimal_dict):
        topo = PipelineTopology.from_dict(minimal_dict)
        d = topo.to_dict()
        topo2 = PipelineTopology.from_dict(d)
        assert set(topo2.stages.keys()) == set(topo.stages.keys())

    def test_directory_load(self, simple_yaml_path, tmp_path):
        """Test loading from a directory containing pipeline.yaml."""
        import shutil
        subdir = tmp_path / "pipeline_dir"
        subdir.mkdir()
        shutil.copy(simple_yaml_path, subdir / "pipeline.yaml")
        topo = PipelineTopology.from_file(str(subdir))
        assert "producer" in topo.stages

    def test_directory_not_found(self, tmp_path):
        """Directory with no pipeline file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            PipelineTopology.from_file(str(tmp_path))
