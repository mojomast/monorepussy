"""Tests for config module."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ussy_seral.config import SeralConfig, DEFAULT_THRESHOLDS
from ussy_seral.models import Stage, StageTransition


class TestSeralConfig:
    """Tests for SeralConfig."""

    def test_init_creates_directory(self, tmp_path: Path):
        config = SeralConfig(tmp_path)
        seral_dir = config.init()
        assert seral_dir.exists()
        assert (seral_dir / "config.yaml").exists()
        assert (seral_dir / "stages.json").exists()
        assert (seral_dir / "history.jsonl").exists()
        assert (seral_dir / "rules").exists()

    def test_init_creates_rule_files(self, tmp_path: Path):
        config = SeralConfig(tmp_path)
        config.init()
        assert (tmp_path / ".seral" / "rules" / "pioneer.yaml").exists()
        assert (tmp_path / ".seral" / "rules" / "climax.yaml").exists()
        assert (tmp_path / ".seral" / "rules" / "disturbed.yaml").exists()

    def test_load_config(self, tmp_path: Path):
        config = SeralConfig(tmp_path)
        config.init()
        data = config.load_config()
        assert "thresholds" in data

    def test_default_thresholds(self, tmp_path: Path):
        config = SeralConfig(tmp_path)
        config.init()
        data = config.load_config()
        assert data["thresholds"]["deletion_disturbed_threshold"] == 0.4
        assert data["thresholds"]["contributor_spike_threshold"] == 2.5

    def test_save_and_load_stages(self, tmp_path: Path):
        config = SeralConfig(tmp_path)
        config.init()
        stages = {"src/auth": "climax", "src/new": "pioneer"}
        config.save_stages(stages)
        loaded = config.load_stages()
        assert loaded == stages

    def test_load_stages_empty(self, tmp_path: Path):
        config = SeralConfig(tmp_path)
        config.init()
        loaded = config.load_stages()
        assert loaded == {}

    def test_append_and_load_history(self, tmp_path: Path):
        config = SeralConfig(tmp_path)
        config.init()
        transition = StageTransition(
            path="src/test",
            from_stage=Stage.PIONEER,
            to_stage=Stage.SERAL_MID,
            timestamp=datetime.now(timezone.utc),
            reason="Growing module",
        )
        config.append_history(transition)
        history = config.load_history()
        assert len(history) == 1
        assert history[0]["path"] == "src/test"
        assert history[0]["from_stage"] == "pioneer"

    def test_load_history_filtered(self, tmp_path: Path):
        config = SeralConfig(tmp_path)
        config.init()
        t1 = StageTransition(
            path="src/a",
            from_stage=Stage.PIONEER,
            to_stage=Stage.SERAL_MID,
        )
        t2 = StageTransition(
            path="src/b",
            from_stage=Stage.SERAL_MID,
            to_stage=Stage.CLIMAX,
        )
        config.append_history(t1)
        config.append_history(t2)

        history_a = config.load_history(path="src/a")
        assert len(history_a) == 1
        assert history_a[0]["path"] == "src/a"

    def test_is_initialized(self, tmp_path: Path):
        config = SeralConfig(tmp_path)
        assert config.is_initialized() is False
        config.init()
        assert config.is_initialized() is True

    def test_write_and_load_rule_file(self, tmp_path: Path):
        config = SeralConfig(tmp_path)
        config.init()
        rules = {"mandatory": ["Rule 1"], "recommended": ["Rule 2"]}
        config.write_rule_file(Stage.PIONEER, rules)
        loaded = config.load_rule_file(Stage.PIONEER)
        assert loaded is not None
        assert loaded["mandatory"] == ["Rule 1"]

    def test_load_rule_file_nonexistent(self, tmp_path: Path):
        config = SeralConfig(tmp_path)
        loaded = config.load_rule_file(Stage.CLIMAX)
        assert loaded is None

    def test_init_idempotent(self, tmp_path: Path):
        config = SeralConfig(tmp_path)
        config.init()
        config.init()  # Should not raise
        assert config.is_initialized()
