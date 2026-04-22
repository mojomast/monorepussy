"""Tests for chromato.coelution — Co-elution detection."""

import pytest

from ussy_chromato.models import (
    Coelution,
    Dependency,
    DependencyGraph,
    EntanglementKind,
    Peak,
    PeakShape,
)
from ussy_chromato.coelution import classify_entanglement, detect_coelution, peak_overlap


class TestPeakOverlap:
    def test_no_overlap(self):
        pa = Peak(dep=Dependency(name="a"), retention_time=0.0, width=0.2)
        pb = Peak(dep=Dependency(name="b"), retention_time=10.0, width=0.2)
        overlap = peak_overlap(pa, pb)
        assert overlap == 0.0

    def test_complete_overlap(self):
        pa = Peak(dep=Dependency(name="a"), retention_time=1.0, width=0.5)
        pb = Peak(dep=Dependency(name="b"), retention_time=1.0, width=0.5)
        overlap = peak_overlap(pa, pb)
        assert overlap > 0.9

    def test_partial_overlap(self):
        pa = Peak(dep=Dependency(name="a"), retention_time=1.0, width=0.5)
        pb = Peak(dep=Dependency(name="b"), retention_time=1.2, width=0.5)
        overlap = peak_overlap(pa, pb)
        assert 0.0 < overlap < 1.0

    def test_overlap_symmetric(self):
        pa = Peak(dep=Dependency(name="a"), retention_time=1.0, width=0.5)
        pb = Peak(dep=Dependency(name="b"), retention_time=1.3, width=0.5)
        overlap_ab = peak_overlap(pa, pb)
        overlap_ba = peak_overlap(pb, pa)
        assert overlap_ab == overlap_ba


class TestClassifyEntanglement:
    def test_circular(self):
        deps = [Dependency(name="a"), Dependency(name="b")]
        graph = DependencyGraph(dependencies=deps, edges=[("a", "b"), ("b", "a")])
        kind = classify_entanglement("a", "b", graph)
        assert kind == EntanglementKind.CIRCULAR

    def test_conflict(self):
        # Both a and b depend on common dep c
        deps = [Dependency(name="a"), Dependency(name="b"), Dependency(name="c")]
        graph = DependencyGraph(dependencies=deps, edges=[("a", "c"), ("b", "c")])
        kind = classify_entanglement("a", "b", graph)
        assert kind == EntanglementKind.CONFLICT

    def test_mutual_one_direction(self):
        deps = [Dependency(name="a"), Dependency(name="b")]
        graph = DependencyGraph(dependencies=deps, edges=[("a", "b")])
        kind = classify_entanglement("a", "b", graph)
        # a -> b, no common deps, one-directional => MUTUAL
        assert kind == EntanglementKind.MUTUAL

    def test_mutual_no_edges(self):
        deps = [Dependency(name="a"), Dependency(name="b")]
        graph = DependencyGraph(dependencies=deps, edges=[])
        kind = classify_entanglement("a", "b", graph)
        # No relationship => default MUTUAL
        assert kind == EntanglementKind.MUTUAL


class TestDetectCoelution:
    def test_no_coelutions(self):
        pa = Peak(dep=Dependency(name="a"), retention_time=0.0, width=0.2)
        pb = Peak(dep=Dependency(name="b"), retention_time=10.0, width=0.2)
        graph = DependencyGraph(dependencies=[Dependency(name="a"), Dependency(name="b")])
        coelutions = detect_coelution([pa, pb], graph)
        assert len(coelutions) == 0

    def test_detect_coelution(self):
        pa = Peak(dep=Dependency(name="a"), retention_time=1.0, width=0.5)
        pb = Peak(dep=Dependency(name="b"), retention_time=1.1, width=0.5)
        graph = DependencyGraph(
            dependencies=[Dependency(name="a"), Dependency(name="b")],
            edges=[("a", "b"), ("b", "a")],
        )
        coelutions = detect_coelution([pa, pb], graph)
        assert len(coelutions) > 0
        assert coelutions[0].overlap > 0.3

    def test_threshold_filtering(self):
        pa = Peak(dep=Dependency(name="a"), retention_time=1.0, width=0.5)
        pb = Peak(dep=Dependency(name="b"), retention_time=1.1, width=0.5)
        graph = DependencyGraph(
            dependencies=[Dependency(name="a"), Dependency(name="b")],
        )
        # High threshold should filter out weak overlaps
        coelutions_low = detect_coelution([pa, pb], graph, threshold=0.1)
        coelutions_high = detect_coelution([pa, pb], graph, threshold=0.9)
        assert len(coelutions_low) >= len(coelutions_high)

    def test_empty_peaks(self):
        graph = DependencyGraph()
        coelutions = detect_coelution([], graph)
        assert len(coelutions) == 0

    def test_single_peak(self):
        pa = Peak(dep=Dependency(name="a"), retention_time=1.0, width=0.5)
        graph = DependencyGraph(dependencies=[Dependency(name="a")])
        coelutions = detect_coelution([pa], graph)
        assert len(coelutions) == 0
