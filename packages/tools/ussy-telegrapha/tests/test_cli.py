"""Tests for the CLI module."""

import json
import pytest
from pathlib import Path

from ussy_telegrapha.cli import main, build_parser


class TestBuildParser:
    """Tests for argument parser construction."""

    def test_parser_creates(self):
        parser = build_parser()
        assert parser is not None

    def test_version(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0


class TestAttenuationCLI:
    """Tests for the attenuation subcommand."""

    def test_basic_route(self):
        result = main([
            "attenuation",
            "order->payment->ledger",
            "--degradations", "0.01,0.02,0.03",
        ])
        assert result == 0

    def test_with_threshold(self):
        result = main([
            "attenuation",
            "a->b->c",
            "--degradations", "0.05,0.05,0.05",
            "--threshold", "0.90",
        ])
        assert result == 0

    def test_json_output(self, capsys):
        result = main([
            "attenuation",
            "a->b",
            "--degradations", "0.01,0.02",
            "--json",
        ])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "fidelity" in data
        assert "hops" in data

    def test_with_topology(self, sample_topology_json):
        result = main([
            "attenuation",
            "order-to-ledger",
            "--topology", str(sample_topology_json),
        ])
        assert result == 0


class TestRelayChainCLI:
    """Tests for the relay-chain subcommand."""

    def test_basic_route(self):
        result = main([
            "relay-chain",
            "gw->auth->svc",
            "--reliabilities", "0.9999,0.9995,0.9998",
            "--sla", "99.9",
        ])
        assert result == 0

    def test_json_output(self, capsys):
        result = main([
            "relay-chain",
            "a->b",
            "--reliabilities", "0.999,0.999",
            "--sla", "99.9",
            "--json",
        ])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "meets_sla" in data


class TestCapacityCLI:
    """Tests for the capacity subcommand."""

    def test_basic(self):
        result = main([
            "capacity",
            "--bandwidth", "500",
            "--signal", "420",
            "--noise", "80",
        ])
        assert result == 0

    def test_json_output(self, capsys):
        result = main([
            "capacity",
            "--bandwidth", "500",
            "--signal", "420",
            "--noise", "80",
            "--json",
        ])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "theoretical_ceiling" in data

    def test_with_workers(self):
        result = main([
            "capacity",
            "--bandwidth", "500",
            "--signal", "420",
            "--noise", "80",
            "--workers", "50",
            "--utilization", "0.6",
        ])
        assert result == 0


class TestPrecedenceCLI:
    """Tests for the precedence subcommand."""

    def test_default_classes(self):
        result = main(["precedence"])
        assert result == 0

    def test_json_output(self, capsys):
        result = main(["precedence", "--json"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "classes" in data

    def test_with_config(self, sample_precedence_json):
        result = main([
            "precedence",
            "--config", str(sample_precedence_json),
        ])
        assert result == 0

    def test_missing_config_file(self):
        result = main([
            "precedence",
            "--config", "/nonexistent/file.json",
        ])
        assert result == 1


class TestHammingCLI:
    """Tests for the hamming subcommand."""

    def test_basic(self):
        result = main([
            "hamming",
            "--error-rate", "0.03",
            "--hops", "6",
        ])
        assert result == 0

    def test_json_output(self, capsys):
        result = main([
            "hamming",
            "--error-rate", "0.03",
            "--hops", "6",
            "--json",
        ])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "preferred" in data

    def test_with_drift(self):
        result = main([
            "hamming",
            "--error-rate", "0.03",
            "--hops", "6",
            "--drift", "2",
        ])
        assert result == 0


class TestDLOCLI:
    """Tests for the dlo subcommand."""

    def test_with_dlq_file(self, sample_dlq_json):
        result = main([
            "dlo",
            "--dlq", str(sample_dlq_json),
            "--accumulation", "47",
            "--resolution", "12",
        ])
        assert result == 0

    def test_json_output(self, sample_dlq_json, capsys):
        result = main([
            "dlo",
            "--dlq", str(sample_dlq_json),
            "--accumulation", "47",
            "--resolution", "12",
            "--json",
        ])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "health_score" in data

    def test_no_dlq_file(self):
        result = main(["dlo"])
        assert result == 1

    def test_missing_dlq_file(self):
        result = main(["dlo", "--dlq", "/nonexistent/file.json"])
        assert result == 1

    def test_dlo_json_error_flag(self, capsys):
        """Ensure --json outputs valid JSON on error paths."""
        result = main(["dlo", "--json"])
        assert result == 1
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "error" in data


class TestDashboardCLI:
    """Tests for the dashboard subcommand."""

    def test_basic(self, sample_topology_json):
        result = main([
            "dashboard",
            str(sample_topology_json),
        ])
        assert result == 0

    def test_json_output(self, sample_topology_json, capsys):
        result = main([
            "dashboard",
            str(sample_topology_json),
            "--json",
        ])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "topology" in data
        assert "routes" in data
        assert "capacity" in data
        assert "hamming" in data

    def test_with_dlq(self, sample_topology_json, sample_dlq_json):
        result = main([
            "dashboard",
            str(sample_topology_json),
            "--dlq", str(sample_dlq_json),
            "--dlq-accumulation", "47",
            "--dlq-resolution", "12",
        ])
        assert result == 0


class TestNoCommand:
    """Tests for no subcommand."""

    def test_no_command_returns_zero(self):
        result = main([])
        assert result == 0
