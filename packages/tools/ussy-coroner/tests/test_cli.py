"""Tests for coroner.cli — Command Line Interface."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ussy_coroner.cli import build_parser, main


FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_RUN_JSON = FIXTURES_DIR / "sample_run" / "run.json"


class TestBuildParser:
    """Tests for argument parser construction."""

    def test_parser_creation(self):
        parser = build_parser()
        assert parser is not None

    def test_version_flag(self):
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0


class TestCLISubcommands:
    """Tests for CLI subcommands."""

    def test_traces_command(self, capsys):
        main(["traces", str(SAMPLE_RUN_JSON)])
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_spatter_command(self, capsys):
        main(["spatter", str(SAMPLE_RUN_JSON)])
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_luminol_command(self, capsys):
        main(["luminol", str(SAMPLE_RUN_JSON)])
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_custody_command(self, capsys):
        main(["custody", str(SAMPLE_RUN_JSON)])
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_striation_command_no_compare(self, capsys):
        main(["striation", str(SAMPLE_RUN_JSON)])
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_investigate_command(self, capsys):
        main(["investigate", str(SAMPLE_RUN_JSON)])
        captured = capsys.readouterr()
        assert "AUTOPSY REPORT" in captured.out

    def test_report_command(self, capsys):
        main(["report", str(SAMPLE_RUN_JSON)])
        captured = capsys.readouterr()
        assert "AUTOPSY REPORT" in captured.out

    def test_no_command_shows_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 1

    def test_traces_with_bidirectional(self, capsys):
        main(["traces", str(SAMPLE_RUN_JSON), "--bidirectional"])
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_investigate_with_directory(self, capsys):
        main(["investigate", str(FIXTURES_DIR / "sample_run")])
        captured = capsys.readouterr()
        assert "AUTOPSY REPORT" in captured.out


class TestCLIDBIntegration:
    """Tests for CLI with database integration."""

    def test_custody_with_compare(self, capsys):
        """Test custody comparison between two JSON runs."""
        build_38_json = FIXTURES_DIR / "build_38.json"
        main(["custody", str(SAMPLE_RUN_JSON), "--compare", str(build_38_json)])
        captured = capsys.readouterr()
        assert "Chain of Custody" in captured.out
