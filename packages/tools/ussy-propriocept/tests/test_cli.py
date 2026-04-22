"""Integration tests for the CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

CLI = [sys.executable, "-m", "propriocept"]
_SRC = str(Path(__file__).resolve().parents[1] / "src")
_ENV = {**os.environ, "PYTHONPATH": _SRC}


class TestSchemaCommand:
    def test_cli_schema_build(self, tmp_path: Path) -> None:
        root = tmp_path / "projects"
        root.mkdir()
        (root / "repo-a").mkdir()
        schema_path = tmp_path / "schema.json"
        result = subprocess.run(
            [*CLI, "schema", "--root", str(root), "--output", str(schema_path)],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 0
        assert schema_path.exists()
        data = json.loads(schema_path.read_text())
        assert len(data["limbs"]) == 1

    def test_cli_schema_default(self, tmp_path: Path) -> None:
        # Change cwd so default body_schema.json is inside tmp_path
        result = subprocess.run(
            [*CLI, "schema", "--root", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            env=_ENV,
        )
        assert result.returncode == 0
        assert (tmp_path / "body_schema.json").exists()


class TestSenseCommand:
    def test_cli_sense_ascii(self, tmp_path: Path) -> None:
        schema_path = tmp_path / "schema.json"
        schema_path.write_text(json.dumps({"limbs": [], "root": str(tmp_path)}))
        result = subprocess.run(
            [*CLI, "sense", "--schema", str(schema_path)],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 0
        assert "Soma Map" in result.stdout

    def test_cli_sense_json(self, tmp_path: Path) -> None:
        schema_path = tmp_path / "schema.json"
        schema_path.write_text(json.dumps({"limbs": [], "root": str(tmp_path)}))
        result = subprocess.run(
            [*CLI, "sense", "--schema", str(schema_path), "--format", "json"],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "limbs" in data

    def test_cli_sense_missing_schema(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [*CLI, "sense", "--schema", str(tmp_path / "nope.json")],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 1
        assert "not found" in result.stdout or "not found" in result.stderr


class TestKinesthesiaCommand:
    def test_cli_kinesthesia_ascii(self, tmp_path: Path) -> None:
        hist = tmp_path / "history"
        hist.write_text("cd /tmp\n")
        result = subprocess.run(
            [*CLI, "kinesthesia", "--history", str(hist)],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 0
        assert "velocity" in result.stdout

    def test_cli_kinesthesia_json(self, tmp_path: Path) -> None:
        hist = tmp_path / "history"
        hist.write_text("cd /tmp\n")
        result = subprocess.run(
            [*CLI, "kinesthesia", "--history", str(hist), "--format", "json"],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "velocity" in data


class TestMuscleMemoryCommand:
    def test_cli_muscle_memory_stdout(self, tmp_path: Path) -> None:
        hist = tmp_path / "history"
        hist.write_text("git pull\npytest\ngit push\n" * 10)
        result = subprocess.run(
            [*CLI, "muscle-memory", "--history", str(hist), "--min-freq", "5"],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 0
        assert "alias" in result.stdout

    def test_cli_muscle_memory_output_file(self, tmp_path: Path) -> None:
        hist = tmp_path / "history"
        hist.write_text("git pull\npytest\ngit push\n" * 10)
        out = tmp_path / "aliases.sh"
        result = subprocess.run(
            [*CLI, "muscle-memory", "--history", str(hist), "--min-freq", "5", "--output", str(out)],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 0
        assert out.exists()
        assert "alias" in out.read_text()

    def test_cli_muscle_memory_no_programs(self, tmp_path: Path) -> None:
        hist = tmp_path / "history"
        hist.write_text("ls\ncd /tmp\n")
        result = subprocess.run(
            [*CLI, "muscle-memory", "--history", str(hist), "--min-freq", "5"],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 0
        assert "No motor programs" in result.stdout


class TestDriftCommand:
    def test_cli_drift_json(self, tmp_path: Path) -> None:
        schema_path = tmp_path / "schema.json"
        schema_path.write_text(json.dumps({"limbs": [], "root": str(tmp_path)}))
        result = subprocess.run(
            [*CLI, "drift", "--schema", str(schema_path)],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_cli_drift_report(self, tmp_path: Path) -> None:
        schema_path = tmp_path / "schema.json"
        schema_path.write_text(json.dumps({"limbs": [], "root": str(tmp_path)}))
        result = subprocess.run(
            [*CLI, "drift", "--schema", str(schema_path), "--report"],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 0
        assert "Drift Report" in result.stdout

    def test_cli_drift_missing_schema(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [*CLI, "drift", "--schema", str(tmp_path / "nope.json")],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 1


class TestLimbCommand:
    def test_cli_limb_status(self, tmp_path: Path) -> None:
        limb = tmp_path / "limb"
        limb.mkdir()
        result = subprocess.run(
            [*CLI, "limb", "status", str(limb)],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["path"] == str(limb)

    def test_cli_limb_missing(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [*CLI, "limb", "status", str(tmp_path / "nope")],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 1


class TestHelp:
    def test_cli_help(self) -> None:
        result = subprocess.run(
            [*CLI, "--help"],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 0
        assert "schema" in result.stdout

    def test_cli_subcommand_help(self) -> None:
        result = subprocess.run(
            [*CLI, "schema", "--help"],
            capture_output=True,
            text=True,
            env=_ENV,
        )
        assert result.returncode == 0
        assert "--root" in result.stdout


class TestPerformance:
    def test_performance_baseline(self, tmp_path: Path) -> None:
        import time

        root = tmp_path / "workspace"
        root.mkdir()
        for i in range(50):
            repo = root / f"repo-{i}"
            repo.mkdir()
            subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
        schema_path = tmp_path / "schema.json"
        start = time.monotonic()
        subprocess.run(
            [*CLI, "schema", "--root", str(root), "--output", str(schema_path)],
            check=True,
            capture_output=True,
            env=_ENV,
        )
        subprocess.run(
            [*CLI, "sense", "--schema", str(schema_path)],
            check=True,
            capture_output=True,
            env=_ENV,
        )
        subprocess.run(
            [*CLI, "drift", "--schema", str(schema_path)],
            check=True,
            capture_output=True,
            env=_ENV,
        )
        elapsed = time.monotonic() - start
        assert elapsed < 2.0
