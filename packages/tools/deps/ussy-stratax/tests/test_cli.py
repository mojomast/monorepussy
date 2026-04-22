"""Tests for CLI interface."""
import json
import os
import tempfile
import pytest
from ussy_stratax.cli import main, build_parser


class TestCLIParser:
    def test_no_command_shows_help(self):
        # Should return 0 (help shown)
        assert main([]) == 0

    def test_scan_requires_lockfile(self):
        with pytest.raises(SystemExit):
            main(["scan"])

    def test_analyze_requires_package(self):
        with pytest.raises(SystemExit):
            main(["analyze"])

    def test_diff_requires_args(self):
        with pytest.raises(SystemExit):
            main(["diff", "pkg"])

        with pytest.raises(SystemExit):
            main(["diff"])

    def test_legend_command(self):
        assert main(["legend"]) == 0

    def test_scan_nonexistent_file(self):
        assert main(["scan", "/nonexistent/file.txt"]) == 1


class TestCLILegend:
    def test_legend_output(self, capsys):
        main(["legend"])
        captured = capsys.readouterr()
        assert "Bedrock" in captured.out
        assert "Quicksand" in captured.out
        assert "Seismic" in captured.out
        assert "Fault Line" in captured.out


class TestCLIScan:
    def test_scan_requirements_txt(self, capsys):
        tmpdir = tempfile.mkdtemp()
        lockfile = os.path.join(tmpdir, "requirements.txt")
        with open(lockfile, "w") as f:
            f.write("json==1.0.0\n")  # stdlib, always available

        result = main(["scan", lockfile])
        captured = capsys.readouterr()
        assert "1 dependencies" in captured.out or "dependencies" in captured.out

    def test_scan_empty_requirements(self, capsys):
        tmpdir = tempfile.mkdtemp()
        lockfile = os.path.join(tmpdir, "requirements.txt")
        with open(lockfile, "w") as f:
            f.write("# just a comment\n")

        result = main(["scan", lockfile])
        captured = capsys.readouterr()
        assert "No dependencies" in captured.out

    def test_scan_npm_lockfile(self, capsys):
        tmpdir = tempfile.mkdtemp()
        lockfile = os.path.join(tmpdir, "package-lock.json")
        data = {
            "packages": {
                "": {},
                "node_modules/lodash": {"version": "4.17.21"},
            }
        }
        with open(lockfile, "w") as f:
            json.dump(data, f)

        result = main(["scan", lockfile])
        captured = capsys.readouterr()
        assert "1 dependencies" in captured.out or "dependencies" in captured.out

    def test_scan_no_color(self, capsys):
        tmpdir = tempfile.mkdtemp()
        lockfile = os.path.join(tmpdir, "requirements.txt")
        with open(lockfile, "w") as f:
            f.write("numpy==1.24.0\n")

        main(["--no-color", "scan", lockfile])
        captured = capsys.readouterr()
        # Should not contain ANSI codes
        assert "\033[" not in captured.out


class TestBuildParser:
    def test_parser_structure(self):
        parser = build_parser()
        assert parser.prog == "strata"

    def test_scan_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "test.lock"])
        assert args.command == "scan"
        assert args.lockfile == "test.lock"

    def test_analyze_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["analyze", "numpy"])
        assert args.command == "analyze"
        assert args.package == "numpy"

    def test_diff_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["diff", "numpy", "1.0.0", "2.0.0"])
        assert args.command == "diff"
        assert args.package == "numpy"
        assert args.version_a == "1.0.0"
        assert args.version_b == "2.0.0"

    def test_json_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--json", "scan", "test.lock"])
        assert args.json is True

    def test_no_color_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--no-color", "legend"])
        assert args.no_color is True

    def test_probe_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["probe", "numpy"])
        assert args.command == "probe"
        assert args.package == "numpy"

    def test_run_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["run", "numpy", "--version", "1.24.0"])
        assert args.command == "run"
        assert args.package == "numpy"
        assert args.version == "1.24.0"
