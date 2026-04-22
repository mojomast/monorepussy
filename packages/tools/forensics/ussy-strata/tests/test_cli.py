"""Tests for the CLI module (ussy_strata.cli)."""

import pytest
import subprocess
import sys
from ussy_strata.cli import main


class TestCLIHelp:
    def test_help_flag(self):
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0

    def test_survey_help(self):
        with pytest.raises(SystemExit) as exc:
            main(["survey", "--help"])
        assert exc.value.code == 0


class TestCLISurvey:
    def test_basic_survey(self, git_repo, capsys):
        result = main(["survey", "-C", git_repo])
        assert result == 0
        captured = capsys.readouterr()
        assert "GEOLOGICAL SURVEY" in captured.out

    def test_survey_no_fossils(self, git_repo, capsys):
        result = main(["survey", "-C", git_repo, "--no-fossils"])
        assert result == 0

    def test_survey_max_commits(self, git_repo, capsys):
        result = main(["survey", "-C", git_repo, "-n", "2"])
        assert result == 0

    def test_invalid_repo(self):
        result = main(["survey", "-C", "/nonexistent/path"])
        assert result == 1


class TestCLINoCommand:
    def test_default_to_survey(self, git_repo, capsys):
        result = main(["-C", git_repo])
        assert result == 0
        captured = capsys.readouterr()
        assert "GEOLOGICAL SURVEY" in captured.out


class TestCLIModuleExecution:
    def test_module_help(self, git_repo):
        result = subprocess.run(
            [sys.executable, "-m", "ussy_strata", "--help"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "ussy-strata" in result.stdout.lower() or "geological" in result.stdout.lower()
