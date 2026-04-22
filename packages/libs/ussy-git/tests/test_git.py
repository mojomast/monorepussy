"""Tests for ussy_git."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from ussy_git import GitError, GitRepo, find_git_root, run_git


class TestFindGitRoot:
    def test_finds_git(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            assert find_git_root(root) == root

    def test_none_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assert find_git_root(td) is None


class TestRunGit:
    def test_version(self) -> None:
        result = run_git("--version")
        assert result.returncode == 0
        assert "git version" in result.stdout

    def test_failure_raises(self) -> None:
        with pytest.raises(GitError):
            run_git("not-a-real-command")

    def test_timeout(self) -> None:
        with pytest.raises(GitError) as exc_info:
            # Use a command that sleeps to ensure timeout is hit
            run_git(
                "-c",
                "core.quotepath=false",
                "log",
                "--all",
                "--format=%H",
                "--since=1970-01-01",
                timeout=0.0001,
            )
        assert "timed out" in str(exc_info.value)


class TestGitRepo:
    def _init_repo(self, path: Path) -> None:
        run_git("init", cwd=path)
        run_git("config", "user.email", "test@example.com", cwd=path)
        run_git("config", "user.name", "Test", cwd=path)

    def test_init_fails_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(GitError):
                GitRepo(td)

    def test_current_branch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_repo(root)
            # Need at least one commit for branch to resolve
            (root / "a.txt").write_text("hello")
            run_git("add", ".", cwd=root)
            run_git("commit", "-m", "init", cwd=root)
            repo = GitRepo(root)
            branch = repo.current_branch()
            assert branch in ("master", "main", "HEAD")

    def test_log(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_repo(root)
            (root / "a.txt").write_text("hello")
            run_git("add", ".", cwd=root)
            run_git("commit", "-m", "first", cwd=root)
            repo = GitRepo(root)
            commits = repo.log()
            assert len(commits) == 1
            assert commits[0].message == "first"

    def test_branches(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_repo(root)
            (root / "a.txt").write_text("hello")
            run_git("add", ".", cwd=root)
            run_git("commit", "-m", "init", cwd=root)
            repo = GitRepo(root)
            branches = repo.branches()
            assert any(b in ("master", "main", "HEAD") for b in branches)

    def test_reflog(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_repo(root)
            (root / "a.txt").write_text("hello")
            run_git("add", ".", cwd=root)
            run_git("commit", "-m", "first", cwd=root)
            repo = GitRepo(root)
            entries = repo.reflog()
            assert len(entries) >= 1
            assert "sha" in entries[0]
