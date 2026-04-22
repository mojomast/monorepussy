"""Tests for mint.debasement — Debasement tracking."""

import pytest
from datetime import datetime, timezone, timedelta

from mint.debasement import (
    compute_debasement_rate,
    project_zero_date,
    detect_recoinage_events,
    analyze_debasement,
    format_debasement_bar,
    format_debasement_report,
)


def make_date(year: int, month: int = 1, day: int = 1) -> datetime:
    """Helper to create timezone-aware dates."""
    return datetime(year, month, day, tzinfo=timezone.utc)


class TestComputeDebasementRate:
    """Test debasement rate calculation."""

    def test_stable_package(self):
        """Grades staying the same → rate = 0."""
        versions = [
            ("1.0.0", 60, make_date(2020, 1)),
            ("1.1.0", 60, make_date(2020, 7)),
        ]
        rate = compute_debasement_rate(versions)
        assert rate == 0.0

    def test_degrading_package(self):
        """Declining grades → positive rate (debasement)."""
        versions = [
            ("1.0.0", 65, make_date(2020, 1)),
            ("1.1.0", 55, make_date(2020, 7)),
        ]
        rate = compute_debasement_rate(versions)
        assert rate > 0  # Positive = losing grade points

    def test_improving_package(self):
        """Improving grades → negative rate."""
        versions = [
            ("1.0.0", 40, make_date(2020, 1)),
            ("1.1.0", 60, make_date(2020, 7)),
        ]
        rate = compute_debasement_rate(versions)
        assert rate < 0  # Negative = gaining grade points

    def test_single_version(self):
        """Single version → rate = 0."""
        versions = [("1.0.0", 60, make_date(2020))]
        rate = compute_debasement_rate(versions)
        assert rate == 0.0

    def test_empty_versions(self):
        """No versions → rate = 0."""
        rate = compute_debasement_rate([])
        assert rate == 0.0

    def test_gradual_debasement(self):
        """Gradual decline over many versions."""
        versions = [
            ("1.0.0", 65, make_date(2020, 1)),
            ("2.0.0", 60, make_date(2021, 1)),
            ("3.0.0", 55, make_date(2022, 1)),
            ("4.0.0", 50, make_date(2023, 1)),
        ]
        rate = compute_debasement_rate(versions)
        assert rate > 0
        # Should be roughly 5 points per 12 months = ~0.41 per month
        assert 0.2 < rate < 0.8


class TestProjectZeroDate:
    """Test P-1 projection."""

    def test_degrading_package(self):
        """A degrading package should have a projected zero date."""
        date = project_zero_date(30, 1.0, make_date(2024, 1))
        assert date is not None
        assert date > make_date(2024, 1)

    def test_stable_package_no_projection(self):
        """A stable package should not have a projected zero date."""
        date = project_zero_date(60, 0.0, make_date(2024, 1))
        assert date is None

    def test_improving_package_no_projection(self):
        """An improving package should not have a projected zero date."""
        date = project_zero_date(60, -0.5, make_date(2024, 1))
        assert date is None

    def test_already_at_p1(self):
        """Package already at P-1 should project to now or past."""
        date = project_zero_date(1, 1.0, make_date(2024, 1))
        assert date is not None
        assert date <= make_date(2024, 2)


class TestDetectRecoinageEvents:
    """Test recoinage event detection."""

    def test_major_improvement(self):
        """A grade jump > 20 should be detected as recoinage."""
        versions = [
            ("1.0.0", 30, make_date(2020)),
            ("2.0.0", 65, make_date(2021)),  # +35 points = recoinage
        ]
        events = detect_recoinage_events(versions)
        assert len(events) == 1
        assert events[0] == 1

    def test_gradual_change_no_recoinage(self):
        """Gradual changes should not be flagged as recoinage."""
        versions = [
            ("1.0.0", 60, make_date(2020)),
            ("1.1.0", 62, make_date(2021)),
            ("1.2.0", 64, make_date(2022)),
        ]
        events = detect_recoinage_events(versions)
        assert len(events) == 0

    def test_custom_threshold(self):
        """Custom threshold should be respected."""
        versions = [
            ("1.0.0", 60, make_date(2020)),
            ("2.0.0", 72, make_date(2021)),  # grade can't exceed 70 in practice
        ]
        events = detect_recoinage_events(versions, threshold=100)
        assert len(events) == 0  # threshold too high

    def test_empty_versions(self):
        events = detect_recoinage_events([])
        assert len(events) == 0


class TestAnalyzeDebasement:
    """Test full debasement analysis."""

    def test_full_analysis(self):
        versions = [
            ("1.0.0", 65, make_date(2020, 1)),
            ("2.0.0", 55, make_date(2021, 1)),
        ]
        curve = analyze_debasement("test-pkg", versions)
        assert curve.package == "test-pkg"
        assert curve.debasement_rate > 0
        assert curve.projected_zero_date is not None
        assert len(curve.versions) == 2

    def test_stable_analysis(self):
        versions = [
            ("1.0.0", 60, make_date(2020, 1)),
            ("2.0.0", 60, make_date(2021, 1)),
        ]
        curve = analyze_debasement("stable-pkg", versions)
        assert curve.debasement_rate == 0.0
        assert curve.projected_zero_date is None


class TestFormatDebasementBar:
    """Test visual debasement bar formatting."""

    def test_full_bar(self):
        bar = format_debasement_bar(70)
        assert len(bar) > 0
        assert "█" in bar

    def test_empty_bar(self):
        bar = format_debasement_bar(1)
        assert len(bar) >= 0

    def test_half_bar(self):
        bar = format_debasement_bar(35)
        assert "█" in bar


class TestFormatDebasementReport:
    """Test debasement report formatting."""

    def test_report_output(self):
        from mint.debasement import DebasementCurve
        curve = DebasementCurve(
            package="test-pkg",
            versions=[
                ("1.0.0", 65, make_date(2020)),
                ("2.0.0", 55, make_date(2021)),
            ],
            debasement_rate=0.83,
            recoinage_events=[],
        )
        report = format_debasement_report(curve)
        assert "test-pkg" in report
        assert "1.0.0" in report
        assert "0.83" in report

    def test_empty_versions(self):
        from mint.debasement import DebasementCurve
        curve = DebasementCurve(package="empty-pkg")
        report = format_debasement_report(curve)
        assert "empty-pkg" in report
