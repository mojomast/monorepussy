"""Tests for circadia.config module."""

import json
import os
import tempfile
import pytest
from pathlib import Path

from circadia.config import CircadiaConfig, ZoneThresholds, GitHooksConfig, LinterConfig


class TestZoneThresholds:
    """Tests for ZoneThresholds dataclass."""

    def test_defaults(self):
        zt = ZoneThresholds()
        assert zt.green_min == 0.4
        assert zt.yellow_min == 0.3
        assert zt.red_min == 0.3
        assert zt.creative_min == 0.3


class TestGitHooksConfig:
    """Tests for GitHooksConfig dataclass."""

    def test_defaults(self):
        gh = GitHooksConfig()
        assert gh.block_force_push_in_yellow is True
        assert gh.block_force_push_in_red is True
        assert gh.block_hard_reset_in_red is True
        assert gh.block_delete_branch_in_red is True
        assert gh.block_deploy_in_red is True
        assert gh.require_confirmation_in_yellow is True
        assert gh.require_typed_override_in_red is True


class TestLinterConfig:
    """Tests for LinterConfig dataclass."""

    def test_defaults(self):
        lc = LinterConfig()
        assert "E" in lc.standard_rules
        assert "F" in lc.standard_rules
        assert len(lc.fatigue_error_patterns) > 0


class TestCircadiaConfig:
    """Tests for CircadiaConfig."""

    def test_defaults(self):
        config = CircadiaConfig()
        assert config.utc_offset_hours == 0.0
        assert config.work_start_hour == 9.0
        assert config.work_end_hour == 18.0
        assert config.session_duration_limit_hours == 8.0

    def test_from_dict(self):
        data = {
            "utc_offset_hours": -5.0,
            "work_start_hour": 8.0,
            "work_end_hour": 17.0,
        }
        config = CircadiaConfig.from_dict(data)
        assert config.utc_offset_hours == -5.0
        assert config.work_start_hour == 8.0
        assert config.work_end_hour == 17.0

    def test_from_dict_with_nested(self):
        data = {
            "utc_offset_hours": -5.0,
            "zone_thresholds": {"green_min": 0.5},
            "git_hooks": {"block_deploy_in_red": False},
        }
        config = CircadiaConfig.from_dict(data)
        assert config.zone_thresholds.green_min == 0.5
        assert config.git_hooks.block_deploy_in_red is False

    def test_to_dict(self):
        config = CircadiaConfig(utc_offset_hours=-5.0)
        d = config.to_dict()
        assert d["utc_offset_hours"] == -5.0
        assert "zone_thresholds" in d
        assert "git_hooks" in d
        assert "linter" in d

    def test_to_dict_roundtrip(self):
        config = CircadiaConfig(utc_offset_hours=-5.0, work_start_hour=8.0)
        d = config.to_dict()
        config2 = CircadiaConfig.from_dict(d)
        assert config2.utc_offset_hours == config.utc_offset_hours
        assert config2.work_start_hour == config.work_start_hour

    def test_load_nonexistent_file(self):
        config = CircadiaConfig.load(path="/nonexistent/path/config.json")
        assert config.utc_offset_hours == 0.0  # defaults

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            config = CircadiaConfig(utc_offset_hours=-5.0)
            config.save(path)
            loaded = CircadiaConfig.load(path=path)
            assert loaded.utc_offset_hours == -5.0

    def test_save_creates_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "dir", "config.json")
            config = CircadiaConfig()
            config.save(path)
            assert os.path.exists(path)

    def test_load_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            with open(path, "w") as f:
                f.write("not valid json{{{")
            config = CircadiaConfig.load(path=path)
            assert config.utc_offset_hours == 0.0  # falls back to defaults
