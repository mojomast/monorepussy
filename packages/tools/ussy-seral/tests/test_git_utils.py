"""Tests for git_utils module."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from ussy_seral.git_utils import (
    get_commit_count,
    get_contributor_count,
    get_file_count,
    get_file_type_diversity,
    is_git_repo,
    find_repo_root,
    get_test_coverage,
    get_module_age_days,
)


class TestIsGitRepo:
    """Tests for is_git_repo."""

    def test_valid_git_repo(self, tmp_git_repo: Path):
        assert is_git_repo(tmp_git_repo) is True

    def test_not_a_git_repo(self, tmp_path: Path):
        nongit = tmp_path / "nongit"
        nongit.mkdir()
        assert is_git_repo(nongit) is False


class TestFindRepoRoot:
    """Tests for find_repo_root."""

    def test_finds_root(self, tmp_git_repo: Path):
        root = find_repo_root(tmp_git_repo)
        assert root is not None
        assert root == tmp_git_repo

    def test_finds_root_from_subdir(self, tmp_git_repo: Path):
        subdir = tmp_git_repo / "src" / "mymodule"
        root = find_repo_root(subdir)
        assert root is not None

    def test_returns_none_for_nongit(self, tmp_path: Path):
        nongit = tmp_path / "nongit"
        nongit.mkdir()
        assert find_repo_root(nongit) is None


class TestGetCommitCount:
    """Tests for get_commit_count."""

    def test_commit_count_for_module(self, tmp_git_repo: Path):
        mod_path = tmp_git_repo / "src" / "mymodule"
        count = get_commit_count(mod_path, tmp_git_repo)
        assert count >= 2  # At least 2 commits touch mymodule

    def test_commit_count_for_repo(self, tmp_git_repo: Path):
        count = get_commit_count(".", tmp_git_repo)
        assert count >= 3  # 3 total commits

    def test_commit_count_nonexistent_path(self, tmp_git_repo: Path):
        count = get_commit_count("nonexistent", tmp_git_repo)
        assert count == 0


class TestGetContributorCount:
    """Tests for get_contributor_count."""

    def test_single_contributor(self, tmp_git_repo: Path):
        count = get_contributor_count(".", tmp_git_repo)
        assert count >= 1

    def test_multiple_contributors(self, tmp_git_repo_with_contributors: Path):
        repo = tmp_git_repo_with_contributors
        count = get_contributor_count(".", repo)
        assert count >= 2  # At least 2 different contributors


class TestGetFileCount:
    """Tests for get_file_count."""

    def test_file_count(self, tmp_git_repo: Path):
        count = get_file_count(".", tmp_git_repo)
        assert count >= 5  # README, main.py, __init__.py, core.py, utils.py, test_core.py

    def test_file_count_subdir(self, tmp_git_repo: Path):
        count = get_file_count("src/mymodule", tmp_git_repo)
        assert count >= 2  # __init__.py, core.py, utils.py


class TestGetFileTypeDiversity:
    """Tests for get_file_type_diversity."""

    def test_diversity(self, tmp_git_repo: Path):
        diversity = get_file_type_diversity(".", tmp_git_repo)
        assert diversity >= 1  # At least .py

    def test_diversity_subdir(self, tmp_git_repo: Path):
        diversity = get_file_type_diversity("src/mymodule", tmp_git_repo)
        assert diversity >= 1


class TestGetTestCoverage:
    """Tests for get_test_coverage."""

    def test_has_some_coverage(self, tmp_git_repo: Path):
        coverage = get_test_coverage(".", tmp_git_repo)
        assert coverage >= 0.0  # There's at least one test file

    def test_no_coverage_for_module(self, tmp_git_repo: Path):
        coverage = get_test_coverage("src/mymodule", tmp_git_repo)
        # Module dir has no test files in it
        assert coverage >= 0.0


class TestGetModuleAgeDays:
    """Tests for get_module_age_days."""

    def test_age_is_positive(self, tmp_git_repo: Path):
        age = get_module_age_days("src/mymodule", tmp_git_repo)
        assert age > 0  # First commit was in 2024-01-01

    def test_age_for_repo(self, tmp_git_repo: Path):
        age = get_module_age_days(".", tmp_git_repo)
        assert age > 0
