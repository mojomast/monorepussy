"""Tests for the dependency graph module."""

import pytest

from gridiron.graph import DependencyGraph
from gridiron.models import DependencyEdge, PackageInfo


def _make_simple_graph():
    """Create a simple graph: app → lib_a → lib_b."""
    g = DependencyGraph()
    g.add_package(PackageInfo(name="app", is_direct=False))
    g.add_package(PackageInfo(name="lib_a", is_direct=True))
    g.add_package(PackageInfo(name="lib_b", is_direct=True))
    g.add_edge(DependencyEdge(source="app", target="lib_a"))
    g.add_edge(DependencyEdge(source="lib_a", target="lib_b"))
    return g


def _make_complex_graph():
    """Create a more complex graph with multiple paths."""
    g = DependencyGraph()
    g.add_package(PackageInfo(name="app", is_direct=False))
    g.add_package(PackageInfo(name="lib_a", is_direct=True))
    g.add_package(PackageInfo(name="lib_b", is_direct=True))
    g.add_package(PackageInfo(name="lib_c", is_direct=True, backup_packages=["lib_a"]))
    g.add_package(PackageInfo(name="lib_d", is_direct=False))
    g.add_edge(DependencyEdge(source="app", target="lib_a"))
    g.add_edge(DependencyEdge(source="app", target="lib_b"))
    g.add_edge(DependencyEdge(source="app", target="lib_c"))
    g.add_edge(DependencyEdge(source="lib_a", target="lib_d"))
    g.add_edge(DependencyEdge(source="lib_b", target="lib_d"))
    return g


class TestDependencyGraphBasic:
    """Tests for basic graph operations."""

    def test_add_package(self):
        g = DependencyGraph()
        g.add_package(PackageInfo(name="test"))
        assert "test" in g.packages
        assert g.package_count() == 1

    def test_add_edge(self):
        g = DependencyGraph()
        g.add_edge(DependencyEdge(source="a", target="b"))
        assert g.package_count() == 2
        assert g.edge_count() == 1

    def test_edge_creates_packages(self):
        g = DependencyGraph()
        g.add_edge(DependencyEdge(source="x", target="y"))
        assert "x" in g.packages
        assert "y" in g.packages

    def test_package_count(self):
        g = _make_simple_graph()
        assert g.package_count() == 3

    def test_edge_count(self):
        g = _make_simple_graph()
        assert g.edge_count() == 2


class TestDependencyGraphTraversal:
    """Tests for graph traversal operations."""

    def test_direct_dependents(self):
        g = _make_simple_graph()
        assert g.dependents("lib_a") == {"app"}
        assert g.dependents("lib_b") == {"lib_a"}

    def test_direct_dependencies(self):
        g = _make_simple_graph()
        assert g.dependencies("app") == {"lib_a"}
        assert g.dependencies("lib_a") == {"lib_b"}

    def test_transitive_dependents(self):
        g = _make_simple_graph()
        # lib_b's transitive dependents: lib_a, app
        result = g.transitive_dependents("lib_b")
        assert "lib_a" in result
        assert "app" in result

    def test_transitive_dependencies(self):
        g = _make_simple_graph()
        # app's transitive dependencies: lib_a, lib_b
        result = g.transitive_dependencies("app")
        assert "lib_a" in result
        assert "lib_b" in result

    def test_no_dependents_for_root(self):
        g = _make_simple_graph()
        assert g.dependents("app") == set()

    def test_no_dependencies_for_leaf(self):
        g = _make_simple_graph()
        assert g.dependencies("lib_b") == set()


class TestDependencyGraphRemoval:
    """Tests for package removal and state assessment."""

    def test_remove_package(self):
        g = _make_simple_graph()
        g2 = g.remove_package("lib_a")
        assert "lib_a" not in g2.packages
        assert "app" in g2.packages
        assert "lib_b" in g2.packages

    def test_remove_edge_source(self):
        g = _make_simple_graph()
        g2 = g.remove_package("lib_a")
        # Edge lib_a -> lib_b removed, edge app -> lib_a removed
        assert g2.edge_count() == 0

    def test_assess_state_leaf_removal(self):
        g = _make_simple_graph()
        # Removing lib_b: lib_a has no remaining deps → FAILED
        state = g.assess_state_without("lib_b")
        assert state.value == "failed"

    def test_assess_state_with_alternatives(self):
        g = _make_complex_graph()
        # Removing lib_d: both lib_a and lib_b depend on it
        # lib_a and lib_b have no backup listed for lib_d → DEGRADED
        state = g.assess_state_without("lib_d")
        # Since lib_a and lib_b lose a dep, should be degraded or failed
        assert state.value in ("degraded", "failed")

    def test_assess_state_isolated_removal(self):
        g = DependencyGraph()
        g.add_package(PackageInfo(name="isolated"))
        state = g.assess_state_without("isolated")
        assert state.value == "functional"


class TestDependencyGraphMatrix:
    """Tests for matrix operations."""

    def test_adjacency_matrix(self):
        g = _make_simple_graph()
        names, matrix = g.adjacency_matrix()
        assert len(names) == 3
        assert len(matrix) == 3
        assert len(matrix[0]) == 3

    def test_susceptance_matrix(self):
        g = _make_simple_graph()
        names, B = g.susceptance_matrix()
        assert len(names) == 3
        # Diagonal should be non-negative (sum of outgoing coupling)
        for i in range(len(names)):
            assert B[i][i] >= 0

    def test_susceptance_off_diagonal_negative(self):
        g = _make_simple_graph()
        names, B = g.susceptance_matrix()
        # Off-diagonal should be non-positive
        for i in range(len(names)):
            for j in range(len(names)):
                if i != j:
                    assert B[i][j] <= 0

    def test_get_coupling(self):
        g = _make_simple_graph()
        assert g.get_coupling("app", "lib_a") == 1.0
        assert g.get_coupling("lib_a", "app") == 0.0

    def test_direct_packages(self):
        g = _make_simple_graph()
        direct = g.direct_packages()
        assert "lib_a" in direct
        assert "lib_b" in direct
        assert "app" not in direct
