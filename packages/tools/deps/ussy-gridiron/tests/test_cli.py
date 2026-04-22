"""Tests for the CLI interface."""

import os
import sys
import pytest

from gridiron.cli import build_graph, create_parser, main
from gridiron.graph import DependencyGraph


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestBuildGraph:
    """Tests for graph building from project paths."""

    def test_build_from_package_json(self):
        path = os.path.join(FIXTURES_DIR, "package.json")
        graph = build_graph(path)
        assert graph.package_count() > 0

    def test_build_from_requirements_txt(self):
        path = os.path.join(FIXTURES_DIR, "requirements.txt")
        graph = build_graph(path)
        assert graph.package_count() > 0

    def test_build_from_pyproject_toml(self):
        path = os.path.join(FIXTURES_DIR, "pyproject.toml")
        graph = build_graph(path)
        assert graph.package_count() > 0

    def test_build_from_directory(self):
        graph = build_graph(FIXTURES_DIR)
        assert graph.package_count() > 0

    def test_build_from_nonexistent(self):
        graph = build_graph("/nonexistent/path")
        assert graph.package_count() == 0


class TestCLIParser:
    """Tests for CLI argument parsing."""

    def test_parser_created(self):
        parser = create_parser()
        assert parser is not None

    def test_n1_command(self):
        parser = create_parser()
        args = parser.parse_args(["n1", "/tmp/project"])
        assert args.command == "n1"
        assert args.project == "/tmp/project"

    def test_frequency_command_with_shock(self):
        parser = create_parser()
        args = parser.parse_args(["frequency", "/tmp/project", "--shock", "lib"])
        assert args.command == "frequency"
        assert args.shock == "lib"

    def test_dispatch_command(self):
        parser = create_parser()
        args = parser.parse_args(["dispatch", "/tmp/project"])
        assert args.command == "dispatch"

    def test_relay_command(self):
        parser = create_parser()
        args = parser.parse_args(["relay", "/tmp/project"])
        assert args.command == "relay"

    def test_voltage_command(self):
        parser = create_parser()
        args = parser.parse_args(["voltage", "/tmp/project"])
        assert args.command == "voltage"

    def test_inspect_command_with_package(self):
        parser = create_parser()
        args = parser.parse_args(["inspect", "/tmp/project", "--package", "lib"])
        assert args.command == "inspect"
        assert args.package == "lib"

    def test_report_command(self):
        parser = create_parser()
        args = parser.parse_args(["report", "/tmp/project", "--full"])
        assert args.command == "report"
        assert args.full is True

    def test_format_option(self):
        parser = create_parser()
        args = parser.parse_args(["--format", "json", "n1", "/tmp/project"])
        assert args.format == "json"


class TestCLIExecution:
    """Tests for CLI command execution."""

    def test_n1_runs(self, capsys):
        main(["n1", os.path.join(FIXTURES_DIR, "package.json")])
        captured = capsys.readouterr()
        assert "N-1" in captured.out or "GRIDIRON" in captured.out

    def test_frequency_runs(self, capsys):
        main(["frequency", os.path.join(FIXTURES_DIR, "package.json")])
        captured = capsys.readouterr()
        assert "FREQUENCY" in captured.out or "GRIDIRON" in captured.out

    def test_dispatch_runs(self, capsys):
        main(["dispatch", os.path.join(FIXTURES_DIR, "package.json")])
        captured = capsys.readouterr()
        assert "FLOW" in captured.out or "GRIDIRON" in captured.out

    def test_relay_runs(self, capsys):
        main(["relay", os.path.join(FIXTURES_DIR, "package.json")])
        captured = capsys.readouterr()
        assert "RELAY" in captured.out or "GRIDIRON" in captured.out

    def test_voltage_runs(self, capsys):
        main(["voltage", os.path.join(FIXTURES_DIR, "package.json")])
        captured = capsys.readouterr()
        assert "VOLTAGE" in captured.out or "GRIDIRON" in captured.out

    def test_inspect_runs(self, capsys):
        main(["inspect", os.path.join(FIXTURES_DIR, "package.json")])
        captured = capsys.readouterr()
        assert "GRID CODE" in captured.out or "GRIDIRON" in captured.out

    def test_report_runs(self, capsys):
        main(["report", os.path.join(FIXTURES_DIR, "package.json")])
        captured = capsys.readouterr()
        assert "GRIDIRON" in captured.out

    def test_json_format(self, capsys):
        main(["--format", "json", "n1", os.path.join(FIXTURES_DIR, "package.json")])
        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out)
        assert "n1" in data

    def test_no_command_shows_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 0


class TestDBModule:
    """Tests for the SQLite database module."""

    def test_save_and_load_package(self):
        from gridiron.db import GridironDB
        from gridiron.models import PackageInfo
        from datetime import datetime, timezone

        db = GridironDB()
        pkg = PackageInfo(
            name="test-pkg",
            version="1.2.3",
            is_direct=True,
            maintainers=3,
            last_release=datetime.now(timezone.utc),
        )
        db.save_package(pkg)
        loaded = db.load_package("test-pkg")
        assert loaded is not None
        assert loaded.name == "test-pkg"
        assert loaded.version == "1.2.3"
        assert loaded.maintainers == 3
        db.close()

    def test_save_and_load_edge(self):
        from gridiron.db import GridironDB
        from gridiron.models import DependencyEdge, PackageInfo

        db = GridironDB()
        db.save_package(PackageInfo(name="a"))
        db.save_package(PackageInfo(name="b"))
        edge = DependencyEdge(source="a", target="b", version_constraint="^1.0")
        db.save_edge(edge)
        edges = db.load_all_edges()
        assert len(edges) == 1
        assert edges[0].source == "a"
        assert edges[0].target == "b"
        db.close()

    def test_save_analysis_result(self):
        from gridiron.db import GridironDB

        db = GridironDB()
        db.save_analysis("n1", "/tmp/test", {"score": 95.0})
        # No error means success
        db.close()

    def test_load_nonexistent_package(self):
        from gridiron.db import GridironDB

        db = GridironDB()
        result = db.load_package("nonexistent")
        assert result is None
        db.close()


class TestReportFormatter:
    """Tests for the report formatter."""

    def test_text_format(self):
        from gridiron.report import ReportFormatter
        from gridiron.models import FullReport, N1Report, HealthStatus

        report = FullReport(
            project_path="/test",
            n1_report=N1Report(total_packages=5, passing_packages=4),
            overall_status=HealthStatus.NORMAL,
        )
        formatter = ReportFormatter()
        output = formatter.format_full_report(report, fmt="text")
        assert "GRIDIRON" in output
        assert "80.0%" in output

    def test_json_format(self):
        from gridiron.report import ReportFormatter
        from gridiron.models import FullReport, N1Report, HealthStatus

        report = FullReport(
            project_path="/test",
            n1_report=N1Report(total_packages=5, passing_packages=4),
            overall_status=HealthStatus.NORMAL,
        )
        formatter = ReportFormatter()
        output = formatter.format_full_report(report, fmt="json")
        import json
        data = json.loads(output)
        assert data["n1"]["compliance_score"] == 80.0
