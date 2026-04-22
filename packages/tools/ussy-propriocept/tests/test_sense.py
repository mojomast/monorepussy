"""Tests for the passive state sense module."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from propriocept.sense import render_ascii, sense, sense_processes


class TestSenseProcesses:
    def test_sense_processes_returns_list(self) -> None:
        procs = sense_processes()
        assert isinstance(procs, list)

    def test_sense_processes_entries_have_keys(self) -> None:
        procs = sense_processes()
        for p in procs:
            assert "pid" in p
            assert "cmd" in p
            assert "cwd" in p
            assert isinstance(p["pid"], int)

    def test_sense_processes_includes_self(self) -> None:
        procs = sense_processes()
        pids = [p["pid"] for p in procs]
        assert os.getpid() in pids


class TestSense:
    def test_sense_adds_active_pids(self, tmp_path: Path) -> None:
        schema = {
            "limbs": [
                {"path": str(tmp_path), "type": "bare-directory", "state": {}}
            ]
        }
        result = sense(schema)
        assert "active_pids" in result["limbs"][0]["state"]
        # The test process itself should be active if cwd is inside tmp_path,
        # but usually it isn't, so we just verify the key exists.

    def test_sense_filters_by_prefix(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        limb_a = root / "a"
        limb_a.mkdir()
        limb_b = root / "b"
        limb_b.mkdir()
        schema = {
            "limbs": [
                {"path": str(limb_a), "type": "bare-directory", "state": {}},
                {"path": str(limb_b), "type": "bare-directory", "state": {}},
            ]
        }
        result = sense(schema)
        for limb in result["limbs"]:
            # Our test cwd is not inside either limb, so no PIDs should match
            assert limb["state"].get("active_pids") == []

    def test_sense_with_background_proc(self, tmp_path: Path) -> None:
        limb = tmp_path / "server-limb"
        limb.mkdir()
        schema = {
            "limbs": [
                {"path": str(limb), "type": "bare-directory", "state": {}}
            ]
        }
        # Start a background Python process with cwd inside the limb
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            cwd=str(limb),
        )
        try:
            time.sleep(0.3)
            result = sense(schema)
            pids = result["limbs"][0]["state"]["active_pids"]
            assert proc.pid in pids
        finally:
            proc.terminate()
            proc.wait()
        # After termination, re-sense
        result2 = sense(schema)
        pids2 = result2["limbs"][0]["state"]["active_pids"]
        assert proc.pid not in pids2


class TestRenderAscii:
    def test_render_ascii_basic(self) -> None:
        schema = {
            "limbs": [
                {
                    "path": "/home/user/projects/api",
                    "type": "git-repo",
                    "state": {
                        "head": "ref: refs/heads/main",
                        "dirty": False,
                        "active_pids": [],
                    },
                },
                {
                    "path": "/home/user/projects/web",
                    "type": "bare-directory",
                    "state": {
                        "active_pids": [1234],
                    },
                },
            ]
        }
        text = render_ascii(schema)
        assert "api" in text
        assert "web" in text
        assert "active:1" in text
        assert "numb" in text

    def test_render_ascii_dirty(self) -> None:
        schema = {
            "limbs": [
                {
                    "path": "/home/user/projects/api",
                    "type": "git-repo",
                    "state": {
                        "head": "ref: refs/heads/main",
                        "dirty": True,
                        "active_pids": [],
                    },
                }
            ]
        }
        text = render_ascii(schema)
        assert "dirty" in text

    def test_render_ascii_empty(self) -> None:
        text = render_ascii({"limbs": []})
        assert "Soma Map" in text
