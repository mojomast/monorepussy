"""Tests for indicator module."""
import pytest

from ussy_circadia.indicator import TerminalIndicator
from ussy_circadia.zones import CognitiveZone
from ussy_circadia.config import CircadiaConfig


@pytest.fixture
def config():
    return CircadiaConfig()


class TestTerminalIndicator:
    def test_short_indicator(self, config):
        indicator = TerminalIndicator(config=config)
        result = indicator.short_indicator()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_colored_indicator(self, config):
        indicator = TerminalIndicator(config=config)
        result = indicator.colored_indicator()
        assert isinstance(result, str)

    def test_full_indicator(self, config):
        indicator = TerminalIndicator(config=config)
        result = indicator.full_indicator()
        assert isinstance(result, str)

    def test_shell_prompt_string(self, config):
        indicator = TerminalIndicator(config=config)
        result = indicator.shell_prompt_string()
        assert isinstance(result, str)

    def test_bash_prompt_integration(self, config):
        indicator = TerminalIndicator(config=config)
        result = indicator.bash_prompt_integration()
        assert isinstance(result, str)
        assert "bash" in result.lower() or "PROMPT" in result or "PS1" in result

    def test_zsh_prompt_integration(self, config):
        indicator = TerminalIndicator(config=config)
        result = indicator.zsh_prompt_integration()
        assert isinstance(result, str)

    def test_get_zone_returns_zone(self, config):
        indicator = TerminalIndicator(config=config)
        zone = indicator.get_zone()
        assert isinstance(zone, CognitiveZone)
