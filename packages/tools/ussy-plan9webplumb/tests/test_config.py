"""Tests for Plan9-WebPlumb configuration management."""

import json
import os
from pathlib import Path

import pytest

from plan9webplumb.config import Config, DEFAULT_PORT, DEFAULT_HOST
from plan9webplumb.models import Handler, HandlerRule


@pytest.fixture
def tmp_config_dir(tmp_path):
    """Create a temporary config directory."""
    config_dir = tmp_path / "plan9webplumb"
    config_dir.mkdir()
    (config_dir / "handlers").mkdir()
    (config_dir / "rules").mkdir()
    return config_dir


@pytest.fixture
def config(tmp_config_dir):
    """Create a Config instance with a temporary directory."""
    return Config(config_dir=tmp_config_dir)


class TestConfig:
    """Tests for the Config class."""

    def test_default_config_dir(self):
        c = Config()
        assert "plan9webplumb" in str(c.config_dir)

    def test_custom_config_dir(self, tmp_config_dir):
        c = Config(config_dir=tmp_config_dir)
        assert c.config_dir == tmp_config_dir

    def test_xdg_config_home(self, monkeypatch, tmp_path):
        xdg_dir = tmp_path / "xdg_config"
        xdg_dir.mkdir()
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))
        c = Config()
        assert c.config_dir == xdg_dir / "plan9webplumb"

    def test_ensure_dirs(self, tmp_path):
        config_dir = tmp_path / "new_config"
        c = Config(config_dir=config_dir)
        c.ensure_dirs()
        assert config_dir.exists()
        assert (config_dir / "handlers").exists()
        assert (config_dir / "rules").exists()

    def test_load_default_server_config(self, config):
        cfg = config.load_server_config()
        assert cfg["host"] == DEFAULT_HOST
        assert cfg["port"] == DEFAULT_PORT

    def test_save_and_load_server_config(self, config):
        custom = {"host": "0.0.0.0", "port": 9999, "log_level": "DEBUG"}
        config.save_server_config(custom)
        loaded = config.load_server_config()
        assert loaded["host"] == "0.0.0.0"
        assert loaded["port"] == 9999

    def test_host_property(self, config):
        config.load_server_config()
        assert config.host == DEFAULT_HOST

    def test_port_property(self, config):
        config.load_server_config()
        assert config.port == DEFAULT_PORT

    def test_load_handlers_empty(self, config):
        handlers = config.load_handlers()
        assert handlers == []

    def test_save_and_load_handler(self, config):
        handler = Handler(name="test", command="echo hello")
        path = config.save_handler(handler)
        assert path.exists()
        loaded = config.load_handlers()
        assert len(loaded) == 1
        assert loaded[0].name == "test"
        assert loaded[0].command == "echo hello"

    def test_get_handler(self, config):
        handler = Handler(name="myhandler", command="echo hi")
        config.save_handler(handler)
        found = config.get_handler("myhandler")
        assert found is not None
        assert found.name == "myhandler"

    def test_get_handler_not_found(self, config):
        found = config.get_handler("nonexistent")
        assert found is None

    def test_remove_handler(self, config):
        handler = Handler(name="removeme", command="echo bye")
        config.save_handler(handler)
        assert config.remove_handler("removeme") is True
        assert config.get_handler("removeme") is None

    def test_remove_handler_not_found(self, config):
        assert config.remove_handler("nope") is False

    def test_load_rules_empty(self, config):
        rules = config.load_rules()
        assert rules == []

    def test_save_and_load_rule(self, config):
        rule = HandlerRule(name="test_rule", pattern=r"test", handler="test_handler")
        path = config.save_rule(rule)
        assert path.exists()
        loaded = config.load_rules()
        assert len(loaded) == 1
        assert loaded[0].name == "test_rule"
        assert loaded[0].pattern == r"test"

    def test_remove_rule(self, config):
        rule = HandlerRule(name="rm_rule", pattern=r".*", handler="h")
        config.save_rule(rule)
        assert config.remove_rule("rm_rule") is True

    def test_remove_rule_not_found(self, config):
        assert config.remove_rule("nope") is False

    def test_load_handler_from_json(self, tmp_config_dir):
        """Test loading a handler from a JSON file."""
        handler_data = {"name": "json_handler", "command": "echo json", "action": "exec"}
        json_path = tmp_config_dir / "handlers" / "json_handler.json"
        with open(json_path, "w") as f:
            json.dump(handler_data, f)

        c = Config(config_dir=tmp_config_dir)
        handlers = c.load_handlers()
        assert len(handlers) == 1
        assert handlers[0].name == "json_handler"

    def test_load_handler_invalid_file(self, tmp_config_dir):
        """Test graceful handling of invalid handler files."""
        bad_path = tmp_config_dir / "handlers" / "bad.yaml"
        bad_path.write_text("not: a\nvalid: [handler")

        c = Config(config_dir=tmp_config_dir)
        # Should not crash, just skip
        handlers = c.load_handlers()
        # It's OK if it returns empty or partial results
        assert isinstance(handlers, list)

    def test_handlers_with_list_key(self, tmp_config_dir):
        """Test handler file with 'handlers' key containing a list."""
        import yaml
        handler_data = {
            "handlers": [
                {"name": "list_handler", "command": "echo list", "action": "exec"}
            ]
        }
        yaml_path = tmp_config_dir / "handlers" / "list_handler.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(handler_data, f)

        c = Config(config_dir=tmp_config_dir)
        handlers = c.load_handlers()
        assert len(handlers) == 1
        assert handlers[0].name == "list_handler"
