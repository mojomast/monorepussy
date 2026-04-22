"""Tests for Cambium CLI module."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from ussy_cambium.cli import main

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestCLIVersion:
    """Tests for --version flag."""

    def test_version_flag(self):
        # Should not raise
        result = main(["--version"])
        assert result == 0


class TestCLIScan:
    """Tests for scan command."""

    def test_scan_directory(self):
        result = main(["scan", FIXTURES_DIR])
        assert result == 0

    def test_scan_json_output(self):
        # Capture stdout
        import io
        from unittest.mock import patch

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            result = main(["--json", "scan", FIXTURES_DIR])
        assert result == 0

    def test_scan_nonexistent(self):
        result = main(["scan", "/nonexistent/path"])
        assert result == 1


class TestCLICompatibility:
    """Tests for compatibility command."""

    def test_compatibility_named(self):
        result = main(["compatibility", "consumer", "provider"])
        assert result == 0

    def test_compatibility_json_output(self):
        import io
        from unittest.mock import patch

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            result = main(["--json", "compatibility", "consumer", "provider"])
        assert result == 0
        output = mock_stdout.getvalue()
        data = json.loads(output)
        assert "composite" in data

    def test_compatibility_from_files(self):
        consumer_path = os.path.join(FIXTURES_DIR, "consumer.py")
        provider_path = os.path.join(FIXTURES_DIR, "provider.py")
        result = main(["compatibility", consumer_path, provider_path])
        assert result == 0


class TestCLIAlignment:
    """Tests for alignment command."""

    def test_alignment_named(self):
        result = main(["alignment", "consumer", "provider"])
        assert result == 0

    def test_alignment_json_output(self):
        import io
        from unittest.mock import patch

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            result = main(["--json", "alignment", "consumer", "provider"])
        assert result == 0
        output = mock_stdout.getvalue()
        data = json.loads(output)
        assert "name_match" in data
        assert "signature_match" in data
        assert "semantic_match" in data

    def test_alignment_from_files(self):
        consumer_path = os.path.join(FIXTURES_DIR, "consumer.py")
        provider_path = os.path.join(FIXTURES_DIR, "provider.py")
        result = main(["alignment", consumer_path, provider_path])
        assert result == 0


class TestCLIDriftForecast:
    """Tests for drift-forecast command."""

    def test_basic_drift_forecast(self):
        result = main(["drift-forecast", "mylib"])
        assert result == 0

    def test_drift_forecast_doomed(self):
        result = main([
            "drift-forecast", "mylib",
            "--delta-behavior", "0.1",
            "--delta-contract", "0.1",
            "--delta-environment", "0.1",
        ])
        assert result == 0

    def test_drift_forecast_json(self):
        import io
        from unittest.mock import patch

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            result = main(["--json", "drift-forecast", "mylib"])
        assert result == 0
        output = mock_stdout.getvalue()
        data = json.loads(output)
        assert "analysis" in data
        assert "forecast" in data


class TestCLIBondTraj:
    """Tests for bond-traj command."""

    def test_basic_bond_traj(self):
        result = main(["bond-traj", "mylib"])
        assert result == 0

    def test_bond_traj_json(self):
        import io
        from unittest.mock import patch

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            result = main(["--json", "bond-traj", "mylib"])
        assert result == 0
        output = mock_stdout.getvalue()
        data = json.loads(output)
        assert "parameters" in data
        assert "trajectory" in data


class TestCLIDwarfing:
    """Tests for dwarfing command."""

    def test_dwarfing_directory(self):
        result = main(["dwarfing", FIXTURES_DIR])
        assert result == 0

    def test_dwarfing_json(self):
        import io
        from unittest.mock import patch

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            result = main(["--json", "dwarfing", FIXTURES_DIR])
        assert result == 0
        output = mock_stdout.getvalue()
        data = json.loads(output)
        assert "analysis" in data

    def test_dwarfing_nonexistent(self):
        result = main(["dwarfing", "/nonexistent/path"])
        assert result == 1


class TestCLIGCIHistory:
    """Tests for gci-history command."""

    def test_gci_history_no_data(self):
        import io
        from unittest.mock import patch

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            result = main(["gci-history", "nonexistent_dep"])
        assert result == 0


class TestCLINoCommand:
    """Tests for no command (help)."""

    def test_no_command_returns_zero(self):
        result = main([])
        assert result == 0
