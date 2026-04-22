"""Tests for circadia.zones module."""

import pytest
from circadia.zones import CognitiveZone, ZoneProbability


class TestCognitiveZone:
    """Tests for CognitiveZone enum."""

    def test_zone_values(self):
        assert CognitiveZone.GREEN.value == "green"
        assert CognitiveZone.YELLOW.value == "yellow"
        assert CognitiveZone.RED.value == "red"
        assert CognitiveZone.CREATIVE.value == "creative"

    def test_zone_icons(self):
        assert CognitiveZone.GREEN.icon == "🟢"
        assert CognitiveZone.YELLOW.icon == "🟡"
        assert CognitiveZone.RED.icon == "🔴"
        assert CognitiveZone.CREATIVE.icon == "🎨"

    def test_zone_descriptions(self):
        assert "Peak" in CognitiveZone.GREEN.description
        assert "Moderate" in CognitiveZone.YELLOW.description
        assert "Low" in CognitiveZone.RED.description
        assert "Creative" in CognitiveZone.CREATIVE.description

    def test_linter_strictness(self):
        assert CognitiveZone.GREEN.linter_strictness == "standard"
        assert CognitiveZone.YELLOW.linter_strictness == "enhanced"
        assert CognitiveZone.RED.linter_strictness == "maximum"
        assert CognitiveZone.CREATIVE.linter_strictness == "relaxed"

    def test_deploy_allowed(self):
        assert CognitiveZone.GREEN.deploy_allowed is True
        assert CognitiveZone.YELLOW.deploy_allowed is False
        assert CognitiveZone.RED.deploy_allowed is False
        assert CognitiveZone.CREATIVE.deploy_allowed is True

    def test_risky_git_allowed(self):
        assert CognitiveZone.GREEN.risky_git_allowed is True
        assert CognitiveZone.YELLOW.risky_git_allowed is False
        assert CognitiveZone.RED.risky_git_allowed is False
        assert CognitiveZone.CREATIVE.risky_git_allowed is False

    def test_all_zones_have_icons(self):
        for zone in CognitiveZone:
            assert len(zone.icon) > 0

    def test_all_zones_have_descriptions(self):
        for zone in CognitiveZone:
            assert len(zone.description) > 0


class TestZoneProbability:
    """Tests for ZoneProbability dataclass."""

    def test_default_uniform(self):
        zp = ZoneProbability()
        assert abs(zp.green - 0.25) < 0.01
        assert abs(zp.yellow - 0.25) < 0.01
        assert abs(zp.red - 0.25) < 0.01
        assert abs(zp.creative - 0.25) < 0.01

    def test_normalization(self):
        zp = ZoneProbability(green=2.0, yellow=1.0, red=1.0, creative=0.0)
        total = zp.green + zp.yellow + zp.red + zp.creative
        assert abs(total - 1.0) < 0.01

    def test_dominant_zone(self):
        zp = ZoneProbability(green=0.7, yellow=0.1, red=0.1, creative=0.1)
        assert zp.dominant_zone == CognitiveZone.GREEN

    def test_dominant_zone_red(self):
        zp = ZoneProbability(green=0.1, yellow=0.1, red=0.7, creative=0.1)
        assert zp.dominant_zone == CognitiveZone.RED

    def test_confidence(self):
        zp = ZoneProbability(green=0.7, yellow=0.1, red=0.1, creative=0.1)
        assert abs(zp.confidence - 0.7) < 0.01

    def test_get_probability(self):
        zp = ZoneProbability(green=0.5, yellow=0.2, red=0.2, creative=0.1)
        assert abs(zp.get_probability(CognitiveZone.GREEN) - 0.5) < 0.01

    def test_zero_total_falls_back_to_uniform(self):
        zp = ZoneProbability(green=0.0, yellow=0.0, red=0.0, creative=0.0)
        assert abs(zp.green - 0.25) < 0.01

    def test_probabilities_sum_to_one(self):
        zp = ZoneProbability(green=0.6, yellow=0.2, red=0.15, creative=0.05)
        total = zp.green + zp.yellow + zp.red + zp.creative
        assert abs(total - 1.0) < 0.01
