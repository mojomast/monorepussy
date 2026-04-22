"""Tests for curator.conservation."""

from __future__ import annotations

from pathlib import Path

import pytest

from ussy_curator.conservation import ConservationReport


class TestConservationReport:
    def test_metrics_calculated(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("Hello world.")
        report = ConservationReport(f)
        assert "age_days" in report.metrics
        assert report.metrics["age_days"] >= 0

    def test_deterioration_rate_positive(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("Hello world.")
        report = ConservationReport(f)
        rate = report.deterioration_rate()
        assert rate > 0.0

    def test_condition_index_range(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("Hello world.")
        report = ConservationReport(f)
        ci = report.condition_index()
        assert 0.0 <= ci <= 100.0

    def test_grade_excellent_for_fresh(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("Fresh document.")
        report = ConservationReport(f)
        # Fresh file should have high condition
        assert report.grade() in ConservationReport.GRADES

    def test_treatment_for_fresh(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("Fresh document.")
        report = ConservationReport(f)
        assert "Preventive" in report.recommended_treatment()

    def test_link_rot_zero_when_no_links(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("No links here.")
        report = ConservationReport(f)
        assert report.metrics["link_rot"] == 0.0

    def test_link_rot_with_broken_link(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("See [broken](missing.md)")
        report = ConservationReport(f)
        assert report.metrics["link_rot"] == 1.0

    def test_dependency_drift_no_deps(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("No dependencies.")
        report = ConservationReport(f)
        assert report.metrics["dependency_drift"] == 0.0

    def test_grades_ordered(self) -> None:
        assert ConservationReport.GRADES == ["Excellent", "Good", "Fair", "Poor", "Critical"]
