"""Tests for environment variable capture and restore."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from snapshot.environment import (
    capture_environment,
    parse_env_file,
    restore_environment,
    generate_env_export_script,
    _is_secret,
    _is_relevant,
    _find_env_files,
)
from snapshot.models import EnvironmentState


class TestIsSecret:
    def test_secret_patterns(self):
        assert _is_secret("API_KEY") is True
        assert _is_secret("MY_SECRET") is True
        assert _is_secret("PASSWORD") is True
        assert _is_secret("AUTH_TOKEN") is True
        assert _is_secret("PRIVATE_KEY") is True
        assert _is_secret("AWS_CREDENTIAL") is True

    def test_non_secret(self):
        assert _is_secret("HOME") is False
        assert _is_secret("PATH") is False
        assert _is_secret("EDITOR") is False
        assert _is_secret("MY_VAR") is False


class TestIsRelevant:
    def test_relevant_vars(self):
        assert _is_relevant("PATH") is True
        assert _is_relevant("PYTHONPATH") is True
        assert _is_relevant("GOPATH") is True
        assert _is_relevant("HOME") is True
        assert _is_relevant("VIRTUAL_ENV") is True

    def test_non_relevant(self):
        assert _is_relevant("DISPLAY") is False
        assert _is_relevant("LS_COLORS") is False


class TestCaptureEnvironment:
    def test_captures_environment(self):
        env = capture_environment()
        assert isinstance(env, EnvironmentState)
        assert len(env.variables) > 0

    def test_excludes_secrets_by_default(self):
        with patch.dict(os.environ, {"MY_API_KEY": "secret123", "NORMAL_VAR": "ok"}, clear=False):
            env = capture_environment()
            assert "MY_API_KEY" not in env.variables
            assert "NORMAL_VAR" in env.variables

    def test_includes_secrets_when_requested(self):
        with patch.dict(os.environ, {"MY_API_KEY": "secret123"}, clear=False):
            env = capture_environment(include_secrets=True)
            assert "MY_API_KEY" in env.variables

    def test_captures_path(self):
        env = capture_environment()
        assert len(env.path_entries) > 0

    def test_excludes_long_values(self):
        with patch.dict(os.environ, {"SHORT": "abc", "LONG": "x" * 1100}, clear=False):
            env = capture_environment()
            assert "SHORT" in env.variables
            assert "LONG" not in env.variables


class TestFindEnvFiles:
    def test_finds_env_files(self, tmp_path):
        (tmp_path / ".env").write_text("FOO=bar\n")
        (tmp_path / ".env.local").write_text("LOCAL=test\n")
        files = _find_env_files(str(tmp_path))
        assert len(files) >= 2
        basenames = [os.path.basename(f) for f in files]
        assert ".env" in basenames
        assert ".env.local" in basenames

    def test_no_env_files(self, tmp_path):
        files = _find_env_files(str(tmp_path))
        assert files == []

    def test_nonexistent_dir(self):
        files = _find_env_files("/nonexistent/path")
        assert files == []


class TestParseEnvFile:
    def test_parse_simple(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\nBAZ=qux\n")
        result = parse_env_file(str(env_file))
        assert result["FOO"] == "bar"
        assert result["BAZ"] == "qux"

    def test_parse_with_comments(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# Comment\nFOO=bar\n# Another comment\n")
        result = parse_env_file(str(env_file))
        assert "FOO" in result
        assert len(result) == 1

    def test_parse_with_quotes(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text('FOO="hello world"\nBAR=\'single quotes\'\n')
        result = parse_env_file(str(env_file))
        assert result["FOO"] == "hello world"
        assert result["BAR"] == "single quotes"

    def test_parse_empty_lines(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("\n\nFOO=bar\n\n")
        result = parse_env_file(str(env_file))
        assert result["FOO"] == "bar"

    def test_parse_nonexistent(self):
        result = parse_env_file("/nonexistent/.env")
        assert result == {}

    def test_excludes_secrets(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\nNORMAL_VAR=ok\n")
        result = parse_env_file(str(env_file))
        assert "API_KEY" not in result
        assert "NORMAL_VAR" in result


class TestRestoreEnvironment:
    def test_restore_sets_vars(self):
        state = EnvironmentState(variables={"TEST_SNAPSHOT_VAR": "restored_value"})
        restore_environment(state)
        assert os.environ.get("TEST_SNAPSHOT_VAR") == "restored_value"
        # Cleanup
        os.environ.pop("TEST_SNAPSHOT_VAR", None)

    def test_restore_dry_run(self):
        state = EnvironmentState(variables={"TEST_VAR_DRY": "should_not_set"})
        restore_environment(state, dry_run=True)
        assert "TEST_VAR_DRY" not in os.environ


class TestGenerateEnvExportScript:
    def test_generates_script(self):
        state = EnvironmentState(variables={"HOME": "/home/user", "PATH": "/usr/bin"})
        script = generate_env_export_script(state)
        assert "#!/bin/bash" in script
        assert "export HOME=" in script
        assert "export PATH=" in script

    def test_escapes_single_quotes(self):
        state = EnvironmentState(variables={"TEST": "it's a test"})
        script = generate_env_export_script(state)
        assert "export TEST='it'\\''s a test'" in script
