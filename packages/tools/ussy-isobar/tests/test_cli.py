"""Tests for isobar.cli module."""

import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

import pytest

from isobar.cli import build_parser, main


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository with sample commits."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    subprocess.run(["git", "init"], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"],
                   cwd=str(repo), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"],
                   cwd=str(repo), capture_output=True, check=True)

    (repo / "main.py").write_text("import auth\nprint('hello')")
    (repo / "auth.py").write_text("def login(): pass")

    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"],
                   cwd=str(repo), capture_output=True, check=True)

    (repo / "auth.py").write_text("def login(): pass\ndef logout(): pass")
    subprocess.run(["git", "add", "auth.py"], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "fix: add logout"],
                   cwd=str(repo), capture_output=True, check=True)

    return repo


class TestBuildParser:
    def test_parser_creation(self):
        parser = build_parser()
        assert parser is not None

    def test_version_flag(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    def test_path_default(self):
        parser = build_parser()
        args = parser.parse_args(["survey"])
        assert args.path == "."

    def test_path_explicit(self):
        parser = build_parser()
        args = parser.parse_args(["survey", "--path", "/tmp/repo", "--max-commits", "100"])
        assert args.command == "survey"
        assert args.path == "/tmp/repo"
        assert args.max_commits == 100

    def test_map_command(self):
        parser = build_parser()
        args = parser.parse_args(["map", "--path", "."])
        assert args.command == "map"

    def test_map_json_format(self):
        parser = build_parser()
        args = parser.parse_args(["map", "--path", ".", "--format", "json"])
        assert args.format == "json"

    def test_forecast_command(self):
        parser = build_parser()
        args = parser.parse_args(["forecast", "--path", ".", "--ahead", "3"])
        assert args.command == "forecast"
        assert args.ahead == 3

    def test_warn_threshold(self):
        parser = build_parser()
        args = parser.parse_args(["warn", "--path", ".", "--threshold", "severe"])
        assert args.threshold == "severe"

    def test_fronts_command(self):
        parser = build_parser()
        args = parser.parse_args(["fronts", "--path", "."])
        assert args.command == "fronts"

    def test_climate_command(self):
        parser = build_parser()
        args = parser.parse_args(["climate", "--path", ".", "auth.py"])
        assert args.command == "climate"
        assert args.file == "auth.py"

    def test_history_command(self):
        parser = build_parser()
        args = parser.parse_args(["history", "--path", ".", "--last-month"])
        assert args.command == "history"
        assert args.last_month is True


class TestCLICommands:
    def test_survey(self, git_repo, capsys):
        sys.argv = ["isobar", "survey", "--path", str(git_repo)]
        main()
        captured = capsys.readouterr()
        assert "Scanning" in captured.out

    def test_current(self, git_repo, capsys):
        sys.argv = ["isobar", "current", "--path", str(git_repo)]
        main()
        captured = capsys.readouterr()
        assert "CURRENT CONDITIONS" in captured.out

    def test_map_text(self, git_repo, capsys):
        sys.argv = ["isobar", "map", "--path", str(git_repo)]
        main()
        captured = capsys.readouterr()
        assert "ISOBAR" in captured.out

    def test_map_json(self, git_repo, capsys):
        sys.argv = ["isobar", "map", "--path", str(git_repo), "--format", "json"]
        main()
        captured = capsys.readouterr()
        assert "profiles" in captured.out

    def test_fronts(self, git_repo, capsys):
        sys.argv = ["isobar", "fronts", "--path", str(git_repo)]
        main()
        captured = capsys.readouterr()
        assert "FRONTAL ANALYSIS" in captured.out or "stable" in captured.out.lower()

    def test_forecast(self, git_repo, capsys):
        sys.argv = ["isobar", "forecast", "--path", str(git_repo), "--ahead", "2"]
        main()
        captured = capsys.readouterr()
        assert "FORECAST" in captured.out

    def test_warn(self, git_repo, capsys):
        sys.argv = ["isobar", "warn", "--path", str(git_repo)]
        main()
        captured = capsys.readouterr()
        # Either warnings or calm message
        assert len(captured.out) > 0

    def test_no_command_shows_help(self, capsys):
        sys.argv = ["isobar"]
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_nonexistent_path(self, capsys):
        sys.argv = ["isobar", "survey", "--path", "/nonexistent/path/xyz"]
        with pytest.raises(SystemExit):
            main()
