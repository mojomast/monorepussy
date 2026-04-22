"""Tests for the scanner module."""

from pathlib import Path

import pytest

from ussy_assay.scanner import _resolve_paths, _walk_py_files, read_source


class TestResolvePaths:
    def test_single_file(self, business_file):
        result = _resolve_paths(business_file)
        assert len(result) == 1
        assert result[0] == business_file

    def test_directory(self, fixtures_dir):
        result = _resolve_paths(fixtures_dir)
        assert len(result) >= 4  # at least 4 fixture files
        assert all(p.suffix == ".py" for p in result)

    def test_nonexistent_path(self):
        result = _resolve_paths("/nonexistent/path")
        assert result == []

    def test_non_py_file(self, tmp_path):
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("hello")
        result = _resolve_paths(txt_file)
        assert result == []

    def test_skips_hidden_dirs(self, tmp_path):
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "test.py").write_text("x = 1")
        (tmp_path / "main.py").write_text("y = 2")
        result = _resolve_paths(tmp_path)
        paths_str = [str(p) for p in result]
        assert any("main.py" in p for p in paths_str)
        assert not any(".hidden" in p for p in paths_str)

    def test_skips_pycache(self, tmp_path):
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "test.pyc").write_text("bytecode")
        (tmp_path / "app.py").write_text("x = 1")
        result = _resolve_paths(tmp_path)
        assert len(result) == 1


class TestReadSource:
    def test_read_existing_file(self, business_file):
        source = read_source(business_file)
        assert "calc_tax" in source

    def test_read_nonexistent_file(self):
        source = read_source(Path("/nonexistent/file.py"))
        assert source == ""

    def test_read_returns_string(self, business_file):
        source = read_source(business_file)
        assert isinstance(source, str)
