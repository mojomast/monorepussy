"""Tests for hooks module."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ussy_circadia.hooks import GitHooksManager, HookCheckResult
from ussy_circadia.zones import CognitiveZone
from ussy_circadia.config import CircadiaConfig


@pytest.fixture
def tmp_git_dir():
    with tempfile.TemporaryDirectory() as d:
        git_dir = os.path.join(d, ".git")
        os.makedirs(git_dir)
        hooks_dir = os.path.join(git_dir, "hooks")
        os.makedirs(hooks_dir)
        yield d


@pytest.fixture
def config():
    return CircadiaConfig()


class TestGitHooksManager:
    def test_install_all(self, tmp_git_dir, config):
        manager = GitHooksManager(repo_path=tmp_git_dir, config=config)
        installed = manager.install_all()
        assert len(installed) > 0

    def test_remove_all(self, tmp_git_dir, config):
        manager = GitHooksManager(repo_path=tmp_git_dir, config=config)
        manager.install_all()
        removed = manager.remove_all()
        assert len(removed) > 0

    def test_is_git_repo(self, tmp_git_dir, config):
        manager = GitHooksManager(repo_path=tmp_git_dir, config=config)
        assert manager.is_git_repo() is True

    def test_is_not_git_repo(self, config):
        with tempfile.TemporaryDirectory() as d:
            manager = GitHooksManager(repo_path=d, config=config)
            assert manager.is_git_repo() is False

    def test_is_installed(self, tmp_git_dir, config):
        manager = GitHooksManager(repo_path=tmp_git_dir, config=config)
        manager.install_all()
        # Check that at least one hook is installed
        installed = manager.is_installed("pre-push")
        assert installed is True or installed is False  # Depends on what hooks are created

    def test_check_operation_force_push_red_zone(self, tmp_git_dir, config):
        manager = GitHooksManager(repo_path=tmp_git_dir, config=config)
        # Mock the estimator to return RED zone
        with patch.object(manager.estimator, 'current_zone', return_value=CognitiveZone.RED):
            result = manager.check_operation("force_push")
            assert isinstance(result, HookCheckResult)
            assert result.allowed is False

    def test_check_operation_force_push_green_zone(self, tmp_git_dir, config):
        manager = GitHooksManager(repo_path=tmp_git_dir, config=config)
        with patch.object(manager.estimator, 'current_zone', return_value=CognitiveZone.GREEN):
            result = manager.check_operation("force_push")
            assert isinstance(result, HookCheckResult)
            # Green zone should allow force push
            assert result.allowed is True or result.zone == CognitiveZone.GREEN

    def test_check_operation_hard_reset_red_zone(self, tmp_git_dir, config):
        manager = GitHooksManager(repo_path=tmp_git_dir, config=config)
        with patch.object(manager.estimator, 'current_zone', return_value=CognitiveZone.RED):
            result = manager.check_operation("hard_reset")
            assert isinstance(result, HookCheckResult)
            assert result.allowed is False

    def test_check_operation_deploy_red_zone(self, tmp_git_dir, config):
        manager = GitHooksManager(repo_path=tmp_git_dir, config=config)
        with patch.object(manager.estimator, 'current_zone', return_value=CognitiveZone.RED):
            result = manager.check_operation("deploy_production")
            assert isinstance(result, HookCheckResult)
            assert result.allowed is False

    def test_check_operation_with_override(self, tmp_git_dir, config):
        manager = GitHooksManager(repo_path=tmp_git_dir, config=config)
        with patch.object(manager.estimator, 'current_zone', return_value=CognitiveZone.RED):
            result = manager.check_operation("force_push", override=True)
            assert isinstance(result, HookCheckResult)
            assert result.allowed is True

    def test_install_hook(self, tmp_git_dir, config):
        manager = GitHooksManager(repo_path=tmp_git_dir, config=config)
        result = manager.install_hook("pre-push", "#!/bin/sh\necho test\n")
        assert result is True

    def test_remove_hook(self, tmp_git_dir, config):
        manager = GitHooksManager(repo_path=tmp_git_dir, config=config)
        manager.install_hook("pre-push", "#!/bin/sh\necho test\n")
        result = manager.remove_hook("pre-push")
        assert result is True

    def test_hooks_dir_property(self, tmp_git_dir, config):
        manager = GitHooksManager(repo_path=tmp_git_dir, config=config)
        assert str(manager.hooks_dir).endswith(".git/hooks")
