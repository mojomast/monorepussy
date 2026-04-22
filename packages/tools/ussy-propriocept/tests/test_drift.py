"""Tests for proprioceptive drift detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ussy_propriocept.drift import detect_drift, render_report


class TestDetectDrift:
    def test_no_drift(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        schema = {
            "limbs": [
                {
                    "path": str(repo),
                    "type": "bare-directory",
                    "state": {},
                }
            ]
        }
        drifts = detect_drift(schema)
        assert drifts == []

    def test_phantom_limb(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing"
        schema = {
            "limbs": [
                {
                    "path": str(missing),
                    "type": "git-repo",
                    "state": {"head": "ref: refs/heads/main"},
                }
            ]
        }
        drifts = detect_drift(schema)
        assert len(drifts) == 1
        assert drifts[0]["type"] == "phantom_limb"
        assert drifts[0]["score"] == 1.0

    def test_branch_drift(self, tmp_path: Path) -> None:
        import subprocess

        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
        (repo / ".git" / "HEAD").write_text("ref: refs/heads/main")
        schema = {
            "limbs": [
                {
                    "path": str(repo),
                    "type": "git-repo",
                    "state": {"head": "ref: refs/heads/old-feature"},
                }
            ]
        }
        drifts = detect_drift(schema)
        assert len(drifts) == 1
        assert drifts[0]["type"] == "branch_drift"
        assert drifts[0]["perceived"] == "ref: refs/heads/old-feature"
        assert drifts[0]["actual"] == "ref: refs/heads/main"
        assert drifts[0]["score"] == 0.8

    def test_venv_drift(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        venv = repo / ".venv"
        venv.mkdir()
        schema = {
            "limbs": [
                {
                    "path": str(repo),
                    "type": "bare-directory",
                    "state": {"venv": str(venv)},
                }
            ]
        }
        # venv exists — no drift
        assert detect_drift(schema) == []
        # remove venv
        venv.rmdir()
        drifts = detect_drift(schema)
        assert len(drifts) == 1
        assert drifts[0]["type"] == "venv_drift"
        assert drifts[0]["score"] == 0.6

    def test_env_drift(self, tmp_path: Path) -> None:
        schema = {"limbs": []}
        env = {"VIRTUAL_ENV": str(tmp_path / "deleted_env")}
        drifts = detect_drift(schema, env=env)
        assert len(drifts) == 1
        assert drifts[0]["type"] == "env_drift"
        assert drifts[0]["score"] == 0.7

    def test_no_env_drift_when_valid(self, tmp_path: Path) -> None:
        env_dir = tmp_path / "env"
        env_dir.mkdir()
        schema = {"limbs": []}
        env = {"VIRTUAL_ENV": str(env_dir)}
        drifts = detect_drift(schema, env=env)
        assert all(d["type"] != "env_drift" for d in drifts)

    def test_multiple_drifts(self, tmp_path: Path) -> None:
        import subprocess

        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
        venv = repo / ".venv"
        venv.mkdir()
        schema = {
            "limbs": [
                {
                    "path": str(repo),
                    "type": "git-repo",
                    "state": {
                        "head": "ref: refs/heads/old",
                        "venv": str(venv),
                    },
                }
            ]
        }
        # Change HEAD and delete venv
        (repo / ".git" / "HEAD").write_text("ref: refs/heads/new")
        venv.rmdir()
        env = {"VIRTUAL_ENV": str(tmp_path / "ghost")}
        drifts = detect_drift(schema, env=env)
        types = [d["type"] for d in drifts]
        assert "branch_drift" in types
        assert "venv_drift" in types
        assert "env_drift" in types


class TestRenderReport:
    def test_render_empty(self) -> None:
        text = render_report([])
        assert "No drift detected" in text

    def test_render_with_drifts(self) -> None:
        drifts = [
            {
                "limb": "/tmp/repo",
                "type": "branch_drift",
                "perceived": "old",
                "actual": "new",
                "score": 0.8,
            }
        ]
        text = render_report(drifts)
        assert "branch_drift" in text
        assert "/tmp/repo" in text

    def test_render_threshold(self) -> None:
        drifts = [
            {
                "limb": "/tmp/repo",
                "type": "venv_drift",
                "perceived": "venv",
                "actual": "deleted",
                "score": 0.6,
            },
            {
                "limb": "/tmp/repo2",
                "type": "branch_drift",
                "perceived": "old",
                "actual": "new",
                "score": 0.8,
            },
        ]
        text = render_report(drifts, threshold=0.7)
        assert "branch_drift" in text
        assert "venv_drift" not in text
