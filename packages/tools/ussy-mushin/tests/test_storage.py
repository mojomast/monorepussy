"""Tests for mushin.storage module."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ussy_mushin.storage import (
    MUSHIN_DIR,
    atomic_write_bytes,
    atomic_write_json,
    mushin_root,
    read_bytes,
    read_json,
    ts_now,
    ts_parse,
)


class TestMushinRoot:
    def test_creates_directory(self, tmp_path):
        root = mushin_root(tmp_path)
        assert root.exists()
        assert root.name == MUSHIN_DIR

    def test_idempotent(self, tmp_path):
        r1 = mushin_root(tmp_path)
        r2 = mushin_root(tmp_path)
        assert r1 == r2

    def test_resolves_path(self, tmp_path):
        root = mushin_root(tmp_path / "subdir")
        assert root.parent.name == "subdir"


class TestAtomicWriteJson:
    def test_writes_json(self, tmp_path):
        path = tmp_path / "test.json"
        atomic_write_json(path, {"key": "value"})
        data = json.loads(path.read_text())
        assert data == {"key": "value"}

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "a" / "b" / "test.json"
        atomic_write_json(path, {"x": 1})
        assert path.exists()

    def test_handles_datetime(self, tmp_path):
        path = tmp_path / "dt.json"
        dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        atomic_write_json(path, {"ts": dt})
        data = json.loads(path.read_text())
        assert "2025-01-01" in data["ts"]

    def test_handles_path(self, tmp_path):
        path = tmp_path / "p.json"
        atomic_write_json(path, {"p": Path("/foo/bar")})
        data = json.loads(path.read_text())
        assert data["p"] == "/foo/bar"

    def test_overwrites_existing(self, tmp_path):
        path = tmp_path / "ow.json"
        atomic_write_json(path, {"v": 1})
        atomic_write_json(path, {"v": 2})
        data = json.loads(path.read_text())
        assert data["v"] == 2

    def test_atomic_on_error(self, tmp_path):
        """If serialization fails, the original file (if any) is untouched."""
        path = tmp_path / "atomic.json"
        atomic_write_json(path, {"good": True})

        class Unserializable:
            pass

        with pytest.raises(TypeError):
            atomic_write_json(path, {"bad": Unserializable()})

        # Original data should still be intact
        data = json.loads(path.read_text())
        assert data == {"good": True}


class TestReadJson:
    def test_reads_existing(self, tmp_path):
        path = tmp_path / "r.json"
        path.write_text('{"a": 1}')
        assert read_json(path) == {"a": 1}

    def test_returns_none_for_missing(self, tmp_path):
        path = tmp_path / "missing.json"
        assert read_json(path) is None


class TestAtomicWriteBytes:
    def test_writes_binary(self, tmp_path):
        path = tmp_path / "bin.dat"
        atomic_write_bytes(path, b"\x00\x01\x02")
        assert path.read_bytes() == b"\x00\x01\x02"

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "a" / "b" / "bin.dat"
        atomic_write_bytes(path, b"hello")
        assert path.exists()


class TestReadBytes:
    def test_reads_existing(self, tmp_path):
        path = tmp_path / "b.dat"
        path.write_bytes(b"data")
        assert read_bytes(path) == b"data"

    def test_returns_none_for_missing(self, tmp_path):
        assert read_bytes(tmp_path / "nope.dat") is None


class TestTimestamps:
    def test_ts_now_is_utc(self):
        ts = ts_now()
        dt = ts_parse(ts)
        assert dt.tzinfo is not None

    def test_ts_now_roundtrip(self):
        ts = ts_now()
        dt = ts_parse(ts)
        assert dt.isoformat() == ts

    def test_ts_parse_explicit(self):
        s = "2025-06-15T10:30:00+00:00"
        dt = ts_parse(s)
        assert dt.year == 2025
        assert dt.month == 6
