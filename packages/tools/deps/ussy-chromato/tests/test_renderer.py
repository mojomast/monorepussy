"""Tests for chromato.renderer — Chromatogram rendering."""

import json

import pytest

from ussy_chromato.models import (
    ChromatogramResult,
    Coelution,
    Dependency,
    EntanglementKind,
    Peak,
    PeakShape,
    Solvent,
)
from ussy_chromato.renderer import (
    render_chromatogram,
    render_diff,
    render_json,
    _diagnosis,
    _shape_label,
)


class TestRenderChromatogram:
    def test_basic_render(self):
        dep = Dependency(name="requests", version="2.28.0")
        peak = Peak(dep=dep, retention_time=0.5, area=0.45, width=0.2, shape=PeakShape.NARROW_TALL)
        result = ChromatogramResult(
            source="test.txt",
            solvent=Solvent.COUPLING,
            peaks=[peak],
        )
        output = render_chromatogram(result)
        assert "CHROMATOGRAM" in output
        assert "requests" in output
        assert "coupling" in output

    def test_render_with_coelution(self):
        dep_a = Dependency(name="celery", version="5.0")
        dep_b = Dependency(name="redis", version="4.0")
        peak_a = Peak(dep=dep_a, retention_time=2.4, area=0.6, width=0.5, shape=PeakShape.SHOULDER)
        peak_b = Peak(dep=dep_b, retention_time=2.4, area=0.5, width=0.5, shape=PeakShape.SYMMETRIC)
        coelution = Coelution(dep_a=dep_a, dep_b=dep_b, overlap=0.72, kind=EntanglementKind.MUTUAL)
        result = ChromatogramResult(
            source="test.txt",
            solvent=Solvent.COUPLING,
            peaks=[peak_a, peak_b],
            coelutions=[coelution],
        )
        output = render_chromatogram(result)
        assert "CO-ELUTION" in output
        assert "celery" in output
        assert "redis" in output

    def test_empty_result(self):
        result = ChromatogramResult(source="empty.txt")
        output = render_chromatogram(result)
        assert "CHROMATOGRAM" in output

    def test_multiple_peaks(self):
        peaks = [
            Peak(dep=Dependency(name=f"dep_{i}"), retention_time=float(i), area=0.1 * i, width=0.2, shape=PeakShape.SYMMETRIC)
            for i in range(5)
        ]
        result = ChromatogramResult(source="test.txt", peaks=peaks)
        output = render_chromatogram(result)
        assert "dep_0" in output
        assert "dep_4" in output


class TestRenderJson:
    def test_basic_json(self):
        dep = Dependency(name="requests", version="2.28.0", license="Apache-2.0")
        peak = Peak(dep=dep, retention_time=0.5, area=0.45, width=0.2, shape=PeakShape.NARROW_TALL)
        result = ChromatogramResult(
            source="test.txt",
            solvent=Solvent.COUPLING,
            peaks=[peak],
        )
        output = render_json(result)
        data = json.loads(output)
        assert data["source"] == "test.txt"
        assert data["solvent"] == "coupling"
        assert len(data["peaks"]) == 1
        assert data["peaks"][0]["name"] == "requests"
        assert data["peaks"][0]["retention_time"] == 0.5
        assert data["summary"]["total_dependencies"] == 1

    def test_json_with_coelution(self):
        dep_a = Dependency(name="a")
        dep_b = Dependency(name="b")
        peak_a = Peak(dep=dep_a, retention_time=1.0, area=0.5, width=0.3)
        peak_b = Peak(dep=dep_b, retention_time=1.0, area=0.4, width=0.3)
        coelution = Coelution(dep_a=dep_a, dep_b=dep_b, overlap=0.8, kind=EntanglementKind.CIRCULAR)
        result = ChromatogramResult(
            source="test.txt",
            peaks=[peak_a, peak_b],
            coelutions=[coelution],
        )
        output = render_json(result)
        data = json.loads(output)
        assert len(data["coelutions"]) == 1
        assert data["coelutions"][0]["kind"] == "circular"

    def test_empty_json(self):
        result = ChromatogramResult(source="empty.txt")
        output = render_json(result)
        data = json.loads(output)
        assert data["summary"]["total_dependencies"] == 0
        assert data["summary"]["health_ratio"] == 1.0


class TestRenderDiff:
    def test_basic_diff(self):
        dep_a = Dependency(name="requests", version="2.28.0")
        result_a = ChromatogramResult(
            source="old.txt",
            peaks=[Peak(dep=dep_a, retention_time=0.5, area=0.3, width=0.2)],
        )
        dep_b = Dependency(name="requests", version="2.31.0")
        result_b = ChromatogramResult(
            source="new.txt",
            peaks=[Peak(dep=dep_b, retention_time=0.3, area=0.3, width=0.2)],
        )
        output = render_diff(result_a, result_b)
        assert "DIFFERENTIAL" in output
        assert "requests" in output

    def test_diff_added_removed(self):
        dep_a = Dependency(name="old-dep")
        result_a = ChromatogramResult(
            source="old.txt",
            peaks=[Peak(dep=dep_a, retention_time=1.0)],
        )
        dep_b = Dependency(name="new-dep")
        result_b = ChromatogramResult(
            source="new.txt",
            peaks=[Peak(dep=dep_b, retention_time=0.5)],
        )
        output = render_diff(result_a, result_b)
        assert "ADDED" in output
        assert "REMOVED" in output


class TestHelperFunctions:
    def test_shape_label(self):
        assert _shape_label(PeakShape.NARROW_TALL) == "focused"
        assert _shape_label(PeakShape.WIDE_SHORT) == "wide"
        assert _shape_label(PeakShape.SHOULDER) == "shoulder"
        assert _shape_label(PeakShape.TAILING) == "tailing"
        assert _shape_label(PeakShape.SYMMETRIC) == "normal"

    def test_diagnosis(self):
        peak_focused = Peak(dep=Dependency(name="t"), shape=PeakShape.NARROW_TALL)
        assert "focused" in _diagnosis(peak_focused)

        peak_wide = Peak(dep=Dependency(name="t"), shape=PeakShape.WIDE_SHORT)
        assert "wide" in _diagnosis(peak_wide)
