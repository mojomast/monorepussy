"""Tests for crystallo.cli — command-line interface."""

import pytest
from pathlib import Path

from crystallo.cli import main, build_parser


FIXTURES = Path(__file__).parent / "fixtures"


class TestBuildParser:
    def test_parser_creates(self):
        parser = build_parser()
        assert parser is not None

    def test_version(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_no_command_shows_help(self):
        result = main([])
        assert result == 0


class TestScanCommand:
    def test_scan_fixtures(self):
        result = main(["scan", str(FIXTURES)])
        assert result == 0

    def test_scan_single_file(self):
        result = main(["scan", str(FIXTURES / "models.py")])
        assert result == 0

    def test_scan_no_paths(self):
        result = main(["scan"])
        assert result == 1

    def test_scan_with_threshold(self):
        result = main(["scan", "--threshold", "0.6", str(FIXTURES)])
        assert result == 0


class TestSymmetryCommand:
    def test_symmetry_fixtures(self):
        result = main(["symmetry", str(FIXTURES)])
        assert result == 0

    def test_symmetry_with_type_filter(self):
        result = main(["symmetry", "--type", "rotational", str(FIXTURES)])
        assert result == 0

    def test_symmetry_invalid_type(self):
        result = main(["symmetry", "--type", "invalid_type", str(FIXTURES)])
        assert result == 1


class TestDefectsCommand:
    def test_defects_fixtures(self):
        result = main(["defects", str(FIXTURES)])
        assert result == 0

    def test_defects_no_paths(self):
        result = main(["defects"])
        assert result == 1


class TestClassifyCommand:
    def test_classify_fixtures(self):
        result = main(["classify", str(FIXTURES)])
        assert result == 0

    def test_classify_no_paths(self):
        result = main(["classify"])
        assert result == 1


class TestUnitCellCommand:
    def test_unit_cell_fixtures(self):
        result = main(["unit-cell", str(FIXTURES)])
        assert result == 0

    def test_unit_cell_no_paths(self):
        result = main(["unit-cell"])
        assert result == 1


class TestCLIHandlesDirectory:
    def test_directory_walk(self):
        """CLI should walk directories for Python files."""
        result = main(["scan", str(FIXTURES)])
        assert result == 0

    def test_nonexistent_path(self):
        """CLI should handle nonexistent paths gracefully."""
        result = main(["scan", "/nonexistent/path/xyz123"])
        assert result == 0  # no files found but doesn't crash
