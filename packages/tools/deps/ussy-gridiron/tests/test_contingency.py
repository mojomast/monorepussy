"""Tests for the contingency analyzer (N-1)."""

import pytest

from gridiron.graph import DependencyGraph
from gridiron.instruments.contingency import ContingencyAnalyzer
from gridiron.models import DependencyEdge, PackageInfo, SystemState


def _make_graph_with_spof():
    """Create a graph where lib_b is a SPOF.

    app → lib_a → lib_b
    app → lib_c
    """
    g = DependencyGraph()
    g.add_package(PackageInfo(name="app", is_direct=False))
    g.add_package(PackageInfo(name="lib_a", is_direct=True))
    g.add_package(PackageInfo(name="lib_b", is_direct=True))
    g.add_package(PackageInfo(name="lib_c", is_direct=True))
    g.add_edge(DependencyEdge(source="app", target="lib_a"))
    g.add_edge(DependencyEdge(source="lib_a", target="lib_b"))
    g.add_edge(DependencyEdge(source="app", target="lib_c"))
    return g


def _make_graph_resilient():
    """Create a graph with no SPOF due to backup paths.

    app → lib_a → lib_b
    app → lib_c → lib_b  (alternative path to lib_b)
    """
    g = DependencyGraph()
    g.add_package(PackageInfo(name="app", is_direct=False))
    g.add_package(PackageInfo(name="lib_a", is_direct=True))
    g.add_package(PackageInfo(name="lib_b", is_direct=True))
    g.add_package(PackageInfo(name="lib_c", is_direct=True))
    g.add_edge(DependencyEdge(source="app", target="lib_a"))
    g.add_edge(DependencyEdge(source="app", target="lib_c"))
    g.add_edge(DependencyEdge(source="lib_a", target="lib_b"))
    g.add_edge(DependencyEdge(source="lib_c", target="lib_b"))
    return g


class TestContingencyAnalyzer:
    """Tests for N-1 contingency analysis."""

    def test_analyze_basic(self):
        g = _make_graph_with_spof()
        analyzer = ContingencyAnalyzer(g)
        report = analyzer.analyze()
        assert report.total_packages == 4
        assert report.compliance_score <= 100.0

    def test_spof_detected(self):
        g = _make_graph_with_spof()
        analyzer = ContingencyAnalyzer(g)
        report = analyzer.analyze()
        # lib_b should be a SPOF since lib_a depends solely on it
        spof_names = [s.removed_package for s in report.spof_register]
        assert "lib_b" in spof_names

    def test_resilient_graph_higher_score(self):
        g_spof = _make_graph_with_spof()
        g_res = _make_graph_resilient()

        report_spof = ContingencyAnalyzer(g_spof).analyze()
        report_res = ContingencyAnalyzer(g_res).analyze()

        # Resilient graph should have higher compliance score
        assert report_res.compliance_score >= report_spof.compliance_score

    def test_analyze_specific(self):
        g = _make_graph_with_spof()
        analyzer = ContingencyAnalyzer(g)
        result = analyzer.analyze_specific("lib_b")
        assert result.removed_package == "lib_b"
        assert result.system_state == SystemState.FAILED
        assert result.is_spof is True

    def test_blast_radius_calculation(self):
        g = _make_graph_with_spof()
        analyzer = ContingencyAnalyzer(g)
        result = analyzer.analyze_specific("lib_b")
        # lib_b's dependents: lib_a, app → blast radius > 0
        assert result.blast_radius > 0

    def test_no_spof_for_root(self):
        g = _make_graph_with_spof()
        analyzer = ContingencyAnalyzer(g)
        result = analyzer.analyze_specific("app")
        # app has no dependents, so removing it shouldn't cause failure
        assert result.system_state == SystemState.FUNCTIONAL

    def test_recommendation_provided_for_spof(self):
        g = DependencyGraph()
        g.add_package(PackageInfo(name="app", is_direct=False))
        g.add_package(PackageInfo(name="critical", is_direct=True))
        g.add_edge(DependencyEdge(source="app", target="critical"))

        analyzer = ContingencyAnalyzer(g)
        result = analyzer.analyze_specific("critical")
        assert result.recommendation != ""

    def test_recommendation_with_backup(self):
        g = DependencyGraph()
        g.add_package(PackageInfo(name="app", is_direct=False))
        g.add_package(PackageInfo(name="critical", is_direct=True, backup_packages=["alternative"]))
        g.add_edge(DependencyEdge(source="app", target="critical"))

        analyzer = ContingencyAnalyzer(g)
        result = analyzer.analyze_specific("critical")
        assert "alternative" in result.recommendation

    def test_empty_graph(self):
        g = DependencyGraph()
        analyzer = ContingencyAnalyzer(g)
        report = analyzer.analyze()
        assert report.total_packages == 0
        assert report.compliance_score == 100.0

    def test_all_results_populated(self):
        g = _make_graph_with_spof()
        analyzer = ContingencyAnalyzer(g)
        report = analyzer.analyze()
        assert len(report.all_results) == 4  # 4 packages
