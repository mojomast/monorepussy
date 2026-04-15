"""Integration tests for the CLI."""

import os
import pytest
import subprocess
import sys

from pathlib import Path

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")


class TestCLIHelp:
    def test_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "endemic", "--help"],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert "endemic" in result.stdout.lower() or "epidemiological" in result.stdout.lower()

    def test_version(self):
        result = subprocess.run(
            [sys.executable, "-m", "endemic", "--version"],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert "0.1.0" in result.stdout

    def test_scan_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "endemic", "scan", "--help"],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert "path" in result.stdout.lower()

    def test_simulate_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "endemic", "simulate", "--help"],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0


class TestCLIScan:
    def test_scan_fixtures(self):
        result = subprocess.run(
            [sys.executable, "-m", "endemic", "scan", FIXTURES_DIR],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert "ENDEMIC" in result.stdout

    def test_scan_single_file(self):
        filepath = os.path.join(FIXTURES_DIR, "sample_bad.py")
        result = subprocess.run(
            [sys.executable, "-m", "endemic", "scan", filepath],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0


class TestCLISimulate:
    def test_simulate_with_r0(self):
        result = subprocess.run(
            [sys.executable, "-m", "endemic", "simulate",
             "--r0", "3.0", "--population", "50"],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert "SIR Simulation" in result.stdout

    def test_simulate_with_intervention(self):
        result = subprocess.run(
            [sys.executable, "-m", "endemic", "simulate",
             "--r0", "3.0", "--intervention-r0", "0.5", "--population", "50"],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert "WITH intervention" in result.stdout


class TestCLIHerdImmunity:
    def test_herd_immunity_basic(self):
        result = subprocess.run(
            [sys.executable, "-m", "endemic", "herd-immunity",
             "--pattern", "bare-except", "--r0", "3.2", "--population", "50"],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert "Herd Immunity" in result.stdout


class TestCLIWatch:
    def test_watch_fixtures(self):
        result = subprocess.run(
            [sys.executable, "-m", "endemic", "watch", FIXTURES_DIR],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0


class TestCLIPromote:
    def test_promote_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "endemic", "promote", "--help"],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0

    def test_promote_with_path(self):
        result = subprocess.run(
            [sys.executable, "-m", "endemic", "promote",
             "--pattern", "structured-logging", "--r0", "2.0",
             "--path", FIXTURES_DIR],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
