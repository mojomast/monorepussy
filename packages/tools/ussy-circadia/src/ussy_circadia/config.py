"""Configuration management for Circadia."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CONFIG_FILENAME = ".circadia.toml"


@dataclass
class ZoneThresholds:
    """Thresholds for zone transitions based on probability."""

    green_min: float = 0.4
    yellow_min: float = 0.3
    red_min: float = 0.3
    creative_min: float = 0.3


@dataclass
class GitHooksConfig:
    """Configuration for git hook behavior per zone."""

    block_force_push_in_yellow: bool = True
    block_force_push_in_red: bool = True
    block_hard_reset_in_red: bool = True
    block_delete_branch_in_red: bool = True
    block_deploy_in_red: bool = True
    require_confirmation_in_yellow: bool = True
    require_typed_override_in_red: bool = True


@dataclass
class LinterConfig:
    """Configuration for linter strictness adaptation."""

    standard_rules: list = field(default_factory=lambda: ["E", "W", "F"])
    enhanced_rules: list = field(default_factory=lambda: ["E", "W", "F", "C", "R"])
    maximum_rules: list = field(default_factory=lambda: ["E", "W", "F", "C", "R", "B", "S"])
    relaxed_rules: list = field(default_factory=lambda: ["E", "F"])
    fatigue_error_patterns: list = field(default_factory=lambda: [
        "off-by-one",
        "wrong-comparison",
        "missing-null-check",
        "assignment-in-condition",
    ])


@dataclass
class CircadiaConfig:
    """Main configuration for Circadia."""

    utc_offset_hours: float = 0.0
    work_start_hour: float = 9.0
    work_end_hour: float = 18.0
    session_duration_limit_hours: float = 8.0
    zone_thresholds: ZoneThresholds = field(default_factory=ZoneThresholds)
    git_hooks: GitHooksConfig = field(default_factory=GitHooksConfig)
    linter: LinterConfig = field(default_factory=LinterConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CircadiaConfig":
        """Create config from a dictionary."""
        config = cls()
        if "utc_offset_hours" in data:
            config.utc_offset_hours = float(data["utc_offset_hours"])
        if "work_start_hour" in data:
            config.work_start_hour = float(data["work_start_hour"])
        if "work_end_hour" in data:
            config.work_end_hour = float(data["work_end_hour"])
        if "session_duration_limit_hours" in data:
            config.session_duration_limit_hours = float(
                data["session_duration_limit_hours"]
            )
        if "zone_thresholds" in data:
            zt = data["zone_thresholds"]
            config.zone_thresholds = ZoneThresholds(
                green_min=float(zt.get("green_min", 0.4)),
                yellow_min=float(zt.get("yellow_min", 0.3)),
                red_min=float(zt.get("red_min", 0.3)),
                creative_min=float(zt.get("creative_min", 0.3)),
            )
        if "git_hooks" in data:
            gh = data["git_hooks"]
            config.git_hooks = GitHooksConfig(
                block_force_push_in_yellow=bool(
                    gh.get("block_force_push_in_yellow", True)
                ),
                block_force_push_in_red=bool(
                    gh.get("block_force_push_in_red", True)
                ),
                block_hard_reset_in_red=bool(
                    gh.get("block_hard_reset_in_red", True)
                ),
                block_delete_branch_in_red=bool(
                    gh.get("block_delete_branch_in_red", True)
                ),
                block_deploy_in_red=bool(gh.get("block_deploy_in_red", True)),
                require_confirmation_in_yellow=bool(
                    gh.get("require_confirmation_in_yellow", True)
                ),
                require_typed_override_in_red=bool(
                    gh.get("require_typed_override_in_red", True)
                ),
            )
        if "linter" in data:
            li = data["linter"]
            config.linter = LinterConfig(
                standard_rules=li.get("standard_rules", ["E", "W", "F"]),
                enhanced_rules=li.get("enhanced_rules", ["E", "W", "F", "C", "R"]),
                maximum_rules=li.get(
                    "maximum_rules", ["E", "W", "F", "C", "R", "B", "S"]
                ),
                relaxed_rules=li.get("relaxed_rules", ["E", "F"]),
                fatigue_error_patterns=li.get(
                    "fatigue_error_patterns",
                    [
                        "off-by-one",
                        "wrong-comparison",
                        "missing-null-check",
                        "assignment-in-condition",
                    ],
                ),
            )
        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to a dictionary."""
        return asdict(self)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "CircadiaConfig":
        """Load configuration from a JSON file.

        Falls back to defaults if file doesn't exist.

        Args:
            path: Path to config file. Defaults to .circadia.toml in current dir,
                  then ~/.circadia/config.json.

        Returns:
            CircadiaConfig instance.
        """
        search_paths = []
        if path:
            search_paths.append(Path(path))
        search_paths.append(Path.cwd() / DEFAULT_CONFIG_FILENAME)
        search_paths.append(
            Path.home() / ".circadia" / "config.json"
        )

        for p in search_paths:
            if p.exists():
                try:
                    with open(p, "r") as f:
                        data = json.load(f)
                    return cls.from_dict(data)
                except (json.JSONDecodeError, OSError):
                    continue

        return cls()

    def save(self, path: Optional[str] = None) -> None:
        """Save configuration to a JSON file.

        Args:
            path: Path to config file. Defaults to .circadia.toml in current dir.
        """
        if path is None:
            path = str(Path.cwd() / DEFAULT_CONFIG_FILENAME)
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
