"""Tests for the CLI module."""

import subprocess
import sys
import os
import tempfile
import shutil

import pytest


class TestCLI:
    """Tests for the Dosemate CLI."""

    def test_help(self):
        """--help should work."""
        result = subprocess.run(
            [sys.executable, "-m", "dosemate", "--help"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "dosemate" in result.stdout.lower() or "pharmacokinetic" in result.stdout.lower()

    def test_version(self):
        """--version should work."""
        result = subprocess.run(
            [sys.executable, "-m", "dosemate", "--version"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "1.0.0" in result.stdout

    def test_analyze_subcommand_help(self):
        """analyze --help should work."""
        result = subprocess.run(
            [sys.executable, "-m", "dosemate", "analyze", "--help"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "repo" in result.stdout.lower()

    def test_analyze_on_repo(self, temp_repo):
        """analyze should run on a real repo."""
        result = subprocess.run(
            [sys.executable, "-m", "dosemate", "analyze", "--repo", temp_repo, "--since", "30d"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0

    def test_analyze_json(self, temp_repo):
        """analyze --json should produce valid JSON."""
        result = subprocess.run(
            [sys.executable, "-m", "dosemate", "analyze", "--repo", temp_repo, "--since", "30d", "--json"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0
        import json
        data = json.loads(result.stdout)
        assert "change_pk" in data

    def test_profile_subcommand(self, temp_repo):
        """profile should run on a real repo."""
        result = subprocess.run(
            [sys.executable, "-m", "dosemate", "profile", "--repo", temp_repo, "--since", "30d"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0

    def test_interact_subcommand(self, temp_repo):
        """interact should run on a real repo."""
        result = subprocess.run(
            [sys.executable, "-m", "dosemate", "interact", "--repo", temp_repo, "--since", "30d"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0

    def test_interact_json(self, temp_repo):
        """interact --json should produce valid JSON."""
        result = subprocess.run(
            [sys.executable, "-m", "dosemate", "interact", "--repo", temp_repo, "--since", "30d", "--json"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0
        import json
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_saturate_subcommand(self, temp_repo):
        """saturate should run on a real repo."""
        result = subprocess.run(
            [sys.executable, "-m", "dosemate", "saturate", "--repo", temp_repo, "--since", "30d"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0

    def test_saturate_json(self, temp_repo):
        """saturate --json should produce valid JSON."""
        result = subprocess.run(
            [sys.executable, "-m", "dosemate", "saturate", "--repo", temp_repo, "--since", "30d", "--json"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0
        import json
        data = json.loads(result.stdout)
        assert "Vmax_prs_per_day" in data

    def test_steady_state_subcommand(self, temp_repo):
        """steady-state should run on a real repo."""
        result = subprocess.run(
            [sys.executable, "-m", "dosemate", "steady-state", "--repo", temp_repo, "--since", "90d"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0

    def test_no_command_shows_help(self):
        """No command should show help."""
        result = subprocess.run(
            [sys.executable, "-m", "dosemate"],
            capture_output=True, text=True, timeout=30,
        )
        # Should exit with code 1 and show help
        assert result.returncode == 1
