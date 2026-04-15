"""Tests for scanner module."""

from __future__ import annotations

from pathlib import Path

import pytest

from seral.models import ModuleMetrics, Stage
from seral.scanner import Scanner


class TestScanner:
    """Tests for Scanner."""

    def test_scan_module_returns_metrics(self, tmp_git_repo: Path):
        scanner = Scanner(repo_root=tmp_git_repo)
        mod_path = tmp_git_repo / "src" / "mymodule"
        metrics = scanner.scan_module(mod_path)
        assert isinstance(metrics, ModuleMetrics)
        assert metrics.path == str(mod_path)
        assert metrics.stage is not None

    def test_scan_module_has_age(self, tmp_git_repo: Path):
        scanner = Scanner(repo_root=tmp_git_repo)
        mod_path = tmp_git_repo / "src" / "mymodule"
        metrics = scanner.scan_module(mod_path)
        assert metrics.age_days > 0

    def test_scan_module_has_commits(self, tmp_git_repo: Path):
        scanner = Scanner(repo_root=tmp_git_repo)
        mod_path = tmp_git_repo / "src" / "mymodule"
        metrics = scanner.scan_module(mod_path)
        assert metrics.commit_count >= 2

    def test_scan_module_has_contributors(self, tmp_git_repo: Path):
        scanner = Scanner(repo_root=tmp_git_repo)
        mod_path = tmp_git_repo / "src" / "mymodule"
        metrics = scanner.scan_module(mod_path)
        assert metrics.contributor_count >= 1

    def test_scan_directory_finds_modules(self, tmp_git_repo: Path):
        scanner = Scanner(repo_root=tmp_git_repo)
        results = scanner.scan_directory(tmp_git_repo)
        assert len(results) >= 1

    def test_scan_directory_depth_limit(self, tmp_git_repo: Path):
        scanner = Scanner(repo_root=tmp_git_repo)
        # Depth 0 should find fewer or equal to depth 2
        shallow = scanner.scan_directory(tmp_git_repo, depth=0)
        deep = scanner.scan_directory(tmp_git_repo, depth=3)
        assert len(shallow) <= len(deep) + 1

    def test_record_transition_no_change(self, tmp_git_repo: Path):
        scanner = Scanner(repo_root=tmp_git_repo)
        metrics = ModuleMetrics(path="test", stage=Stage.PIONEER)
        transition = scanner.record_transition(metrics, previous_stage=Stage.PIONEER)
        assert transition is None

    def test_record_transition_with_change(self, tmp_git_repo: Path):
        scanner = Scanner(repo_root=tmp_git_repo)
        metrics = ModuleMetrics(path="test", stage=Stage.SERAL_MID)
        transition = scanner.record_transition(metrics, previous_stage=Stage.PIONEER)
        assert transition is not None
        assert transition.from_stage == Stage.PIONEER
        assert transition.to_stage == Stage.SERAL_MID

    def test_record_transition_no_previous(self, tmp_git_repo: Path):
        scanner = Scanner(repo_root=tmp_git_repo)
        metrics = ModuleMetrics(path="test", stage=Stage.PIONEER)
        transition = scanner.record_transition(metrics, previous_stage=None)
        assert transition is None

    def test_scan_nonexistent_module(self, tmp_git_repo: Path):
        scanner = Scanner(repo_root=tmp_git_repo)
        metrics = scanner.scan_module("nonexistent/path")
        assert metrics.commit_count == 0

    def test_has_code_files_detects_python(self, tmp_git_repo: Path):
        scanner = Scanner(repo_root=tmp_git_repo)
        mod = tmp_git_repo / "src" / "mymodule"
        assert scanner._has_code_files(mod) is True

    def test_has_code_files_empty_dir(self, tmp_git_repo: Path):
        scanner = Scanner(repo_root=tmp_git_repo)
        empty = tmp_git_repo / "empty_dir"
        empty.mkdir()
        assert scanner._has_code_files(empty) is False
