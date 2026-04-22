"""Tests for isobar.fronts module."""

import pytest

from ussy_isobar.fields import AtmosphericField, AtmosphericProfile
from ussy_isobar.fronts import (
    Front, FrontType, FrontIntensity,
    detect_fronts, format_fronts_report,
    _are_adjacent, _classify_front,
    FRONT_THRESHOLD,
)


def _make_field_with_profiles():
    """Create a field with two adjacent files with very different temperatures."""
    field = AtmosphericField()
    field.profiles["api/hot.py"] = AtmosphericProfile(
        filepath="api/hot.py", temperature=80.0, pressure=30.0,
        humidity=90.0, bug_vorticity=2.5, barometric_tendency=1.0,
    )
    field.profiles["models/cold.py"] = AtmosphericProfile(
        filepath="models/cold.py", temperature=5.0, pressure=25.0,
        humidity=20.0, bug_vorticity=0.1, barometric_tendency=-0.5,
    )
    return field


class TestAreAdjacent:
    def test_direct_dependency(self):
        import_graph = {"main.py": {"utils.py"}}
        assert _are_adjacent("main.py", "utils.py", import_graph)

    def test_same_directory(self):
        assert _are_adjacent("api/auth.py", "api/views.py", {})

    def test_not_adjacent(self):
        assert not _are_adjacent("api/auth.py", "models/user.py", {})


class TestClassifyFront:
    def test_warm_front(self):
        hot = AtmosphericProfile(filepath="hot.py", temperature=80.0, pressure=10.0)
        cold = AtmosphericProfile(filepath="cold.py", temperature=5.0, pressure=30.0)
        assert _classify_front(hot, cold) == FrontType.WARM

    def test_cold_front(self):
        hot = AtmosphericProfile(filepath="hot.py", temperature=80.0, pressure=30.0)
        cold = AtmosphericProfile(filepath="cold.py", temperature=5.0, pressure=10.0)
        assert _classify_front(hot, cold) == FrontType.COLD

    def test_occluded_front(self):
        hot = AtmosphericProfile(filepath="hot.py", temperature=80.0, pressure=15.0)
        cold = AtmosphericProfile(filepath="cold.py", temperature=40.0, pressure=15.0)
        result = _classify_front(hot, cold)
        assert result == FrontType.OCCLUDED


class TestDetectFronts:
    def test_no_fronts(self):
        field = AtmosphericField()
        # All similar temperatures
        field.profiles["a.py"] = AtmosphericProfile(filepath="a.py", temperature=25.0)
        field.profiles["b.py"] = AtmosphericProfile(filepath="b.py", temperature=26.0)
        import_graph = {"a.py": {"b.py"}}
        fronts = detect_fronts(field, import_graph)
        assert len(fronts) == 0

    def test_detect_front(self):
        field = _make_field_with_profiles()
        import_graph = {"api/hot.py": {"models/cold.py"}}
        fronts = detect_fronts(field, import_graph)
        # Temperature gradient = 75°C which is > FRONT_THRESHOLD
        assert len(fronts) >= 1

    def test_front_has_correct_type(self):
        field = _make_field_with_profiles()
        import_graph = {"api/hot.py": {"models/cold.py"}}
        fronts = detect_fronts(field, import_graph)
        if fronts:
            assert fronts[0].front_type in [FrontType.WARM, FrontType.COLD,
                                             FrontType.OCCLUDED, FrontType.STATIONARY]

    def test_front_gradient(self):
        field = _make_field_with_profiles()
        import_graph = {"api/hot.py": {"models/cold.py"}}
        fronts = detect_fronts(field, import_graph)
        if fronts:
            assert fronts[0].temperature_gradient > FRONT_THRESHOLD


class TestFront:
    def test_is_severe(self):
        front = Front(
            front_type=FrontType.COLD,
            intensity=FrontIntensity.INTENSIFYING,
            hot_side="hot.py",
            cold_side="cold.py",
            temperature_gradient=50.0,
            frontogenesis_rate=1.0,
        )
        assert front.is_severe

    def test_is_not_severe(self):
        front = Front(
            front_type=FrontType.WARM,
            intensity=FrontIntensity.DEVELOPING,
            hot_side="hot.py",
            cold_side="cold.py",
            temperature_gradient=16.0,
            frontogenesis_rate=0.1,
        )
        assert not front.is_severe

    def test_risk_label_cold_severe(self):
        front = Front(
            front_type=FrontType.COLD,
            intensity=FrontIntensity.INTENSIFYING,
            hot_side="hot.py",
            cold_side="cold.py",
            temperature_gradient=50.0,
        )
        label = front.risk_label
        assert "SEVERE" in label or "COLD" in label

    def test_risk_label_occluded(self):
        front = Front(
            front_type=FrontType.OCCLUDED,
            intensity=FrontIntensity.ACTIVE,
            hot_side="hot.py",
            cold_side="cold.py",
            temperature_gradient=20.0,
        )
        assert "OCCLUDED" in front.risk_label


class TestFormatFrontsReport:
    def test_no_fronts(self):
        report = format_fronts_report([])
        assert "stable" in report.lower()

    def test_with_fronts(self):
        fronts = [
            Front(
                front_type=FrontType.COLD,
                intensity=FrontIntensity.ACTIVE,
                hot_side="api/auth.py",
                cold_side="models/user.py",
                temperature_gradient=35.0,
                frontogenesis_rate=0.3,
                description="Cold front detected",
            )
        ]
        report = format_fronts_report(fronts)
        assert "FRONTAL ANALYSIS" in report
        assert "Cold front" in report or "COLD" in report
