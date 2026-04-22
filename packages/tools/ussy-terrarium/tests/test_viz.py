"""Tests for Rich visualization layer."""

import pytest

from terrarium.viz import render_dashboard, _bar, _score_color, _status_label
from terrarium.health import HealthScore


class TestRenderDashboard:
    def test_renders_without_error(self):
        health = HealthScore(
            overall=0.75,
            fatigue=0.5,
            epidemic=1.0,
            anomaly=0.9,
            drift=0.8,
            churn=0.6,
            complexity=0.7,
            territory="core-api",
            succession="climax",
        )
        panel = render_dashboard(health)
        # Should return a Rich Panel object
        assert panel is not None

    def test_perfect_health(self):
        health = HealthScore()
        panel = render_dashboard(health)
        assert panel is not None


class TestBar:
    def test_full_bar(self):
        bar = _bar(1.0, width=10)
        assert "██████████" in bar

    def test_empty_bar(self):
        bar = _bar(0.0, width=10)
        assert "░░░░░░░░░░" in bar

    def test_half_bar(self):
        bar = _bar(0.5, width=10)
        assert "█████" in bar
        assert "░░░░░" in bar


class TestScoreColor:
    def test_green(self):
        assert _score_color(0.9) == "green"

    def test_yellow(self):
        assert _score_color(0.7) == "yellow"

    def test_red(self):
        assert _score_color(0.1) == "red"


class TestStatusLabel:
    def test_thriving(self):
        assert _status_label(0.9) == "Thriving"

    def test_critical(self):
        assert _status_label(0.1) == "Critical"
