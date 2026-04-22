"""Tests for CLI module."""
import subprocess
import sys

import pytest


class TestCLI:
    def test_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "circadia", "--help"],
            capture_output=True, text=True, cwd="/home/mojo/builds/circadia"
        )
        assert result.returncode == 0
        assert "circadia" in result.stdout.lower() or "Circadia" in result.stdout

    def test_version(self):
        result = subprocess.run(
            [sys.executable, "-m", "circadia", "--version"],
            capture_output=True, text=True, cwd="/home/mojo/builds/circadia"
        )
        assert result.returncode == 0

    def test_status_command(self):
        result = subprocess.run(
            [sys.executable, "-m", "circadia", "status"],
            capture_output=True, text=True, cwd="/home/mojo/builds/circadia"
        )
        assert result.returncode == 0
        # Should show a zone indicator
        output = result.stdout
        assert any(z in output.lower() for z in ["green", "yellow", "red", "creative"])

    def test_config_show(self):
        result = subprocess.run(
            [sys.executable, "-m", "circadia", "config", "--show"],
            capture_output=True, text=True, cwd="/home/mojo/builds/circadia"
        )
        assert result.returncode == 0

    def test_linter_command(self):
        result = subprocess.run(
            [sys.executable, "-m", "circadia", "linter"],
            capture_output=True, text=True, cwd="/home/mojo/builds/circadia"
        )
        assert result.returncode == 0

    def test_hooks_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "circadia", "hooks", "--help"],
            capture_output=True, text=True, cwd="/home/mojo/builds/circadia"
        )
        assert result.returncode == 0

    def test_session_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "circadia", "session", "--help"],
            capture_output=True, text=True, cwd="/home/mojo/builds/circadia"
        )
        assert result.returncode == 0

    def test_unknown_command(self):
        result = subprocess.run(
            [sys.executable, "-m", "circadia", "nonexistent"],
            capture_output=True, text=True, cwd="/home/mojo/builds/circadia"
        )
        assert result.returncode != 0
