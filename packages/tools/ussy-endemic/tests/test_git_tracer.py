"""Tests for endemic.git_tracer module."""

import pytest
import os
import tempfile
import subprocess

from endemic.git_tracer import GitTracer
from endemic.models import TransmissionTree


def _git_available():
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


class TestGitTracer:
    def test_init_no_git(self):
        """GitTracer should handle non-git directories gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = GitTracer(tmpdir)
            assert tracer._git_available is False

    def test_get_log_no_git(self):
        """get_log should return empty list when git is not available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = GitTracer(tmpdir)
            logs = tracer.get_log()
            assert logs == []

    def test_get_blame_no_git(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = GitTracer(tmpdir)
            blames = tracer.get_blame("somefile.py")
            assert blames == []

    def test_trace_pattern_no_git(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = GitTracer(tmpdir)
            tree = tracer.trace_pattern("bare-except", r"except\s*:")
            assert isinstance(tree, TransmissionTree)
            assert len(tree.events) == 0

    def test_get_developer_stats(self):
        tracer = GitTracer(".")
        tree = TransmissionTree(pattern_name="test")
        stats = tracer.get_developer_stats(tree)
        assert stats == {}

    def test_git_repo_detection_from_non_git_dir(self):
        """GitTracer should correctly identify non-git directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = GitTracer(tmpdir)
            assert tracer._git_available is False

    def test_get_log_returns_list_type(self):
        """get_log always returns a list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = GitTracer(tmpdir)
            logs = tracer.get_log()
            assert isinstance(logs, list)

    def test_closest_by_path(self):
        result = GitTracer._closest_by_path(
            "src/api/routes.py",
            {"src/api/views.py", "src/data/model.py", "tests/test_api.py"},
        )
        assert result == "src/api/views.py"

    def test_closest_by_path_empty(self):
        result = GitTracer._closest_by_path("src/api.py", set())
        assert result == ""
