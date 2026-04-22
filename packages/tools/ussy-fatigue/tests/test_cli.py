"""Tests for the CLI module."""

import os
import json
import tempfile
import pytest

from ussy_fatigue.cli import main, create_parser


FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures")
SAMPLE_CODE_DIR = os.path.join(FIXTURES_DIR, "sample_code")


class TestParser:
    """Tests for CLI argument parser."""

    def test_create_parser(self):
        """Test parser creation."""
        parser = create_parser()
        assert parser is not None

    def test_scan_command(self):
        """Test parsing scan command."""
        parser = create_parser()
        args = parser.parse_args(["scan", "."])
        assert args.command == "scan"
        assert args.path == "."

    def test_predict_command(self):
        """Test parsing predict command."""
        parser = create_parser()
        args = parser.parse_args(["predict", "src/module.py", "--horizon", "6"])
        assert args.command == "predict"
        assert args.path == "src/module.py"
        assert args.horizon == 6

    def test_whatif_command(self):
        """Test parsing what-if command."""
        parser = create_parser()
        args = parser.parse_args(["what-if", "src/module.py", "--refactor", "extract_interface"])
        assert args.command == "what-if"
        assert args.refactor == "extract_interface"

    def test_calibrate_command(self):
        """Test parsing calibrate command."""
        parser = create_parser()
        args = parser.parse_args(["calibrate", "."])
        assert args.command == "calibrate"
        assert args.path == "."

    def test_no_command(self):
        """Test parsing with no command."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.command is None

    def test_predict_custom_params(self):
        """Test predict with custom Paris' Law parameters."""
        parser = create_parser()
        args = parser.parse_args([
            "predict", "test.py",
            "--C", "0.02",
            "--m", "3.0",
            "--K-Ic", "35.0",
            "--K-e", "10.0",
        ])
        assert args.C == 0.02
        assert args.m == 3.0
        assert args.K_Ic == 35.0
        assert args.K_e == 10.0

    def test_whatif_in_sprints(self):
        """Test what-if with --in parameter."""
        parser = create_parser()
        args = parser.parse_args([
            "what-if", "test.py",
            "--refactor", "add_tests",
            "--in", "3",
        ])
        assert args.in_sprints == 3


class TestCLIScan:
    """Tests for the scan CLI command."""

    def test_scan_directory(self, sample_code_dir):
        """Test scanning a directory via CLI."""
        result = main(["scan", sample_code_dir])
        assert result == 0

    def test_scan_file(self):
        """Test scanning a single file via CLI."""
        fpath = os.path.join(SAMPLE_CODE_DIR, "god_class_module.py")
        result = main(["scan", fpath])
        assert result == 0

    def test_scan_json_output(self, sample_code_dir):
        """Test scan with JSON output."""
        result = main(["scan", sample_code_dir, "--format", "json"])
        assert result == 0

    def test_scan_nonexistent(self):
        """Test scanning nonexistent path."""
        result = main(["scan", "/nonexistent/path"])
        assert result == 1


class TestCLIPredict:
    """Tests for the predict CLI command."""

    def test_predict_file(self):
        """Test predicting for a file via CLI."""
        fpath = os.path.join(SAMPLE_CODE_DIR, "god_class_module.py")
        result = main(["predict", fpath])
        assert result == 0

    def test_predict_nonexistent(self):
        """Test predicting for nonexistent file."""
        result = main(["predict", "/nonexistent/file.py"])
        assert result == 1


class TestCLIWhatIf:
    """Tests for the what-if CLI command."""

    def test_whatif_extract_interface(self):
        """Test what-if with extract interface."""
        fpath = os.path.join(SAMPLE_CODE_DIR, "god_class_module.py")
        result = main(["what-if", fpath, "--refactor", "extract_interface"])
        assert result == 0

    def test_whatif_add_tests(self):
        """Test what-if with add tests."""
        fpath = os.path.join(SAMPLE_CODE_DIR, "god_class_module.py")
        result = main(["what-if", fpath, "--refactor", "add_tests"])
        assert result == 0

    def test_whatif_nonexistent(self):
        """Test what-if for nonexistent file."""
        result = main(["what-if", "/nonexistent/file.py", "--refactor", "extract_interface"])
        assert result == 1


class TestCLICalibrate:
    """Tests for the calibrate CLI command."""

    def test_calibrate_directory(self, sample_code_dir):
        """Test calibrating from a directory."""
        result = main(["calibrate", sample_code_dir])
        assert result == 0

    def test_calibrate_with_data_file(self, calibration_json_file, sample_code_dir):
        """Test calibrating with a data file."""
        result = main(["calibrate", sample_code_dir, "--data", calibration_json_file])
        assert result == 0

    def test_calibrate_nonexistent(self):
        """Test calibrating from nonexistent directory."""
        result = main(["calibrate", "/nonexistent/dir"])
        assert result == 1


class TestCLIMain:
    """Tests for main CLI entry point."""

    def test_no_command_returns_0(self):
        """Test that no command returns 0 (shows help)."""
        result = main([])
        assert result == 0
