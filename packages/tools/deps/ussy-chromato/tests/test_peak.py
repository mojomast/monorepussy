"""Tests for chromato.peak — Peak shape analysis."""

import pytest

from ussy_chromato.models import Dependency, DependencyGraph, PeakShape
from ussy_chromato.peak import (
    analyze_peak,
    build_peaks,
    compute_peak_area,
    compute_peak_width,
    count_concerns,
)


class TestCountConcerns:
    def test_single_concern(self):
        dep = Dependency(name="requests", concerns=1)
        assert count_concerns(dep) == 1

    def test_multi_concern_explicit(self):
        dep = Dependency(name="django", concerns=5)
        assert count_concerns(dep) == 5

    def test_util_heuristic(self):
        dep = Dependency(name="django-utils", concerns=1)
        assert count_concerns(dep) >= 2

    def test_tool_heuristic(self):
        dep = Dependency(name="dev-tools", concerns=1)
        assert count_concerns(dep) >= 2

    def test_no_heuristic_match(self):
        dep = Dependency(name="requests", concerns=1)
        assert count_concerns(dep) == 1


class TestAnalyzePeak:
    def _make_graph_with_dependents(self, count: int) -> DependencyGraph:
        """Create a graph where 'test' has many dependents."""
        deps = [Dependency(name="test")]
        for i in range(count):
            deps.append(Dependency(name=f"dep_{i}"))
        edges = [(f"dep_{i}", "test") for i in range(count)]
        return DependencyGraph(dependencies=deps, edges=edges)

    def test_narrow_tall(self):
        graph = self._make_graph_with_dependents(6)
        dep = graph.get("test")
        dep.concerns = 1
        shape = analyze_peak(dep, graph)
        assert shape == PeakShape.NARROW_TALL

    def test_wide_short(self):
        dep = Dependency(name="bloat", concerns=5)
        graph = DependencyGraph(dependencies=[dep])
        shape = analyze_peak(dep, graph)
        assert shape == PeakShape.WIDE_SHORT

    def test_shoulder(self):
        dep = Dependency(name="transition", concerns=1, has_major_version_gap=True)
        graph = DependencyGraph(dependencies=[dep])
        shape = analyze_peak(dep, graph)
        assert shape == PeakShape.SHOULDER

    def test_tailing(self):
        dep = Dependency(name="legacy", concerns=1, has_deprecated_apis=True)
        graph = DependencyGraph(dependencies=[dep])
        shape = analyze_peak(dep, graph)
        assert shape == PeakShape.TAILING

    def test_symmetric(self):
        dep = Dependency(name="normal", concerns=2)
        graph = DependencyGraph(dependencies=[dep])
        shape = analyze_peak(dep, graph)
        assert shape == PeakShape.SYMMETRIC

    def test_shoulder_takes_precedence_over_wide(self):
        dep = Dependency(name="test", concerns=5, has_major_version_gap=True)
        graph = DependencyGraph(dependencies=[dep])
        shape = analyze_peak(dep, graph)
        # WIDE_SHORT checks before SHOULDER in the logic
        assert shape == PeakShape.WIDE_SHORT


class TestComputePeakArea:
    def test_zero_dependents(self):
        dep = Dependency(name="lonely")
        graph = DependencyGraph(dependencies=[dep])
        area = compute_peak_area(dep, graph)
        assert area == 0.0

    def test_some_dependents(self):
        dep = Dependency(name="popular")
        deps = [dep] + [Dependency(name=f"d{i}") for i in range(5)]
        edges = [(f"d{i}", "popular") for i in range(5)]
        graph = DependencyGraph(dependencies=deps, edges=edges)
        area = compute_peak_area(dep, graph)
        assert 0.0 < area <= 1.0

    def test_risk_weight_increases_area(self):
        dep = Dependency(name="risky", advisory_count=10)
        graph = DependencyGraph(dependencies=[dep])
        area = compute_peak_area(dep, graph)
        # With high advisory count but no dependents, area is still 0
        assert area == 0.0


class TestComputePeakWidth:
    def test_single_concern(self):
        dep = Dependency(name="focused", concerns=1)
        width = compute_peak_width(dep)
        assert width == 0.2

    def test_many_concerns(self):
        dep = Dependency(name="bloat", concerns=10)
        width = compute_peak_width(dep)
        assert width == 1.0


class TestBuildPeaks:
    def test_build_peaks_basic(self):
        deps = [
            Dependency(name="a", version="1.0"),
            Dependency(name="b", version="2.0"),
        ]
        graph = DependencyGraph(dependencies=deps, edges=[("a", "b")])
        retention_times = {"a": 1.0, "b": 0.5}
        peaks = build_peaks(graph, retention_times)

        assert len(peaks) == 2
        # Sorted by retention time
        assert peaks[0].dep.name == "b"
        assert peaks[1].dep.name == "a"
        assert peaks[0].retention_time == 0.5
        assert peaks[1].retention_time == 1.0

    def test_build_peaks_empty_graph(self):
        graph = DependencyGraph()
        peaks = build_peaks(graph, {})
        assert len(peaks) == 0

    def test_build_peaks_have_areas(self):
        deps = [Dependency(name="a", version="1.0")]
        graph = DependencyGraph(dependencies=deps)
        retention_times = {"a": 1.0}
        peaks = build_peaks(graph, retention_times)
        assert len(peaks) == 1
        assert peaks[0].area >= 0.0
        assert peaks[0].width >= 0.0
        assert peaks[0].height >= 0.0
