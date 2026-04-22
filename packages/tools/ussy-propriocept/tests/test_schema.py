"""Tests for the body schema builder."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from propriocept.schema import build_schema, load_schema, scan_limb


class TestScanLimb:
    def test_scan_limb_bare_directory(self, tmp_path: Path) -> None:
        limb_dir = tmp_path / "bare"
        limb_dir.mkdir()
        limb = scan_limb(limb_dir)
        assert limb["path"] == str(limb_dir)
        assert limb["type"] == "bare-directory"
        assert limb["state"] == {}

    def test_scan_limb_git_clean(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
        (repo / "file.txt").write_text("hello")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-m", "init"],
            check=True,
            capture_output=True,
        )
        limb = scan_limb(repo)
        assert limb["type"] == "git-repo"
        assert "head" in limb["state"]
        assert limb["state"]["dirty"] is False

    def test_scan_limb_git_dirty(self, tmp_path: Path) -> None:
        repo = tmp_path / "dirty-repo"
        repo.mkdir()
        subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
        (repo / "dirty.txt").write_text("dirty")
        limb = scan_limb(repo)
        assert limb["type"] == "git-repo"
        assert limb["state"]["dirty"] is True

    def test_scan_limb_with_venv(self, tmp_path: Path) -> None:
        repo = tmp_path / "project"
        repo.mkdir()
        (repo / ".venv").mkdir()
        limb = scan_limb(repo)
        assert limb["state"].get("venv") == str(repo / ".venv")

    def test_scan_limb_multiple_venvs(self, tmp_path: Path) -> None:
        repo = tmp_path / "project"
        repo.mkdir()
        (repo / "venv").mkdir()
        (repo / ".venv").mkdir()
        limb = scan_limb(repo)
        # First match wins
        assert limb["state"].get("venv") == str(repo / "venv")


class TestBuildSchema:
    def test_build_schema_five_limbs(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        # Create 3 git repos
        for name in ("repo-a", "repo-b", "repo-c"):
            repo = root / name
            repo.mkdir()
            subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
        # Make repo-c dirty
        (root / "repo-c" / "x.txt").write_text("x")
        # Make repo-b have .venv
        (root / "repo-b" / ".venv").mkdir()
        # Create 2 bare directories
        for name in ("docs", "assets"):
            (root / name).mkdir()
        schema = build_schema(root)
        assert len(schema["limbs"]) == 5
        types = {l["type"] for l in schema["limbs"]}
        assert types == {"git-repo", "bare-directory"}
        dirty = [l for l in schema["limbs"] if l["state"].get("dirty")]
        assert len(dirty) == 1
        assert Path(dirty[0]["path"]).name == "repo-c"
        venvs = [l for l in schema["limbs"] if "venv" in l["state"]]
        assert len(venvs) == 1
        assert Path(venvs[0]["path"]).name == "repo-b"

    def test_build_schema_empty_root(self, tmp_path: Path) -> None:
        root = tmp_path / "empty"
        root.mkdir()
        schema = build_schema(root)
        assert schema["limbs"] == []
        assert schema["root"] == str(root)

    def test_build_schema_persists(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / "foo").mkdir()
        output = tmp_path / "schema.json"
        schema = build_schema(root, output)
        assert output.exists()
        loaded = json.loads(output.read_text())
        assert loaded == schema

    def test_build_schema_skips_hidden(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / ".hidden").mkdir()
        (root / "visible").mkdir()
        schema = build_schema(root)
        names = [Path(l["path"]).name for l in schema["limbs"]]
        assert ".hidden" not in names
        assert "visible" in names

    def test_build_schema_not_a_directory(self, tmp_path: Path) -> None:
        output = tmp_path / "schema.json"
        schema = build_schema(tmp_path / "nonexistent", output)
        assert schema["limbs"] == []


class TestLoadSchema:
    def test_load_schema_roundtrip(self, tmp_path: Path) -> None:
        data = {"limbs": [], "root": "/tmp"}
        path = tmp_path / "schema.json"
        path.write_text(json.dumps(data))
        loaded = load_schema(path)
        assert loaded == data

    def test_load_schema_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_schema(tmp_path / "missing.json")
