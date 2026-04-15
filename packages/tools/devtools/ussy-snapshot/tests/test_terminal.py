"""Tests for terminal state capture and restore."""

import os
from unittest.mock import patch, MagicMock

from snapshot.terminal import (
    capture_terminals,
    _capture_current_terminal,
    _get_relevant_env_vars,
    _get_shell_history,
    restore_terminal,
)
from snapshot.models import TerminalState


class TestCaptureTerminals:
    def test_captures_current_terminal(self):
        """Should always capture at least the current terminal."""
        terminals = capture_terminals()
        assert len(terminals) >= 1
        assert terminals[0].session_id == "current"

    def test_current_terminal_has_cwd(self):
        """Current terminal should have a working directory."""
        terminals = capture_terminals()
        assert terminals[0].working_directory != ""


class TestCaptureCurrentTerminal:
    def test_returns_terminal_state(self):
        terminal = _capture_current_terminal()
        assert terminal is not None
        assert isinstance(terminal, TerminalState)
        assert terminal.session_id == "current"
        assert terminal.working_directory == os.getcwd()


class TestGetRelevantEnvVars:
    def test_excludes_secrets(self):
        """Should exclude variables that look like secrets."""
        with patch.dict(os.environ, {
            "MY_API_KEY": "secret123",
            "MY_PASSWORD": "hunter2",
            "AUTH_TOKEN": "tok123",
            "NORMAL_VAR": "normal_value",
        }, clear=False):
            env = _get_relevant_env_vars()
            assert "MY_API_KEY" not in env
            assert "MY_PASSWORD" not in env
            assert "AUTH_TOKEN" not in env
            assert "NORMAL_VAR" in env

    def test_excludes_long_values(self):
        """Should exclude variables with very long values."""
        with patch.dict(os.environ, {
            "SHORT": "abc",
            "LONG": "x" * 600,
        }, clear=False):
            env = _get_relevant_env_vars()
            assert "SHORT" in env
            assert "LONG" not in env


class TestGetShellHistory:
    def test_returns_list(self):
        history = _get_shell_history()
        assert isinstance(history, list)

    def test_history_limited(self):
        """History should be limited to 50 entries."""
        history = _get_shell_history()
        assert len(history) <= 50


class TestRestoreTerminal:
    def test_restore_current_terminal(self):
        state = TerminalState(
            session_id="current",
            working_directory=os.getcwd(),
        )
        result = restore_terminal(state)
        assert result is True

    def test_restore_dry_run(self):
        state = TerminalState(
            session_id="current",
            working_directory="/nonexistent/path",
        )
        result = restore_terminal(state, dry_run=True)
        assert result is True
