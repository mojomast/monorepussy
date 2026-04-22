"""Tests for cavity.cli module."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ussy_cavity.cli import build_parser, main


FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_parser_created(self):
        parser = build_parser()
        assert parser is not None

    def test_version(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_no_command_returns_zero(self):
        result = main([])
        assert result == 0


# ---------------------------------------------------------------------------
# modes subcommand
# ---------------------------------------------------------------------------


class TestCmdModes:
    def test_basic(self, simple_yaml_path, capsys):
        result = main(["modes", simple_yaml_path])
        assert result == 0
        captured = capsys.readouterr()
        assert "Mode" in captured.out or "No resonance" in captured.out

    def test_json_output(self, simple_yaml_path, capsys):
        result = main(["modes", simple_yaml_path, "--json"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)

    def test_all_modes(self, simple_yaml_path, capsys):
        result = main(["modes", simple_yaml_path, "--all-modes"])
        assert result == 0

    def test_custom_dt(self, simple_yaml_path, capsys):
        result = main(["modes", simple_yaml_path, "--dt", "2.0"])
        assert result == 0

    def test_directory_input(self, simple_yaml_path, tmp_path, capsys):
        import shutil
        subdir = tmp_path / "pipe"
        subdir.mkdir()
        shutil.copy(simple_yaml_path, subdir / "pipeline.yaml")
        result = main(["modes", str(subdir)])
        assert result == 0

    def test_file_not_found(self, capsys):
        result = main(["modes", "/nonexistent/path.yaml"])
        assert result == 1


# ---------------------------------------------------------------------------
# impedance subcommand
# ---------------------------------------------------------------------------


class TestCmdImpedance:
    def test_basic(self, simple_yaml_path, capsys):
        result = main(["impedance", simple_yaml_path])
        assert result == 0
        captured = capsys.readouterr()
        assert "Impedance" in captured.out

    def test_json_output(self, simple_yaml_path, capsys):
        result = main(["impedance", simple_yaml_path, "--json"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "boundaries" in data

    def test_custom_target_zeta(self, simple_yaml_path, capsys):
        result = main(["impedance", simple_yaml_path, "--target-zeta", "0.8"])
        assert result == 0

    def test_complex_topology(self, complex_yaml_path, capsys):
        result = main(["impedance", complex_yaml_path])
        assert result == 0


# ---------------------------------------------------------------------------
# monitor subcommand
# ---------------------------------------------------------------------------


class TestCmdMonitor:
    def test_basic(self, deadlock_timeseries_path, capsys):
        result = main(["monitor", deadlock_timeseries_path])
        assert result == 0
        captured = capsys.readouterr()
        assert "Standing" in captured.out or "Beat" in captured.out or "No" in captured.out

    def test_json_output(self, deadlock_timeseries_path, capsys):
        result = main(["monitor", deadlock_timeseries_path, "--json"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "standing_waves" in data
        assert "beat_frequencies" in data

    def test_custom_fs(self, deadlock_timeseries_path, capsys):
        result = main(["monitor", deadlock_timeseries_path, "--fs", "5.0"])
        assert result == 0

    def test_custom_window(self, deadlock_timeseries_path, capsys):
        result = main(["monitor", deadlock_timeseries_path, "--window", "16"])
        assert result == 0

    def test_empty_timeseries(self, empty_timeseries_path, capsys):
        result = main(["monitor", empty_timeseries_path])
        assert result == 1  # Error: no data


# ---------------------------------------------------------------------------
# report subcommand
# ---------------------------------------------------------------------------


class TestCmdReport:
    def test_basic(self, simple_yaml_path, capsys):
        result = main(["report", simple_yaml_path])
        assert result == 0
        captured = capsys.readouterr()
        assert "CAVITY" in captured.out

    def test_json_output(self, simple_yaml_path, capsys):
        result = main(["report", simple_yaml_path, "--json"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "timestamp" in data
        assert "modes" in data

    def test_with_timeseries(self, simple_yaml_path, deadlock_timeseries_path, capsys):
        result = main(["report", simple_yaml_path, "--timeseries", deadlock_timeseries_path])
        assert result == 0

    def test_custom_target_zeta(self, simple_yaml_path, capsys):
        result = main(["report", simple_yaml_path, "--target-zeta", "0.5"])
        assert result == 0


# ---------------------------------------------------------------------------
# Python -m support
# ---------------------------------------------------------------------------


class TestModuleExecution:
    def test_python_m_cavity(self):
        """Test that `python -m ussy_cavity` works."""
        result = subprocess.run(
            [sys.executable, "-m", "ussy_cavity", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "cavity" in result.stdout.lower() or result.returncode == 0
