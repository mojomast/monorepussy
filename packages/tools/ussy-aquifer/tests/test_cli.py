"""Tests for the CLI module."""

import json
import os
import tempfile

import pytest

from aquifer.cli import main, build_parser
from aquifer.topology import create_sample_topology, save_topology


@pytest.fixture
def sample_topo_path():
    """Create a temporary sample topology file."""
    topo = create_sample_topology()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        save_topology(topo, f.name)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def minimal_topo_path():
    """Create a minimal topology file."""
    data = {
        "name": "minimal",
        "services": [
            {"name": "src", "hydraulic_conductivity": 100.0, "queue_depth": 10,
             "processing_latency": 0.1, "is_recharge": True, "grid_x": 0, "grid_y": 0},
            {"name": "snk", "hydraulic_conductivity": 50.0, "queue_depth": 5,
             "processing_latency": 0.05, "is_discharge": True, "grid_x": 1, "grid_y": 0},
        ],
        "connections": [
            {"source": "src", "target": "snk", "connection_type": "porous"}
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    yield path
    os.unlink(path)


class TestBuildParser:
    """Test argument parser construction."""

    def test_parser_has_version(self):
        parser = build_parser()
        # Should not raise
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0

    def test_analyze_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["analyze", "topo.json"])
        assert args.command == "analyze"
        assert args.topology == "topo.json"

    def test_contour_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["contour", "topo.json"])
        assert args.command == "contour"

    def test_whatif_drill(self):
        parser = build_parser()
        args = parser.parse_args(["whatif", "topo.json", "--drill", "service1"])
        assert args.command == "whatif"
        assert args.drill == "service1"

    def test_predict_duration(self):
        parser = build_parser()
        args = parser.parse_args(["predict", "topo.json", "--duration", "2.5"])
        assert args.command == "predict"
        assert args.duration == 2.5

    def test_predict_load(self):
        parser = build_parser()
        args = parser.parse_args(["predict", "topo.json", "--load", "2.0"])
        assert args.load == 2.0

    def test_no_command_returns_none(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.command is None


class TestCLICommands:
    """Test CLI command execution."""

    def test_analyze_command(self, minimal_topo_path, capsys):
        result = main(["analyze", minimal_topo_path])
        assert result == 0
        captured = capsys.readouterr()
        assert "Flow Analysis" in captured.out

    def test_contour_command(self, minimal_topo_path, capsys):
        result = main(["contour", minimal_topo_path])
        assert result == 0
        captured = capsys.readouterr()
        assert "AQUIFER" in captured.out or "Hydraulic" in captured.out

    def test_whatif_drill_command(self, minimal_topo_path, capsys):
        result = main(["whatif", minimal_topo_path, "--drill", "snk"])
        assert result == 0
        captured = capsys.readouterr()
        assert "drill_well" in captured.out

    def test_whatif_fracture_command(self, minimal_topo_path, capsys):
        result = main(["whatif", minimal_topo_path, "--fracture", "src,snk"])
        assert result == 0
        captured = capsys.readouterr()
        assert "fracture" in captured.out.lower()

    def test_whatif_unconfine_command(self, minimal_topo_path, capsys):
        result = main(["whatif", minimal_topo_path, "--unconfine", "snk"])
        assert result == 0
        captured = capsys.readouterr()
        assert "rate limit" in captured.out.lower() or "confining" in captured.out.lower()

    def test_whatif_no_action(self, minimal_topo_path, capsys):
        result = main(["whatif", minimal_topo_path])
        assert result == 1

    def test_predict_command(self, minimal_topo_path, capsys):
        result = main(["predict", minimal_topo_path, "--duration", "0.5"])
        assert result == 0
        captured = capsys.readouterr()
        assert "System Prediction" in captured.out

    def test_no_command_shows_help(self, capsys):
        result = main([])
        assert result == 0

    def test_nonexistent_file(self, capsys):
        result = main(["analyze", "/nonexistent/file.json"])
        assert result == 1

    def test_invalid_json(self, capsys):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            path = f.name
        try:
            result = main(["analyze", path])
            assert result == 1
        finally:
            os.unlink(path)

    def test_sample_command(self, capsys):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            result = main(["sample", "--output", path])
            assert result == 0
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_analyze_with_sample_topology(self, sample_topo_path, capsys):
        result = main(["analyze", sample_topo_path])
        assert result == 0
        captured = capsys.readouterr()
        assert "Flow Analysis" in captured.out

    def test_predict_with_load(self, minimal_topo_path, capsys):
        result = main(["predict", minimal_topo_path, "--duration", "1", "--load", "2.0"])
        assert result == 0

    def test_whatif_with_replicas(self, minimal_topo_path, capsys):
        result = main(["whatif", minimal_topo_path, "--drill", "snk", "--replicas", "3"])
        assert result == 0
