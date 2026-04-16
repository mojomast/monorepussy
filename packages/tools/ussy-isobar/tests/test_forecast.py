"""Tests for isobar.forecast module."""

import pytest

from isobar.fields import AtmosphericField, AtmosphericProfile
from isobar.forecast import (
    generate_forecast, format_forecast, Forecast, ForecastStep,
)


def _make_test_field():
    """Create a test atmospheric field with multiple profiles."""
    field = AtmosphericField()
    field.profiles["api/hot.py"] = AtmosphericProfile(
        filepath="api/hot.py", temperature=80.0, pressure=25.0,
        humidity=85.0, wind_speed=15.0, wind_direction="N",
        dew_point=30.0, bug_vorticity=2.0, barometric_tendency=0.5,
        co_change_files={"api/cold.py": 5, "utils/helpers.py": 3},
    )
    field.profiles["api/cold.py"] = AtmosphericProfile(
        filepath="api/cold.py", temperature=10.0, pressure=15.0,
        humidity=30.0, wind_speed=5.0, wind_direction="S",
        dew_point=-5.0, bug_vorticity=0.1, barometric_tendency=-0.2,
        co_change_files={"api/hot.py": 5},
    )
    field.profiles["utils/helpers.py"] = AtmosphericProfile(
        filepath="utils/helpers.py", temperature=40.0, pressure=10.0,
        humidity=50.0, wind_speed=10.0, wind_direction="E",
        dew_point=10.0, bug_vorticity=0.5, barometric_tendency=0.1,
    )
    return field


class TestGenerateForecast:
    def test_basic_forecast(self):
        field = _make_test_field()
        forecast = generate_forecast(field, num_sprints=3)
        assert len(forecast.steps) == 3

    def test_forecast_step_structure(self):
        field = _make_test_field()
        forecast = generate_forecast(field, num_sprints=2)
        step = forecast.steps[0]
        assert step.sprint_offset == 1
        assert len(step.profiles) > 0
        assert 0 < step.confidence <= 1.0

    def test_confidence_decreases(self):
        field = _make_test_field()
        forecast = generate_forecast(field, num_sprints=5)
        confidences = [s.confidence for s in forecast.steps]
        for i in range(len(confidences) - 1):
            assert confidences[i] >= confidences[i + 1]

    def test_file_filter(self):
        field = _make_test_field()
        forecast = generate_forecast(field, num_sprints=2, file_filter="api/hot.py")
        # Only the filtered file should be in the forecast
        for step in forecast.steps:
            assert "api/hot.py" in step.profiles

    def test_temperature_in_range(self):
        field = _make_test_field()
        forecast = generate_forecast(field, num_sprints=5)
        for step in forecast.steps:
            for profile in step.profiles.values():
                assert 0 <= profile.temperature <= 100

    def test_get_step(self):
        field = _make_test_field()
        forecast = generate_forecast(field, num_sprints=3)
        step = forecast.get_step(2)
        assert step is not None
        assert step.sprint_offset == 2

    def test_get_step_nonexistent(self):
        field = _make_test_field()
        forecast = generate_forecast(field, num_sprints=3)
        step = forecast.get_step(99)
        assert step is None


class TestFormatForecast:
    def test_format_basic(self):
        field = _make_test_field()
        forecast = generate_forecast(field, num_sprints=3)
        text = format_forecast(forecast)
        assert "FORECAST" in text
        assert "Sprint" in text

    def test_format_with_file_filter(self):
        field = _make_test_field()
        forecast = generate_forecast(field, num_sprints=2, file_filter="api/hot.py")
        text = format_forecast(forecast)
        assert "api/hot.py" in text


class TestForecastDataClass:
    def test_default_values(self):
        f = Forecast()
        assert f.steps == []
        assert f.file_forecast is None

    def test_generated_at(self):
        f = Forecast()
        assert f.generated_at is not None
