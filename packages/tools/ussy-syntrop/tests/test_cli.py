"""Tests for the CLI module."""

import pytest
from pathlib import Path

from syntrop.cli import build_parser, main


SOURCE_ORDER_DEP = """
def main():
    result = []
    for item in [1, 2, 3]:
        result.append(item * 2)
    return result
"""

SOURCE_PURE = """
def main():
    return 2 + 3
"""


class TestBuildParser:
    """Tests for the argument parser."""

    def test_parser_created(self):
        parser = build_parser()
        assert parser is not None

    def test_parser_version(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_probe_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["probe", "--file", "test.py"])
        assert args.command == "probe"
        assert args.file == "test.py"

    def test_scan_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "--directory", "/tmp"])
        assert args.command == "scan"
        assert args.directory == "/tmp"

    def test_diff_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["diff", "--file", "test.py"])
        assert args.command == "diff"
        assert args.file == "test.py"

    def test_probe_with_probes(self):
        parser = build_parser()
        args = parser.parse_args(["probe", "--file", "test.py", "--probes", "randomize-iteration"])
        assert args.probes == "randomize-iteration"

    def test_probe_with_function(self):
        parser = build_parser()
        args = parser.parse_args(["probe", "--file", "test.py", "--function", "process"])
        assert args.function == "process"

    def test_diff_with_probes(self):
        parser = build_parser()
        args = parser.parse_args(["diff", "--file", "test.py", "--probes", "alias-state"])
        assert args.probes == "alias-state"


class TestCLIMain:
    """Tests for the main CLI function."""

    def test_no_command_returns_zero(self):
        result = main([])
        assert result == 0

    def test_probe_missing_file(self):
        result = main(["probe", "--file", "/nonexistent/file.py"])
        assert result == 1

    def test_probe_unknown_probe(self):
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(SOURCE_PURE)
            f.flush()
            result = main(["probe", "--file", f.name, "--probes", "nonexistent"])
            assert result == 1

    def test_probe_valid_file(self):
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(SOURCE_PURE)
            f.flush()
            result = main(["probe", "--file", f.name, "--probes", "randomize-iteration"])
            # Pure code should not diverge
            assert result == 0

    def test_scan_valid_directory(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(SOURCE_PURE)
            result = main(["scan", "--directory", tmpdir])
            # Pure code shouldn't have divergences
            assert result == 0

    def test_scan_nonexistent_directory(self):
        result = main(["scan", "--directory", "/nonexistent/dir"])
        assert result == 1

    def test_diff_valid_file(self):
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(SOURCE_PURE)
            f.flush()
            result = main(["diff", "--file", f.name, "--probes", "randomize-iteration"])
            assert result == 0

    def test_diff_missing_file(self):
        result = main(["diff", "--file", "/nonexistent/file.py"])
        assert result == 1
