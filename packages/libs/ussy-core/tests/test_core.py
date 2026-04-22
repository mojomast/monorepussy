"""Tests for ussy_core."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import pytest

from ussy_core import (
    find_config_file,
    get_logger,
    get_project_root,
    safe_path,
    version_tuple,
)


class TestFindConfigFile:
    def test_finds_pyproject_toml(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "pyproject.toml"
            target.write_text("")
            found = find_config_file(td)
            assert found == target

    def test_searches_upward(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "setup.cfg").write_text("")
            nested = root / "a" / "b"
            nested.mkdir(parents=True)
            found = find_config_file(nested)
            assert found == root / "setup.cfg"

    def test_returns_none_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assert find_config_file(td, ("not-real.cfg",)) is None


class TestGetLogger:
    def test_returns_logger(self) -> None:
        logger = get_logger("ussy_test")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "ussy_test"

    def test_handler_attached(self) -> None:
        logger = get_logger("ussy_test_handler")
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)


class TestGetProjectRoot:
    def test_finds_git(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            assert get_project_root(start=root) == root

    def test_finds_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text("")
            assert get_project_root(start=root) == root

    def test_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assert get_project_root(start=td, marker=("nope.txt",)) is None


class TestSafePath:
    def test_builds_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = safe_path("src", "foo.py", base=td)
            assert p == Path(td).resolve() / "src" / "foo.py"

    def test_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(FileNotFoundError):
                safe_path("nope", base=td, must_exist=True)

    def test_traversal_guard(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(ValueError):
                safe_path("..", "etc", base=td)


class TestVersionTuple:
    def test_simple(self) -> None:
        assert version_tuple("1.2.3") == (1, 2, 3)

    def test_prerelease(self) -> None:
        assert version_tuple("2.0a1") == (2, 0, 1)

    def test_dev(self) -> None:
        assert version_tuple("1.0.dev0") == (1, 0, 0)
