"""Configuration management for .seral/ directory."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from seral.models import Stage, StageTransition


DEFAULT_THRESHOLDS = {
    "age_pioneer_days": 30,
    "age_seral_early_days": 90,
    "age_seral_mid_days": 180,
    "age_seral_late_days": 365,
    "age_climax_days": 730,
    "churn_pioneer_min": 100,
    "churn_seral_early_min": 50,
    "churn_seral_mid_min": 20,
    "churn_seral_late_min": 5,
    "coverage_climax_min": 0.8,
    "contributors_climax_min": 6,
    "deletion_disturbed_threshold": 0.4,
    "contributor_spike_threshold": 2.5,
    "churn_spike_threshold": 3.0,
}


class SeralConfig:
    """Manages the .seral/ configuration directory."""

    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root)
        self.seral_dir = self.repo_root / ".seral"
        self.stages_file = self.seral_dir / "stages.json"
        self.history_file = self.seral_dir / "history.jsonl"
        self.rules_dir = self.seral_dir / "rules"
        self.config_file = self.seral_dir / "config.yaml"
        self.thresholds: dict[str, Any] = dict(DEFAULT_THRESHOLDS)

    def init(self) -> Path:
        """Create the .seral/ directory with defaults."""
        self.seral_dir.mkdir(parents=True, exist_ok=True)
        self.rules_dir.mkdir(parents=True, exist_ok=True)

        # Write default config
        if not self.config_file.exists():
            self._write_config()

        # Write default rule templates
        self._write_default_rules()

        # Initialize empty stages file
        if not self.stages_file.exists():
            self.stages_file.write_text("{}\n")

        # Initialize empty history file
        if not self.history_file.exists():
            self.history_file.write_text("")

        return self.seral_dir

    def _write_config(self) -> None:
        """Write default config.yaml."""
        config = {
            "thresholds": self.thresholds,
            "version": "1.0",
        }
        with open(self.config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

    def _write_default_rules(self) -> None:
        """Write default governance rule templates."""
        from seral.prescribe import get_builtin_rules

        for stage in [Stage.PIONEER, Stage.SERAL_EARLY, Stage.SERAL_MID,
                      Stage.SERAL_LATE, Stage.CLIMAX, Stage.DISTURBED]:
            rules = get_builtin_rules(stage)
            rule_file = self.rules_dir / f"{stage.value}.yaml"
            if not rule_file.exists():
                with open(rule_file, "w") as f:
                    yaml.dump(rules, f, default_flow_style=False)

    def load_config(self) -> dict[str, Any]:
        """Load config.yaml, merging with defaults."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                data = yaml.safe_load(f) or {}
            self.thresholds.update(data.get("thresholds", {}))
        return {"thresholds": self.thresholds}

    def save_stages(self, stages: dict[str, str]) -> None:
        """Save current stage classifications."""
        self.seral_dir.mkdir(parents=True, exist_ok=True)
        with open(self.stages_file, "w") as f:
            json.dump(stages, f, indent=2)

    def load_stages(self) -> dict[str, str]:
        """Load previously saved stage classifications."""
        if not self.stages_file.exists():
            return {}
        with open(self.stages_file) as f:
            return json.load(f)

    def append_history(self, transition: StageTransition) -> None:
        """Append a transition to the history log."""
        self.seral_dir.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, "a") as f:
            f.write(json.dumps(transition.to_dict()) + "\n")

    def load_history(self, path: Optional[str] = None) -> list[dict]:
        """Load transition history, optionally filtered by path."""
        if not self.history_file.exists():
            return []
        entries = []
        with open(self.history_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if path is None or entry.get("path") == path:
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue
        return entries

    def write_rule_file(self, stage: Stage, rules: dict) -> Path:
        """Write a governance rule file for a stage."""
        self.rules_dir.mkdir(parents=True, exist_ok=True)
        rule_file = self.rules_dir / f"{stage.value}.yaml"
        with open(rule_file, "w") as f:
            yaml.dump(rules, f, default_flow_style=False)
        return rule_file

    def load_rule_file(self, stage: Stage) -> Optional[dict]:
        """Load a governance rule file for a stage."""
        rule_file = self.rules_dir / f"{stage.value}.yaml"
        if not rule_file.exists():
            return None
        with open(rule_file) as f:
            return yaml.safe_load(f)

    def is_initialized(self) -> bool:
        """Check if .seral/ directory exists and is set up."""
        return self.seral_dir.exists() and self.config_file.exists()
