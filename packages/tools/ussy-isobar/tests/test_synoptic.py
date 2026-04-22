"""Tests for isobar.synoptic module."""

import pytest

from ussy_isobar.fields import AtmosphericField, AtmosphericProfile
from ussy_isobar.fronts import Front, FrontType, FrontIntensity
from ussy_isobar.cyclones import Cyclone, CycloneCategory, WarningLevel, Anticyclone
from ussy_isobar.synoptic import (
    render_synoptic_map, render_current_conditions, render_climate_report,
)


def _make_test_field():
    field = AtmosphericField()
    field.profiles["api/auth.py"] = AtmosphericProfile(
        filepath="api/auth.py", temperature=75.0, pressure=35.0,
        humidity=88.0, wind_speed=20.0, wind_direction="SE",
        dew_point=28.0, bug_vorticity=2.5, barometric_tendency=0.8,
        dependents={"views/login.py"},
        dependencies={"utils/crypto.py"},
        co_change_files={"views/login.py": 8},
    )
    field.profiles["models/user.py"] = AtmosphericProfile(
        filepath="models/user.py", temperature=8.0, pressure=28.0,
        humidity=15.0, wind_speed=3.0, wind_direction="N",
        dew_point=-10.0, bug_vorticity=0.0, barometric_tendency=-0.1,
        dependents={"api/auth.py", "views/profile.py"},
    )
    field.profiles["utils/crypto.py"] = AtmosphericProfile(
        filepath="utils/crypto.py", temperature=35.0, pressure=12.0,
        humidity=45.0, wind_speed=8.0, wind_direction="W",
        dew_point=5.0, bug_vorticity=0.3, barometric_tendency=0.2,
    )
    return field


class TestRenderSynopticMap:
    def test_basic_map(self):
        field = _make_test_field()
        output = render_synoptic_map(field)
        assert "ISOBAR" in output
        assert "Synoptic Analysis" in output

    def test_map_with_cyclones(self):
        field = _make_test_field()
        cyclones = [
            Cyclone(
                eye="api/auth.py", vorticity=2.5,
                category=CycloneCategory.CATEGORY_1,
                warning_level=WarningLevel.WARNING,
                probability=0.6,
            )
        ]
        output = render_synoptic_map(field, cyclones=cyclones)
        assert "Cyclone" in output

    def test_map_with_fronts(self):
        field = _make_test_field()
        fronts = [
            Front(
                front_type=FrontType.COLD,
                intensity=FrontIntensity.ACTIVE,
                hot_side="api/auth.py",
                cold_side="models/user.py",
                temperature_gradient=67.0,
                frontogenesis_rate=0.5,
                description="Cold front detected",
            )
        ]
        output = render_synoptic_map(field, fronts=fronts)
        assert "Cold front" in output or "COLD" in output

    def test_map_with_module_filter(self):
        field = _make_test_field()
        output = render_synoptic_map(field, module_filter="api")
        assert "ISOBAR" in output

    def test_map_with_anticyclones(self):
        field = _make_test_field()
        anticyclones = [
            Anticyclone(center="models/user.py", stability_index=250.0)
        ]
        output = render_synoptic_map(field, anticyclones=anticyclones)
        assert "Anticyclone" in output

    def test_map_storm_warnings(self):
        field = _make_test_field()
        cyclones = [
            Cyclone(
                eye="api/auth.py", vorticity=5.0,
                category=CycloneCategory.CATEGORY_5,
                warning_level=WarningLevel.CRITICAL,
                probability=0.9,
                spiral_files=["api/auth.py"],
            )
        ]
        output = render_synoptic_map(field, cyclones=cyclones)
        assert "STORM WARNING" in output


class TestRenderCurrentConditions:
    def test_basic_conditions(self):
        field = _make_test_field()
        output = render_current_conditions(field)
        assert "CURRENT CONDITIONS" in output
        assert "temperature" in output.lower()

    def test_empty_field(self):
        field = AtmosphericField()
        output = render_current_conditions(field)
        assert "No data" in output or "no data" in output.lower()

    def test_shows_hot_spots(self):
        field = _make_test_field()
        output = render_current_conditions(field)
        assert "HOT SPOTS" in output


class TestRenderClimateReport:
    def test_basic_report(self):
        profile = AtmosphericProfile(
            filepath="api/auth.py", temperature=75.0, pressure=35.0,
            humidity=88.0, wind_speed=20.0, wind_direction="SE",
            dew_point=28.0, bug_vorticity=2.5, barometric_tendency=0.8,
            dependents={"views/login.py"},
            dependencies={"utils/crypto.py"},
            co_change_files={"views/login.py": 8},
        )
        output = render_climate_report(profile)
        assert "MICRO-CLIMATE" in output
        assert "api/auth.py" in output
        assert "75.0°C" in output
        assert "CYCLONIC" in output

    def test_report_with_dependencies(self):
        profile = AtmosphericProfile(
            filepath="test.py", temperature=30.0,
            dependencies={"utils.py", "helpers.py"},
        )
        output = render_climate_report(profile)
        assert "Depends on" in output

    def test_report_with_dependents(self):
        profile = AtmosphericProfile(
            filepath="test.py", temperature=30.0,
            dependents={"main.py", "app.py"},
        )
        output = render_climate_report(profile)
        assert "Imported by" in output
