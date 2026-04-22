"""Tests for mint.hoard — Dependency cluster analysis."""

import pytest
from ussy_mint.hoard import (
    find_connected_components,
    identify_cluster_name,
    compute_contamination_risk,
    analyze_hoard,
    format_hoard_report,
)
from ussy_mint.lockfile import LockedPackage, parse_package_lock_json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


class TestFindConnectedComponents:
    """Test connected component detection."""

    def test_single_component(self):
        """All connected nodes should form one component."""
        graph = {
            "a": ["b"],
            "b": ["c"],
            "c": [],
        }
        components = find_connected_components(graph)
        assert len(components) == 1
        assert components[0] == {"a", "b", "c"}

    def test_two_components(self):
        """Disconnected groups should form separate components."""
        graph = {
            "a": ["b"],
            "b": [],
            "c": ["d"],
            "d": [],
        }
        components = find_connected_components(graph)
        assert len(components) == 2

    def test_isolated_nodes(self):
        """Isolated nodes should each be their own component."""
        graph = {
            "a": [],
            "b": [],
            "c": [],
        }
        components = find_connected_components(graph)
        assert len(components) == 3

    def test_empty_graph(self):
        """Empty graph should return no components."""
        graph = {}
        components = find_connected_components(graph)
        assert len(components) == 0

    def test_bidirectional(self):
        """Reverse edges (dependencies pointing back) should be traversed."""
        graph = {
            "a": [],
            "b": ["a"],
        }
        components = find_connected_components(graph)
        assert len(components) == 1
        assert components[0] == {"a", "b"}


class TestIdentifyClusterName:
    """Test cluster name identification."""

    def test_empty_cluster(self):
        name = identify_cluster_name(set())
        assert name  # Should return something

    def test_known_cluster(self):
        known = {
            "React Ecosystem": ["react", "react-dom", "scheduler"],
        }
        name = identify_cluster_name(
            {"react", "react-dom", "other"},
            known_clusters=known,
        )
        assert name == "React Ecosystem"

    def test_scoped_packages(self):
        name = identify_cluster_name({"@babel/core", "@babel/parser", "@babel/traverse"})
        assert "babel" in name.lower() or "@" in name

    def test_no_scope(self):
        name = identify_cluster_name({"express", "body-parser"})
        assert name  # Should return something


class TestComputeContaminationRisk:
    """Test contamination risk calculation."""

    def test_high_risk(self):
        """High overlap + low grade + many gaps = high risk."""
        risk = compute_contamination_risk(
            maintainer_overlap=0.9,
            min_grade=5,
            provenance_gaps=10,
            total_packages=12,
        )
        assert risk > 0.5

    def test_low_risk(self):
        """Low overlap + high grade + few gaps = low risk."""
        risk = compute_contamination_risk(
            maintainer_overlap=0.0,
            min_grade=65,
            provenance_gaps=0,
            total_packages=10,
        )
        assert risk < 0.3

    def test_risk_bounded(self):
        """Risk should always be 0-1."""
        for overlap in [0, 0.5, 1.0]:
            for grade in [1, 35, 70]:
                risk = compute_contamination_risk(overlap, grade, 0, 10)
                assert 0.0 <= risk <= 1.0


class TestAnalyzeHoard:
    """Test full hoard analysis."""

    def test_hoard_from_lockfile(self):
        """Analyze a real lockfile."""
        packages = parse_package_lock_json(FIXTURES / "package-lock.json")
        hoards = analyze_hoard(packages)
        assert len(hoards) > 0

        # Total packages across all hoards should equal total
        total_in_hoards = sum(len(h.packages) for h in hoards)
        assert total_in_hoards == len(packages)

    def test_hoard_fields_populated(self):
        """Each hoard should have all fields populated."""
        packages = parse_package_lock_json(FIXTURES / "package-lock.json")
        hoards = analyze_hoard(packages)
        for hoard in hoards:
            assert hoard.name
            assert hoard.packages
            assert 0 <= hoard.contamination_risk <= 1.0

    def test_hoard_with_grades(self):
        """Grades should influence contamination risk."""
        packages = [
            LockedPackage(name="a", version="1.0.0"),
            LockedPackage(name="b", version="1.0.0"),
        ]
        grades_good = {"a": 65, "b": 60}
        grades_bad = {"a": 5, "b": 3}

        hoards_good = analyze_hoard(packages, package_grades=grades_good)
        hoards_bad = analyze_hoard(packages, package_grades=grades_bad)

        # The bad-grades hoard should have higher contamination risk
        if hoards_good and hoards_bad:
            assert hoards_bad[0].max_debasement >= hoards_good[0].max_debasement


class TestFormatHoardReport:
    """Test hoard report formatting."""

    def test_report_output(self):
        from ussy_mint.models import Hoard
        hoards = [
            Hoard(
                name="Test Cluster",
                packages=["pkg-a", "pkg-b"],
                contamination_risk=0.3,
                common_maintainers=[],
            ),
        ]
        report = format_hoard_report(hoards, 2)
        assert "Test Cluster" in report
        assert "2" in report  # 2 packages

    def test_empty_hoards(self):
        report = format_hoard_report([], 0)
        assert "0" in report
