"""Tests for the CLI module (stratagit.cli)."""

import pytest
import subprocess
import sys
from stratagit.cli import main


class TestCLIHelp:
    def test_help_flag(self):
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0

    def test_survey_help(self):
        with pytest.raises(SystemExit) as exc:
            main(["survey", "--help"])
        assert exc.value.code == 0

    def test_cross_section_help(self):
        with pytest.raises(SystemExit) as exc:
            main(["cross-section", "--help"])
        assert exc.value.code == 0

    def test_excavate_help(self):
        with pytest.raises(SystemExit) as exc:
            main(["excavate", "--help"])
        assert exc.value.code == 0


class TestCLISurvey:
    def test_basic_survey(self, git_repo, capsys):
        result = main(["-C", git_repo, "survey"])
        assert result == 0
        captured = capsys.readouterr()
        assert "STRATAGIT" in captured.out

    def test_survey_no_fossils(self, git_repo, capsys):
        result = main(["-C", git_repo, "survey", "--no-fossils"])
        assert result == 0

    def test_survey_max_commits(self, git_repo, capsys):
        result = main(["-C", git_repo, "-n", "2", "survey"])
        assert result == 0

    def test_invalid_repo(self):
        result = main(["-C", "/nonexistent/path", "survey"])
        assert result == 1


class TestCLICrossSection:
    def test_basic_cross_section(self, git_repo, capsys):
        result = main(["-C", git_repo, "cross-section"])
        assert result == 0
        captured = capsys.readouterr()
        assert "STRATIGRAPHIC" in captured.out

    def test_cross_section_no_color(self, git_repo, capsys):
        result = main(["-C", git_repo, "--no-color", "cross-section"])
        assert result == 0


class TestCLIExcavate:
    def test_basic_excavate(self, git_repo, capsys):
        result = main(["-C", git_repo, "excavate"])
        assert result == 0

    def test_excavate_with_pattern(self, git_repo, capsys):
        result = main(["-C", git_repo, "excavate", "-p", "hello"])
        assert result == 0


class TestCLIUnconformities:
    def test_basic(self, git_repo, capsys):
        result = main(["-C", git_repo, "unconformities"])
        assert result == 0


class TestCLIFaults:
    def test_basic(self, git_repo, capsys):
        result = main(["-C", git_repo, "faults"])
        assert result == 0


class TestCLICarbonDate:
    def test_basic(self, git_repo, capsys):
        result = main(["-C", git_repo, "carbon-date", "README.md", "1"])
        assert result == 0
        captured = capsys.readouterr()
        assert "CARBON DATING" in captured.out


class TestCLILegend:
    def test_basic(self, capsys):
        result = main(["legend"])
        assert result == 0
        captured = capsys.readouterr()
        assert "MINERAL LEGEND" in captured.out


class TestCLINoCommand:
    def test_default_to_survey(self, git_repo, capsys):
        result = main(["-C", git_repo])
        assert result == 0
        captured = capsys.readouterr()
        assert "STRATAGIT" in captured.out


class TestCLIModuleExecution:
    def test_module_help(self, git_repo):
        result = subprocess.run(
            [sys.executable, "-m", "stratagit", "--help"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "stratagit" in result.stdout.lower() or "geological" in result.stdout.lower()
