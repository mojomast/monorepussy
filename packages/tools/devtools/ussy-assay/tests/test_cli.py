"""Tests for the CLI module."""

import subprocess
import sys
from pathlib import Path

import pytest

from assay.cli import main, build_parser


class TestBuildParser:
    def test_parser_creation(self):
        parser = build_parser()
        assert parser is not None

    def test_grade_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["grade", "src/"])
        assert args.command == "grade"
        assert args.path == "src/"

    def test_compose_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["compose", "src/"])
        assert args.command == "compose"

    def test_alloy_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["alloy", "src/"])
        assert args.command == "alloy"

    def test_crucible_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["crucible", "src/"])
        assert args.command == "crucible"

    def test_slag_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["slag", "src/"])
        assert args.command == "slag"

    def test_watch_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["watch", "src/", "--interval", "3"])
        assert args.command == "watch"
        assert args.interval == 3

    def test_no_subcommand(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.command is None


class TestMainFunction:
    def test_no_args_shows_help(self, capsys):
        """When called with no subcommand, should print help and not crash."""
        main([])
        captured = capsys.readouterr()
        assert "assay" in captured.out.lower() or "usage" in captured.out.lower()

    def test_grade_on_fixtures(self, capsys, fixtures_dir):
        main(["grade", str(fixtures_dir)])
        captured = capsys.readouterr()
        assert "ASSAY REPORT" in captured.out

    def test_compose_on_file(self, capsys, business_file):
        main(["compose", str(business_file)])
        captured = capsys.readouterr()
        assert "Elemental Composition" in captured.out

    def test_alloy_on_fixtures(self, capsys, fixtures_dir):
        main(["alloy", str(fixtures_dir)])
        captured = capsys.readouterr()
        # Should have either alloyed or pure section
        assert "MIXED CONCERNS" in captured.out or "PURE FUNCTIONS" in captured.out

    def test_crucible_on_fixtures(self, capsys, fixtures_dir):
        main(["crucible", str(fixtures_dir)])
        captured = capsys.readouterr()
        assert "MOST VALUABLE" in captured.out

    def test_slag_on_fixtures(self, capsys, fixtures_dir):
        main(["slag", str(fixtures_dir)])
        captured = capsys.readouterr()
        # Should detect slag in the fixtures
        assert "SLAG INVENTORY" in captured.out or "No slag" in captured.out

    def test_grade_on_empty_dir(self, capsys, tmp_path):
        main(["grade", str(tmp_path)])
        captured = capsys.readouterr()
        assert "No Python files" in captured.out


class TestCLIEntryPoint:
    def test_version(self):
        result = subprocess.run(
            [sys.executable, "-m", "assay", "--version"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "0.1.0" in result.stdout
