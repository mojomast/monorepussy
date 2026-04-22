"""Tests for isobar.cyclones module."""

import pytest

from isobar.fields import AtmosphericField, AtmosphericProfile
from isobar.cyclones import (
    Cyclone, Anticyclone, CycloneCategory, WarningLevel,
    classify_cyclone, determine_warning_level,
    detect_cyclones, detect_anticyclones,
    generate_storm_warnings,
)


class TestClassifyCyclone:
    def test_tropical_depression(self):
        assert classify_cyclone(1.2) == CycloneCategory.TROPICAL_DEPRESSION

    def test_tropical_storm(self):
        assert classify_cyclone(1.7) == CycloneCategory.TROPICAL_STORM

    def test_category_1(self):
        assert classify_cyclone(2.2) == CycloneCategory.CATEGORY_1

    def test_category_2(self):
        assert classify_cyclone(2.7) == CycloneCategory.CATEGORY_2

    def test_category_3(self):
        assert classify_cyclone(3.5) == CycloneCategory.CATEGORY_3

    def test_category_4(self):
        assert classify_cyclone(4.5) == CycloneCategory.CATEGORY_4

    def test_category_5(self):
        assert classify_cyclone(6.0) == CycloneCategory.CATEGORY_5


class TestCyclone:
    def test_category_label(self):
        c = Cyclone(eye="test.py", vorticity=3.0, category=CycloneCategory.CATEGORY_3)
        assert "Category 3" in c.category_label

    def test_symbol_extreme(self):
        c = Cyclone(eye="test.py", vorticity=6.0, category=CycloneCategory.CATEGORY_5)
        assert c.symbol == "⛈"

    def test_symbol_tropical_storm(self):
        c = Cyclone(eye="test.py", vorticity=1.8, category=CycloneCategory.TROPICAL_STORM)
        assert c.symbol == "🌀"


class TestDetermineWarningLevel:
    def test_critical(self):
        c = Cyclone(eye="test.py", vorticity=5.0, category=CycloneCategory.CATEGORY_5)
        p = AtmosphericProfile(filepath="test.py", temperature=90.0)
        assert determine_warning_level(c, p) == WarningLevel.CRITICAL

    def test_severe(self):
        c = Cyclone(eye="test.py", vorticity=3.5, category=CycloneCategory.CATEGORY_3)
        p = AtmosphericProfile(filepath="test.py", temperature=50.0)
        assert determine_warning_level(c, p) == WarningLevel.SEVERE

    def test_warning(self):
        c = Cyclone(eye="test.py", vorticity=2.2, category=CycloneCategory.CATEGORY_1)
        p = AtmosphericProfile(filepath="test.py", temperature=50.0)
        assert determine_warning_level(c, p) == WarningLevel.WARNING

    def test_watch(self):
        c = Cyclone(eye="test.py", vorticity=1.2,
                     category=CycloneCategory.TROPICAL_DEPRESSION)
        p = AtmosphericProfile(filepath="test.py", temperature=20.0)
        assert determine_warning_level(c, p) == WarningLevel.WATCH


class TestDetectCyclones:
    def test_no_cyclones(self):
        field = AtmosphericField()
        field.profiles["stable.py"] = AtmosphericProfile(
            filepath="stable.py", temperature=10.0, bug_vorticity=0.1
        )
        cyclones = detect_cyclones(field)
        assert len(cyclones) == 0

    def test_detect_cyclone(self):
        field = AtmosphericField()
        field.profiles["hot.py"] = AtmosphericProfile(
            filepath="hot.py", temperature=80.0, bug_vorticity=3.0,
            dependents={"dep1.py"},
        )
        field.profiles["dep1.py"] = AtmosphericProfile(
            filepath="dep1.py", temperature=60.0, bug_vorticity=1.5,
        )
        cyclones = detect_cyclones(field)
        assert len(cyclones) >= 1
        assert cyclones[0].eye == "hot.py"

    def test_cyclones_sorted_by_vorticity(self):
        field = AtmosphericField()
        field.profiles["a.py"] = AtmosphericProfile(
            filepath="a.py", temperature=80.0, bug_vorticity=4.0,
        )
        field.profiles["b.py"] = AtmosphericProfile(
            filepath="b.py", temperature=70.0, bug_vorticity=2.0,
        )
        cyclones = detect_cyclones(field)
        if len(cyclones) >= 2:
            assert abs(cyclones[0].vorticity) >= abs(cyclones[1].vorticity)


class TestDetectAnticyclones:
    def test_no_anticyclones(self):
        field = AtmosphericField()
        field.profiles["hot.py"] = AtmosphericProfile(
            filepath="hot.py", temperature=80.0, pressure=30.0, humidity=80.0,
        )
        anticyclones = detect_anticyclones(field)
        assert len(anticyclones) == 0

    def test_detect_anticyclone(self):
        field = AtmosphericField()
        field.profiles["stable.py"] = AtmosphericProfile(
            filepath="stable.py", temperature=5.0, pressure=30.0, humidity=20.0,
            dependents={"dep1.py"},
        )
        field.profiles["dep1.py"] = AtmosphericProfile(
            filepath="dep1.py", temperature=10.0,
        )
        anticyclones = detect_anticyclones(field)
        assert len(anticyclones) >= 1


class TestGenerateStormWarnings:
    def test_no_warnings(self):
        warnings = generate_storm_warnings([])
        assert len(warnings) == 0

    def test_critical_warning(self):
        cyclones = [
            Cyclone(
                eye="test.py", vorticity=5.0,
                category=CycloneCategory.CATEGORY_5,
                warning_level=WarningLevel.CRITICAL,
                probability=0.9,
                spiral_files=["test.py", "dep1.py"],
            )
        ]
        warnings = generate_storm_warnings(cyclones, threshold="critical")
        assert len(warnings) == 1
        assert "CRITICAL" in warnings[0]

    def test_threshold_filtering(self):
        cyclones = [
            Cyclone(
                eye="test.py", vorticity=1.2,
                category=CycloneCategory.TROPICAL_DEPRESSION,
                warning_level=WarningLevel.WATCH,
            )
        ]
        # Severe threshold should filter out watch-level
        warnings = generate_storm_warnings(cyclones, threshold="severe")
        assert len(warnings) == 0

    def test_all_warnings_with_watch(self):
        cyclones = [
            Cyclone(
                eye="test.py", vorticity=1.2,
                category=CycloneCategory.TROPICAL_DEPRESSION,
                warning_level=WarningLevel.WATCH,
            )
        ]
        warnings = generate_storm_warnings(cyclones, threshold="watch")
        assert len(warnings) == 1
