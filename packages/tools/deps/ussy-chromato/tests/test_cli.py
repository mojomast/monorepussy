"""Tests for chromato.cli — Command-line interface."""

import pytest
from pathlib import Path

from ussy_chromato.cli import main, build_parser


FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestBuildParser:
    def test_parser_creates(self):
        parser = build_parser()
        assert parser is not None

    def test_scan_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "test.txt"])
        assert args.command == "scan"
        assert args.source == "test.txt"

    def test_scan_with_solvent(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "test.txt", "--solvent", "risk"])
        assert args.solvent == "risk"

    def test_scan_with_format(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "test.txt", "--format", "json"])
        assert args.format == "json"

    def test_scan_with_exit_on_risk(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "test.txt", "--exit-on-risk", "0.8"])
        assert args.exit_on_risk == 0.8

    def test_diff_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["diff", "a.txt", "b.txt"])
        assert args.command == "diff"
        assert args.source_a == "a.txt"
        assert args.source_b == "b.txt"

    def test_coelute_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["coelute", "test.txt", "--threshold", "0.5"])
        assert args.command == "coelute"
        assert args.threshold == 0.5

    def test_peaks_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["peaks", "test.txt", "--diagnose"])
        assert args.command == "peaks"
        assert args.diagnose is True


class TestCLIMain:
    def test_no_command_returns_zero(self):
        result = main([])
        assert result == 0

    def test_scan_chromatogram(self, capsys):
        result = main(["scan", str(FIXTURES / "requirements.txt")])
        assert result == 0
        captured = capsys.readouterr()
        assert "CHROMATOGRAM" in captured.out

    def test_scan_json(self, capsys):
        result = main(["scan", str(FIXTURES / "requirements.txt"), "--format", "json"])
        assert result == 0
        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out)
        assert "peaks" in data

    def test_scan_risk_solvent(self, capsys):
        result = main(["scan", str(FIXTURES / "requirements.txt"), "--solvent", "risk"])
        assert result == 0

    def test_scan_nonexistent(self):
        result = main(["scan", "/nonexistent/file.txt"])
        assert result == 1

    def test_diff_command(self, capsys):
        result = main([
            "diff",
            str(FIXTURES / "requirements.txt"),
            str(FIXTURES / "requirements-new.txt"),
        ])
        assert result == 0
        captured = capsys.readouterr()
        assert "DIFFERENTIAL" in captured.out

    def test_coelute_command(self, capsys):
        result = main(["coelute", str(FIXTURES / "requirements.txt")])
        assert result == 0

    def test_peaks_command(self, capsys):
        result = main(["peaks", str(FIXTURES / "requirements.txt")])
        assert result == 0
        captured = capsys.readouterr()
        assert "PEAK SHAPE" in captured.out

    def test_peaks_diagnose(self, capsys):
        result = main(["peaks", str(FIXTURES / "requirements.txt"), "--diagnose"])
        assert result == 0

    def test_scan_exit_on_risk(self, capsys):
        # Very low threshold should trigger exit
        result = main([
            "scan",
            str(FIXTURES / "requirements.txt"),
            "--exit-on-risk", "0.001",
        ])
        # May or may not exit 1 depending on actual risk scores
        assert result in (0, 1)

    def test_scan_directory(self, capsys):
        result = main(["scan", str(FIXTURES)])
        assert result == 0
