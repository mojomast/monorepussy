"""Tests for mint.cli — CLI interface."""

import pytest
import sys
from io import StringIO
from pathlib import Path

from ussy_mint.cli import main, build_parser, _parse_package_spec

FIXTURES = Path(__file__).parent / "fixtures"


class TestParsePackageSpec:
    """Test package specification parsing."""

    def test_name_and_version(self):
        name, version = _parse_package_spec("lodash@4.17.21")
        assert name == "lodash"
        assert version == "4.17.21"

    def test_name_only(self):
        name, version = _parse_package_spec("lodash")
        assert name == "lodash"
        assert version == "latest"

    def test_scoped_package(self):
        name, version = _parse_package_spec("@babel/core@7.23.0")
        assert name == "@babel/core"
        assert version == "7.23.0"


class TestBuildParser:
    """Test argument parser construction."""

    def test_parser_created(self):
        parser = build_parser()
        assert parser is not None

    def test_version_flag(self):
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0


class TestCmdGrade:
    """Test the grade command."""

    def test_grade_known_package(self):
        """Grade a known package."""
        result = main(["grade", "lodash@4.17.21"])
        assert result == 0

    def test_grade_unknown_package(self):
        """Grade an unknown package (still works with heuristics)."""
        result = main(["grade", "mystery-pkg@1.0.0"])
        assert result == 0

    def test_grade_no_package(self):
        """Grade with no package specified should return error."""
        result = main(["grade"])
        assert result == 1


class TestCmdHoard:
    """Test the hoard command."""

    def test_hoard_with_lockfile(self):
        """Analyze a real lockfile."""
        result = main(["hoard", str(FIXTURES / "package-lock.json")])
        assert result == 0

    def test_hoard_no_lockfile(self):
        """No lockfile specified should return error."""
        result = main(["hoard"])
        assert result == 1

    def test_hoard_missing_file(self):
        """Nonexistent file should return error."""
        result = main(["hoard", "/nonexistent/lock.json"])
        assert result == 1


class TestCmdAuthenticate:
    """Test the authenticate command."""

    def test_authenticate_package(self):
        """Authenticate a single package."""
        result = main(["authenticate", "express"])
        assert result == 0

    def test_authenticate_suspicious_package(self):
        """Authenticate a suspicious package name."""
        result = main(["authenticate", "xpress"])
        assert result == 0

    def test_authenticate_no_args(self):
        """No args should return error."""
        result = main(["authenticate"])
        assert result == 1

    def test_authenticate_with_lockfile(self):
        """Authenticate all packages in a lockfile."""
        result = main(["authenticate", "--lockfile", str(FIXTURES / "package-lock.json")])
        assert result == 0


class TestCmdDebasement:
    """Test the debasement command."""

    def test_debasement_package(self):
        """Track debasement for a package."""
        result = main(["debasement", "lodash"])
        assert result == 0

    def test_debasement_no_package(self):
        """No package should return error."""
        result = main(["debasement"])
        assert result == 1


class TestMainNoCommand:
    """Test main with no command."""

    def test_no_command_shows_help(self):
        """No command should show help and return 0."""
        result = main([])
        assert result == 0
