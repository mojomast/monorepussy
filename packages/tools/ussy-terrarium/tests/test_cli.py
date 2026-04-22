"""Tests for the Click-based CLI interface."""

import os
import tempfile

from click.testing import CliRunner

from terrarium.cli import cli, main


runner = CliRunner()


class TestMainCLI:
    """Tests for the main CLI entry point."""

    def test_no_args_returns_zero(self):
        result = main([])
        assert result == 0

    def test_health_on_temp_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = os.path.join(tmpdir, "src")
            os.makedirs(src_dir)
            with open(os.path.join(src_dir, "main.py"), "w") as f:
                f.write("def main():\n    pass\n")

            result = main(["health", tmpdir])
            assert result == 0

    def test_watch_on_temp_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = os.path.join(tmpdir, "src")
            os.makedirs(src_dir)
            with open(os.path.join(src_dir, "main.py"), "w") as f:
                f.write("def main():\n    pass\n")

            result = main(["watch", tmpdir])
            assert result == 0

    def test_snapshot_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = os.path.join(tmpdir, "src")
            os.makedirs(src_dir)
            with open(os.path.join(src_dir, "main.py"), "w") as f:
                f.write("def main():\n    pass\n")

            result = main(["snapshot", "--format", "text", tmpdir])
            assert result == 0

    def test_snapshot_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = os.path.join(tmpdir, "src")
            os.makedirs(src_dir)
            with open(os.path.join(src_dir, "main.py"), "w") as f:
                f.write("def main():\n    pass\n")

            output_path = os.path.join(tmpdir, "report.txt")
            result = main(
                ["snapshot", "--format", "text", "--output", output_path, tmpdir]
            )
            assert result == 0
            assert os.path.exists(output_path)

    def test_diagnose_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "module.py")
            with open(filepath, "w") as f:
                f.write("def func():\n    if True:\n        pass\n")

            result = main(["diagnose", filepath])
            assert result == 0

    def test_diagnose_nonexistent(self):
        result = main(["diagnose", "/nonexistent/file.py"])
        assert result == 1

    def test_health_nonexistent_dir(self):
        result = main(["health", "/nonexistent/dir"])
        assert result == 1

    def test_version(self):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "terrarium" in result.output


class TestClickCommands:
    """Tests for new Click-specific commands."""

    def test_dashboard_stub_mode(self):
        result = runner.invoke(cli, ["dashboard"])
        assert result.exit_code == 0
        assert "Terrarium Ecosystem Dashboard" in result.output

    def test_export_json(self):
        result = runner.invoke(cli, ["export", "--format", "json"])
        assert result.exit_code == 0
        assert "health" in result.output

    def test_export_csv(self):
        result = runner.invoke(cli, ["export", "--format", "csv"])
        assert result.exit_code == 0
        assert "dimension" in result.output

    def test_watch_live_help(self):
        result = runner.invoke(cli, ["watch-live", "--help"])
        assert result.exit_code == 0
        assert "interval" in result.output
