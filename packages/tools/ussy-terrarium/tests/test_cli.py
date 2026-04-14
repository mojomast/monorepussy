"""Tests for the CLI interface."""

import os
import sys
import tempfile

import pytest

from terrarium.cli import main, create_parser


class TestCreateParser:
    """Tests for CLI argument parser."""

    def test_parser_creation(self):
        """Parser is created without error."""
        parser = create_parser()
        assert parser is not None

    def test_watch_command(self):
        """Watch command is parsed."""
        parser = create_parser()
        args = parser.parse_args(["watch", "."])
        assert args.command == "watch"
        assert args.path == "."

    def test_diagnose_command(self):
        """Diagnose command is parsed."""
        parser = create_parser()
        args = parser.parse_args(["diagnose", "src/main.py"])
        assert args.command == "diagnose"
        assert args.path == "src/main.py"

    def test_snapshot_command(self):
        """Snapshot command is parsed with options."""
        parser = create_parser()
        args = parser.parse_args(["snapshot", "--format", "svg", "--output", "out.svg", "."])
        assert args.command == "snapshot"
        assert args.format == "svg"
        assert args.output == "out.svg"

    def test_seasons_command(self):
        """Seasons command is parsed."""
        parser = create_parser()
        args = parser.parse_args(["seasons", ".", "--since", "6 months ago"])
        assert args.command == "seasons"
        assert args.since == "6 months ago"

    def test_health_command(self):
        """Health command is parsed."""
        parser = create_parser()
        args = parser.parse_args(["health", "."])
        assert args.command == "health"

    def test_no_command(self):
        """No command is handled gracefully."""
        parser = create_parser()
        args = parser.parse_args([])
        assert getattr(args, "command", None) is None


class TestMainCLI:
    """Tests for the main CLI entry point."""

    def test_no_args_returns_zero(self):
        """No arguments prints help and returns 0."""
        result = main([])
        assert result == 0

    def test_health_on_temp_project(self):
        """Health command works on a temporary project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a Python file
            src_dir = os.path.join(tmpdir, "src")
            os.makedirs(src_dir)
            with open(os.path.join(src_dir, "main.py"), "w") as f:
                f.write("def main():\n    pass\n")

            result = main(["health", tmpdir])
            assert result == 0

    def test_watch_on_temp_project(self):
        """Watch command works on a temporary project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = os.path.join(tmpdir, "src")
            os.makedirs(src_dir)
            with open(os.path.join(src_dir, "main.py"), "w") as f:
                f.write("def main():\n    pass\n")

            result = main(["watch", tmpdir])
            assert result == 0

    def test_snapshot_text(self):
        """Snapshot command with text format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = os.path.join(tmpdir, "src")
            os.makedirs(src_dir)
            with open(os.path.join(src_dir, "main.py"), "w") as f:
                f.write("def main():\n    pass\n")

            result = main(["snapshot", "--format", "text", tmpdir])
            assert result == 0

    def test_snapshot_to_file(self):
        """Snapshot command writes to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = os.path.join(tmpdir, "src")
            os.makedirs(src_dir)
            with open(os.path.join(src_dir, "main.py"), "w") as f:
                f.write("def main():\n    pass\n")

            output_path = os.path.join(tmpdir, "report.txt")
            result = main(["snapshot", "--format", "text", "--output", output_path, tmpdir])
            assert result == 0
            assert os.path.exists(output_path)

    def test_diagnose_file(self):
        """Diagnose command works on a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "module.py")
            with open(filepath, "w") as f:
                f.write("def func():\n    if True:\n        pass\n")

            result = main(["diagnose", filepath])
            assert result == 0

    def test_diagnose_nonexistent(self):
        """Diagnose on non-existent file returns error."""
        result = main(["diagnose", "/nonexistent/file.py"])
        assert result == 1

    def test_health_nonexistent_dir(self):
        """Health on non-existent directory returns error."""
        result = main(["health", "/nonexistent/dir"])
        assert result == 1

    def test_version(self):
        """Version flag works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
