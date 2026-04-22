"""Tests for the archaeology module."""

import pytest

from ussy_kintsugi.joint import Joint, JointStore
from ussy_kintsugi.archaeology import (
    FractureEvent,
    ArchaeologyReport,
    build_archaeology_report,
    detect_pattern,
    generate_suggestion,
    format_archaeology_report,
)


class TestFractureEvent:
    """Test FractureEvent dataclass."""

    def test_defaults(self):
        f = FractureEvent()
        assert f.timestamp == ""
        assert f.bug_ref == ""
        assert f.severity == ""

    def test_with_values(self):
        f = FractureEvent(
            timestamp="2024-03-15T10:30:00+00:00",
            bug_ref="PROJ-892",
            severity="critical",
            break_description="null pointer",
            repair_description="added guard",
            status="solid_gold",
        )
        assert f.bug_ref == "PROJ-892"
        assert f.severity == "critical"


class TestArchaeologyReport:
    """Test ArchaeologyReport dataclass."""

    def test_defaults(self):
        r = ArchaeologyReport()
        assert r.fractures == []
        assert r.total_months == 0
        assert r.pattern == ""

    def test_with_fractures(self):
        r = ArchaeologyReport(
            file="test.py",
            fractures=[FractureEvent(bug_ref="X-1")],
        )
        assert len(r.fractures) == 1


class TestBuildArchaeologyReport:
    """Test building archaeology reports from joint data."""

    def test_no_joints(self, tmp_path):
        report = build_archaeology_report("nonexistent.py", root=str(tmp_path))
        assert len(report.fractures) == 0

    def test_with_joints(self, tmp_path):
        store = JointStore(root=str(tmp_path))
        j1 = Joint(
            id="j-1",
            file="src/auth/login.py",
            line=1,
            timestamp="2024-03-15T10:30:00+00:00",
            bug_ref="PROJ-892",
            severity="critical",
            break_description="null pointer",
            repair_description="added guard",
            status="solid_gold",
        )
        j2 = Joint(
            id="j-2",
            file="src/auth/login.py",
            line=10,
            timestamp="2024-07-20T10:30:00+00:00",
            bug_ref="PROJ-1203",
            severity="warning",
            break_description="race condition",
            repair_description="added lock",
            status="hollow",
        )
        store.save(j1)
        store.save(j2)

        report = build_archaeology_report("src/auth/login.py", root=str(tmp_path))
        assert len(report.fractures) == 2
        assert report.fractures[0].bug_ref == "PROJ-892"
        assert report.fractures[1].bug_ref == "PROJ-1203"
        assert report.total_months > 0

    def test_single_joint(self, tmp_path):
        store = JointStore(root=str(tmp_path))
        j = Joint(
            id="j-1",
            file="test.py",
            timestamp="2024-03-15T10:30:00+00:00",
            bug_ref="X-1",
        )
        store.save(j)

        report = build_archaeology_report("test.py", root=str(tmp_path))
        assert len(report.fractures) == 1
        assert report.total_months == 0  # Only one fracture


class TestDetectPattern:
    """Test fracture pattern detection."""

    def test_empty(self):
        assert detect_pattern([]) == ""

    def test_all_critical(self):
        fractures = [
            FractureEvent(severity="critical", break_description="crash A"),
            FractureEvent(severity="critical", break_description="crash B"),
        ]
        result = detect_pattern(fractures)
        assert "chronic failure" in result

    def test_repeated_keywords(self):
        fractures = [
            FractureEvent(severity="warning", break_description="null pointer exception"),
            FractureEvent(severity="warning", break_description="null pointer dereference"),
        ]
        result = detect_pattern(fractures)
        assert "Repeated themes" in result or "null" in result.lower()

    def test_no_pattern(self):
        fractures = [
            FractureEvent(severity="warning", break_description="different bug A"),
            FractureEvent(severity="info", break_description="unrelated issue B"),
        ]
        result = detect_pattern(fractures)
        assert "distinct fractures" in result


class TestGenerateSuggestion:
    """Test suggestion generation."""

    def test_empty(self):
        r = ArchaeologyReport()
        assert generate_suggestion(r) == ""

    def test_high_fracture_count(self):
        r = ArchaeologyReport(fractures=[
            FractureEvent(severity="warning"),
            FractureEvent(severity="warning"),
            FractureEvent(severity="warning"),
        ])
        result = generate_suggestion(r)
        assert "splitting" in result.lower() or "High fracture" in result

    def test_multiple_critical(self):
        r = ArchaeologyReport(fractures=[
            FractureEvent(severity="critical"),
            FractureEvent(severity="critical"),
        ])
        result = generate_suggestion(r)
        assert "critical" in result.lower()

    def test_hollow_joints(self):
        r = ArchaeologyReport(fractures=[
            FractureEvent(severity="warning", status="hollow"),
        ])
        result = generate_suggestion(r)
        assert "hollow" in result.lower()

    def test_healthy_file(self):
        r = ArchaeologyReport(fractures=[
            FractureEvent(severity="info", status="solid_gold"),
        ])
        result = generate_suggestion(r)
        assert "healthy" in result.lower() or "No specific" in result


class TestFormatArchaeologyReport:
    """Test formatting of archaeology reports."""

    def test_format_empty(self):
        report = ArchaeologyReport(file="test.py")
        output = format_archaeology_report(report)
        assert "test.py" in output
        assert "intact" in output

    def test_format_with_fractures(self):
        report = ArchaeologyReport(
            file="src/payments/charge.py",
            total_months=18,
            fractures=[
                FractureEvent(
                    timestamp="2024-03-15T10:30:00+00:00",
                    bug_ref="PROJ-892",
                    severity="critical",
                    break_description="NullPointer on amount",
                    repair_description="Added amount validation",
                    status="solid_gold",
                ),
                FractureEvent(
                    timestamp="2024-11-01T10:30:00+00:00",
                    bug_ref="PROJ-1567",
                    severity="warning",
                    break_description="Float precision loss",
                    repair_description="Switched to Decimal",
                    status="hollow",
                ),
            ],
            pattern="amount handling issues",
            suggestion="Extract Amount class",
        )
        output = format_archaeology_report(report)
        assert "18 months" in output
        assert "CRACK" in output
        assert "REPAIRED" in output
        assert "SOLID GOLD" in output
        assert "HOLLOW" in output
        assert "amount handling" in output
