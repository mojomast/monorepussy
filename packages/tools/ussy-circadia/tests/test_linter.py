"""Tests for linter module."""
import pytest

from ussy_circadia.linter import LinterAdapter, LinterRuleSet
from ussy_circadia.zones import CognitiveZone
from ussy_circadia.config import CircadiaConfig


@pytest.fixture
def config():
    return CircadiaConfig()


class TestLinterRuleSet:
    def test_creation(self):
        rules = LinterRuleSet(
            rules=["E", "W", "F"],
            severity_overrides={"C": "error"},
            disabled_rules=[],
            extra_patterns=["off-by-one"],
        )
        assert "E" in rules.rules
        assert rules.severity_overrides["C"] == "error"

    def test_default_values(self):
        rules = LinterRuleSet()
        assert rules.rules == []
        assert rules.severity_overrides == {}
        assert rules.disabled_rules == []
        assert rules.extra_patterns == []


class TestLinterAdapter:
    def test_get_rules_for_green(self, config):
        adapter = LinterAdapter(config=config)
        rules = adapter.get_rules_for_zone(CognitiveZone.GREEN)
        assert isinstance(rules, LinterRuleSet)
        assert "E" in rules.rules

    def test_get_rules_for_red(self, config):
        adapter = LinterAdapter(config=config)
        rules = adapter.get_rules_for_zone(CognitiveZone.RED)
        assert isinstance(rules, LinterRuleSet)
        assert "E" in rules.rules

    def test_get_rules_for_creative(self, config):
        adapter = LinterAdapter(config=config)
        rules = adapter.get_rules_for_zone(CognitiveZone.CREATIVE)
        assert isinstance(rules, LinterRuleSet)

    def test_get_rules_for_yellow(self, config):
        adapter = LinterAdapter(config=config)
        rules = adapter.get_rules_for_zone(CognitiveZone.YELLOW)
        assert isinstance(rules, LinterRuleSet)

    def test_red_has_more_rules_than_green(self, config):
        adapter = LinterAdapter(config=config)
        red_rules = adapter.get_rules_for_zone(CognitiveZone.RED)
        green_rules = adapter.get_rules_for_zone(CognitiveZone.GREEN)
        assert len(red_rules.rules) >= len(green_rules.rules)

    def test_get_fatigue_patterns_red(self, config):
        adapter = LinterAdapter(config=config)
        patterns = adapter.get_fatigue_patterns(CognitiveZone.RED)
        assert isinstance(patterns, list)

    def test_get_fatigue_patterns_green(self, config):
        adapter = LinterAdapter(config=config)
        patterns = adapter.get_fatigue_patterns(CognitiveZone.GREEN)
        assert isinstance(patterns, list)

    def test_format_linter_config(self, config):
        adapter = LinterAdapter(config=config)
        result = adapter.format_linter_config(CognitiveZone.GREEN)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_current_rules(self, config):
        adapter = LinterAdapter(config=config)
        rules = adapter.get_current_rules()
        assert isinstance(rules, LinterRuleSet)
