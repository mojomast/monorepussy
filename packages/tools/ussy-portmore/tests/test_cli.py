"""Tests for the CLI interface."""
import pytest

from portmore.cli import build_parser, main


class TestCLIParser:
    """Tests for CLI argument parsing."""

    def test_classify_command(self):
        parser = build_parser()
        args = parser.parse_args(["classify", "./my-project"])
        assert args.command == "classify"
        assert args.project == "./my-project"

    def test_classify_with_format(self):
        parser = build_parser()
        args = parser.parse_args(["classify", "./my-project", "--format", "json"])
        assert args.format == "json"

    def test_origin_command(self):
        parser = build_parser()
        args = parser.parse_args(["origin", "./my-project", "--threshold", "0.50"])
        assert args.command == "origin"
        assert args.threshold == 0.50

    def test_compatibility_command(self):
        parser = build_parser()
        args = parser.parse_args([
            "compatibility", "--from", "MIT", "--to", "GPL-3.0"
        ])
        assert args.command == "compatibility"
        assert args.from_license == "MIT"
        assert args.to_license == "GPL-3.0"

    def test_value_command(self):
        parser = build_parser()
        args = parser.parse_args(["value", "--license", "MIT"])
        assert args.command == "value"
        assert args.license == "MIT"

    def test_contagion_command(self):
        parser = build_parser()
        args = parser.parse_args([
            "contagion", "--copyleft", "GPL-3.0", "--ratio", "0.70"
        ])
        assert args.command == "contagion"
        assert args.copyleft == "GPL-3.0"
        assert args.ratio == 0.70

    def test_quarantine_command(self):
        parser = build_parser()
        args = parser.parse_args(["quarantine", "./my-project", "--check"])
        assert args.command == "quarantine"
        assert args.check is True

    def test_version_flag(self):
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0


class TestCLICommands:
    """Tests for CLI command execution."""

    def test_compatibility_runs(self, capsys):
        exit_code = main(["compatibility", "--from", "MIT", "--to", "Apache-2.0"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "COMPATIBLE" in captured.out

    def test_compatibility_json(self, capsys):
        exit_code = main([
            "compatibility", "--from", "MIT", "--to", "Apache-2.0", "--format", "json"
        ])
        assert exit_code == 0

    def test_contagion_runs(self, capsys):
        exit_code = main([
            "contagion", "--copyleft", "GPL-3.0", "--ratio", "0.70"
        ])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "DUMPING" in captured.out

    def test_value_runs(self, capsys):
        exit_code = main(["value", "--license", "MIT"])
        assert exit_code == 0

    def test_no_command(self, capsys):
        exit_code = main([])
        assert exit_code == 0

    def test_compatibility_missing_args(self, capsys):
        with pytest.raises(SystemExit):
            main(["compatibility"])

    def test_classify_nonexistent(self, capsys):
        exit_code = main(["classify", "/nonexistent/xyz"])
        assert exit_code == 1

    def test_contagion_json(self, capsys):
        exit_code = main([
            "contagion", "--copyleft", "AGPL-3.0", "--ratio", "0.80", "--format", "json"
        ])
        assert exit_code == 0

    def test_value_json(self, capsys):
        exit_code = main(["value", "--license", "GPL-3.0", "--format", "json"])
        assert exit_code == 0

    def test_contagion_with_linkage(self, capsys):
        exit_code = main([
            "contagion", "--copyleft", "GPL-3.0", "--ratio", "0.50",
            "--linkage", "dynamic"
        ])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "NO" in captured.out or "dynamic" in captured.out.lower()
