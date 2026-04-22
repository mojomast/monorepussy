"""Configuration management for Plan9-WebPlumb."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

from ussy_plan9webplumb.models import Handler, HandlerRule


DEFAULT_CONFIG_DIR = Path.home() / ".config" / "plan9webplumb"
DEFAULT_PORT = 31151
DEFAULT_HOST = "localhost"


def _yaml_dump(data: Any, stream: Any = None) -> str:
    """Dump data as YAML, falling back to JSON if PyYAML is not available."""
    if yaml is not None:
        return yaml.dump(data, stream=stream, default_flow_style=False, sort_keys=False) or ""
    return json.dumps(data, indent=2)


def _yaml_load(stream: Any) -> Any:
    """Load YAML data, falling back to JSON if PyYAML is not available."""
    if yaml is not None:
        return yaml.safe_load(stream)
    return json.loads(stream)


class Config:
    """Configuration manager for the plumber.

    Manages handler rules, handler definitions, and server settings.
    Config is stored in ~/.config/plan9webplumb/ by default.
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self.config_dir = config_dir or self._default_config_dir()
        self.handlers_dir = self.config_dir / "handlers"
        self.rules_dir = self.config_dir / "rules"
        self._server_config: dict[str, Any] = {}

    @staticmethod
    def _default_config_dir() -> Path:
        """Get the default config directory, respecting XDG_CONFIG_HOME."""
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            return Path(xdg) / "plan9webplumb"
        return DEFAULT_CONFIG_DIR

    def ensure_dirs(self) -> None:
        """Create configuration directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.handlers_dir.mkdir(parents=True, exist_ok=True)
        self.rules_dir.mkdir(parents=True, exist_ok=True)

    def load_server_config(self) -> dict[str, Any]:
        """Load server configuration from config file."""
        config_file = self.config_dir / "config.yaml"
        if config_file.exists():
            with open(config_file) as f:
                data = _yaml_load(f)
                if isinstance(data, dict):
                    self._server_config = data
                    return data
        self._server_config = self._default_server_config()
        return self._server_config

    def save_server_config(self, config: dict[str, Any]) -> None:
        """Save server configuration to config file."""
        self.ensure_dirs()
        config_file = self.config_dir / "config.yaml"
        with open(config_file, "w") as f:
            _yaml_dump(config, stream=f)
        self._server_config = config

    def _default_server_config(self) -> dict[str, Any]:
        """Return default server configuration."""
        return {
            "host": DEFAULT_HOST,
            "port": DEFAULT_PORT,
            "log_level": "INFO",
        }

    @property
    def host(self) -> str:
        """Get the configured host."""
        if not self._server_config:
            self.load_server_config()
        return self._server_config.get("host", DEFAULT_HOST)

    @property
    def port(self) -> int:
        """Get the configured port."""
        if not self._server_config:
            self.load_server_config()
        return self._server_config.get("port", DEFAULT_PORT)

    # ---- Handlers ----

    def load_handlers(self) -> list[Handler]:
        """Load all handler definitions from the handlers config directory."""
        self.ensure_dirs()
        handlers: list[Handler] = []
        if not self.handlers_dir.exists():
            return handlers
        for path in sorted(self.handlers_dir.glob("*.yaml")):
            handler = self._load_handler_file(path)
            if handler:
                handlers.append(handler)
        for path in sorted(self.handlers_dir.glob("*.json")):
            handler = self._load_handler_file(path)
            if handler:
                handlers.append(handler)
        return handlers

    def _load_handler_file(self, path: Path) -> Optional[Handler]:
        """Load a single handler definition from a file."""
        try:
            with open(path) as f:
                data = _yaml_load(f)
            if not isinstance(data, dict):
                return None
            # Support both single handler and list of handlers in a file
            if "handlers" in data:
                items = data["handlers"]
                if items:
                    return Handler.from_dict(items[0] if isinstance(items, list) else items)
            return Handler.from_dict(data)
        except (OSError, ValueError, TypeError, yaml.parser.ParserError, yaml.scanner.ScannerError, yaml.YAMLError):
            return None

    def get_handler(self, name: str) -> Optional[Handler]:
        """Find a handler by name."""
        for handler in self.load_handlers():
            if handler.name == name:
                return handler
        return None

    def save_handler(self, handler: Handler) -> Path:
        """Save a handler definition to a file."""
        self.ensure_dirs()
        path = self.handlers_dir / f"{handler.name}.yaml"
        with open(path, "w") as f:
            _yaml_dump(handler.to_dict(), stream=f)
        return path

    def remove_handler(self, name: str) -> bool:
        """Remove a handler definition file."""
        for ext in (".yaml", ".json"):
            path = self.handlers_dir / f"{name}{ext}"
            if path.exists():
                path.unlink()
                return True
        return False

    # ---- Rules ----

    def load_rules(self) -> list[HandlerRule]:
        """Load all handler rules from the rules config directory."""
        self.ensure_dirs()
        rules: list[HandlerRule] = []
        if not self.rules_dir.exists():
            return rules
        for path in sorted(self.rules_dir.glob("*.yaml")):
            rule = self._load_rule_file(path)
            if rule:
                rules.append(rule)
        for path in sorted(self.rules_dir.glob("*.json")):
            rule = self._load_rule_file(path)
            if rule:
                rules.append(rule)
        return rules

    def _load_rule_file(self, path: Path) -> Optional[HandlerRule]:
        """Load a single rule from a file."""
        try:
            with open(path) as f:
                data = _yaml_load(f)
            if not isinstance(data, dict):
                return None
            return HandlerRule.from_dict(data)
        except (OSError, ValueError, TypeError):
            return None

    def save_rule(self, rule: HandlerRule) -> Path:
        """Save a rule to a file."""
        self.ensure_dirs()
        path = self.rules_dir / f"{rule.name}.yaml"
        with open(path, "w") as f:
            _yaml_dump(rule.to_dict(), stream=f)
        return path

    def remove_rule(self, name: str) -> bool:
        """Remove a rule file."""
        for ext in (".yaml", ".json"):
            path = self.rules_dir / f"{name}{ext}"
            if path.exists():
                path.unlink()
                return True
        return False
