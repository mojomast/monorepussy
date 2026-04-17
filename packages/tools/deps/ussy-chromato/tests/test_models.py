"""Tests for chromato.models — Core data models."""

from datetime import datetime, timezone, timedelta

import pytest

from chromato.models import (
    Coelution,
    ChromatogramResult,
    Dependency,
    DependencyGraph,
    EntanglementKind,
    LICENSE_RESTRICTIVENESS,
    Peak,
    PeakShape,
    Solvent,
)


class TestPeakShape:
    def test_values(self):
        assert PeakShape.NARROW_TALL.value == "narrow_tall"
        assert PeakShape.WIDE_SHORT.value == "wide_short"
        assert PeakShape.SHOULDER.value == "shoulder"
        assert PeakShape.TAILING.value == "tailing"
        assert PeakShape.SYMMETRIC.value == "symmetric"

    def test_all_shapes_exist(self):
        assert len(PeakShape) == 5


class TestEntanglementKind:
    def test_values(self):
        assert EntanglementKind.CIRCULAR.value == "circular"
        assert EntanglementKind.CONFLICT.value == "conflict"
        assert EntanglementKind.MUTUAL.value == "mutual"

    def test_all_kinds_exist(self):
        assert len(EntanglementKind) == 3


class TestSolvent:
    def test_values(self):
        assert Solvent.COUPLING.value == "coupling"
        assert Solvent.RISK.value == "risk"
        assert Solvent.FRESHNESS.value == "freshness"
        assert Solvent.LICENSE.value == "license"

    def test_all_solvents_exist(self):
        assert len(Solvent) == 4


class TestLicenseRestrictiveness:
    def test_mit_is_low(self):
        assert LICENSE_RESTRICTIVENESS["MIT"] < 0.2

    def test_gpl_is_high(self):
        assert LICENSE_RESTRICTIVENESS["GPL-3.0"] > 0.5

    def test_proprietary_is_max(self):
        assert LICENSE_RESTRICTIVENESS["Proprietary"] == 1.0

    def test_unknown_has_default(self):
        assert LICENSE_RESTRICTIVENESS["UNKNOWN"] == 0.6


class TestDependency:
    def test_basic_creation(self):
        dep = Dependency(name="requests", version="2.28.0")
        assert dep.name == "requests"
        assert dep.version == "2.28.0"
        assert dep.license == "UNKNOWN"
        assert dep.advisory_count == 0
        assert dep.concerns == 1
        assert dep.is_dev is False
        assert dep.is_optional is False

    def test_dependent_count(self):
        dep = Dependency(name="django", dependents=["app1", "app2", "app3"])
        assert dep.dependent_count == 3

    def test_dependent_count_empty(self):
        dep = Dependency(name="flask")
        assert dep.dependent_count == 0

    def test_days_since_update_with_date(self):
        recent = datetime.now(timezone.utc) - timedelta(days=10)
        dep = Dependency(name="requests", last_updated=recent)
        days = dep.days_since_update()
        assert 9.5 < days < 10.5

    def test_days_since_update_none(self):
        dep = Dependency(name="requests", last_updated=None)
        assert dep.days_since_update() == 9999.0

    def test_days_since_update_future(self):
        future = datetime.now(timezone.utc) + timedelta(days=5)
        dep = Dependency(name="requests", last_updated=future)
        # Should clamp to 0
        assert dep.days_since_update() >= 0


class TestDependencyGraph:
    def test_empty_graph(self):
        graph = DependencyGraph()
        assert len(graph.dependencies) == 0
        assert len(graph.edges) == 0

    def test_get_dependency(self):
        dep = Dependency(name="requests")
        graph = DependencyGraph(dependencies=[dep])
        found = graph.get("requests")
        assert found is not None
        assert found.name == "requests"

    def test_get_missing_dependency(self):
        graph = DependencyGraph()
        assert graph.get("nonexistent") is None

    def test_coupling_depth_simple(self):
        dep_a = Dependency(name="a")
        dep_b = Dependency(name="b")
        graph = DependencyGraph(
            dependencies=[dep_a, dep_b],
            edges=[("a", "b")],
        )
        assert graph.coupling_depth(dep_a) == 1
        assert graph.coupling_depth(dep_b) == 0

    def test_coupling_depth_chain(self):
        deps = [Dependency(name=n) for n in ["a", "b", "c"]]
        graph = DependencyGraph(
            dependencies=deps,
            edges=[("a", "b"), ("b", "c")],
        )
        assert graph.coupling_depth(deps[0]) == 2
        assert graph.coupling_depth(deps[1]) == 1
        assert graph.coupling_depth(deps[2]) == 0

    def test_coupling_depth_circular(self):
        deps = [Dependency(name=n) for n in ["a", "b"]]
        graph = DependencyGraph(
            dependencies=deps,
            edges=[("a", "b"), ("b", "a")],
        )
        # Should not infinite loop; just returns 0 for visited
        depth = graph.coupling_depth(deps[0])
        assert isinstance(depth, int)

    def test_dependent_count(self):
        deps = [Dependency(name=n) for n in ["a", "b", "c"]]
        graph = DependencyGraph(
            dependencies=deps,
            edges=[("a", "b"), ("c", "b")],
        )
        assert graph.dependent_count(deps[1]) == 2  # b has 2 dependents

    def test_has_circular_true(self):
        deps = [Dependency(name=n) for n in ["a", "b"]]
        graph = DependencyGraph(
            dependencies=deps,
            edges=[("a", "b"), ("b", "a")],
        )
        assert graph.has_circular("a", "b") is True

    def test_has_circular_false(self):
        deps = [Dependency(name=n) for n in ["a", "b"]]
        graph = DependencyGraph(
            dependencies=deps,
            edges=[("a", "b")],
        )
        assert graph.has_circular("a", "b") is False

    def test_has_path(self):
        deps = [Dependency(name=n) for n in ["a", "b", "c"]]
        graph = DependencyGraph(
            dependencies=deps,
            edges=[("a", "b"), ("b", "c")],
        )
        assert graph._has_path("a", "c") is True
        assert graph._has_path("c", "a") is False


class TestPeak:
    def test_default_values(self):
        dep = Dependency(name="test")
        peak = Peak(dep=dep)
        assert peak.retention_time == 0.0
        assert peak.area == 0.0
        assert peak.width == 0.0
        assert peak.shape == PeakShape.SYMMETRIC


class TestCoelution:
    def test_creation(self):
        dep_a = Dependency(name="a")
        dep_b = Dependency(name="b")
        ce = Coelution(dep_a=dep_a, dep_b=dep_b, overlap=0.5, kind=EntanglementKind.MUTUAL)
        assert ce.dep_a.name == "a"
        assert ce.dep_b.name == "b"
        assert ce.overlap == 0.5
        assert ce.kind == EntanglementKind.MUTUAL


class TestChromatogramResult:
    def test_default_values(self):
        result = ChromatogramResult()
        assert result.source == ""
        assert result.solvent == Solvent.COUPLING
        assert len(result.peaks) == 0
        assert len(result.coelutions) == 0
        assert result.timestamp is not None
