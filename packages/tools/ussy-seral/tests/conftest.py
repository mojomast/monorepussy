"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary git repository with some commits."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo, capture_output=True,
    )

    # Create some files
    (repo / "README.md").write_text("# Test Project\n")
    (repo / "main.py").write_text("def main():\n    print('hello')\n")

    # Create a module directory
    mod_dir = repo / "src" / "mymodule"
    mod_dir.mkdir(parents=True)
    (mod_dir / "__init__.py").write_text("")
    (mod_dir / "core.py").write_text("def process():\n    return True\n")

    # Create a test directory
    test_dir = repo / "tests"
    test_dir.mkdir()
    (test_dir / "test_core.py").write_text("def test_process():\n    assert True\n")

    # Commit everything
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = "2024-01-01T00:00:00+0000"
    env["GIT_COMMITTER_DATE"] = "2024-01-01T00:00:00+0000"
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo, capture_output=True, env=env,
    )

    # Add more commits with different dates
    (mod_dir / "utils.py").write_text("def helper():\n    return 42\n")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    env["GIT_AUTHOR_DATE"] = "2024-06-01T00:00:00+0000"
    env["GIT_COMMITTER_DATE"] = "2024-06-01T00:00:00+0000"
    subprocess.run(
        ["git", "commit", "-m", "Add utils"],
        cwd=repo, capture_output=True, env=env,
    )

    # Add another commit
    (mod_dir / "core.py").write_text("def process():\n    return False\n")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    env["GIT_AUTHOR_DATE"] = "2025-01-01T00:00:00+0000"
    env["GIT_COMMITTER_DATE"] = "2025-01-01T00:00:00+0000"
    subprocess.run(
        ["git", "commit", "-m", "Update core"],
        cwd=repo, capture_output=True, env=env,
    )

    yield repo


@pytest.fixture
def tmp_git_repo_with_contributors(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a repo with multiple contributors."""
    repo = tmp_path / "multi_repo"
    repo.mkdir()

    subprocess.run(["git", "init"], cwd=repo, capture_output=True)

    # Contributor 1
    subprocess.run(
        ["git", "config", "user.email", "alice@example.com"],
        cwd=repo, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Alice"],
        cwd=repo, capture_output=True,
    )

    mod = repo / "src" / "payments"
    mod.mkdir(parents=True)
    (mod / "__init__.py").write_text("")
    (mod / "stripe.py").write_text("def charge():\n    pass\n")
    (mod / "test_stripe.py").write_text("def test_charge():\n    pass\n")

    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = "2023-01-01T00:00:00+0000"
    env["GIT_COMMITTER_DATE"] = "2023-01-01T00:00:00+0000"
    subprocess.run(
        ["git", "commit", "-m", "Add payments"],
        cwd=repo, capture_output=True, env=env,
    )

    # Contributor 2
    subprocess.run(
        ["git", "config", "user.email", "bob@example.com"],
        cwd=repo, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Bob"],
        cwd=repo, capture_output=True,
    )
    (mod / "paypal.py").write_text("def pay():\n    pass\n")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    env["GIT_AUTHOR_DATE"] = "2023-06-01T00:00:00+0000"
    env["GIT_COMMITTER_DATE"] = "2023-06-01T00:00:00+0000"
    subprocess.run(
        ["git", "commit", "-m", "Add paypal"],
        cwd=repo, capture_output=True, env=env,
    )

    # Contributor 3
    subprocess.run(
        ["git", "config", "user.email", "carol@example.com"],
        cwd=repo, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Carol"],
        cwd=repo, capture_output=True,
    )
    (mod / "stripe.py").write_text("def charge(amount):\n    return amount\n")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    env["GIT_AUTHOR_DATE"] = "2024-01-01T00:00:00+0000"
    env["GIT_COMMITTER_DATE"] = "2024-01-01T00:00:00+0000"
    subprocess.run(
        ["git", "commit", "-m", "Update stripe"],
        cwd=repo, capture_output=True, env=env,
    )

    yield repo


@pytest.fixture
def seral_config_dir(tmp_path: Path) -> Path:
    """Create a .seral/ directory with default config."""
    from ussy_seral.config import SeralConfig

    config = SeralConfig(tmp_path)
    config.init()
    return tmp_path


@pytest.fixture
def sample_metrics() -> dict:
    """Sample module metrics for testing."""
    return {
        "pioneer": {
            "path": "src/experimental/new_feature",
            "age_days": 14,
            "commit_count": 5,
            "contributor_count": 1,
            "churn_rate": 150.0,
            "test_coverage": 0.0,
            "dependent_count": 0,
            "file_count": 3,
            "file_type_diversity": 1,
            "deletion_ratio": 0.0,
            "contributor_spike": 0.0,
            "churn_spike": 0.0,
            "breaking_change_count": 0,
        },
        "seral_mid": {
            "path": "src/payments/stripe",
            "age_days": 240,
            "commit_count": 89,
            "contributor_count": 4,
            "churn_rate": 45.0,
            "test_coverage": 0.67,
            "dependent_count": 3,
            "file_count": 12,
            "file_type_diversity": 3,
            "deletion_ratio": 0.0,
            "contributor_spike": 0.0,
            "churn_spike": 0.0,
            "breaking_change_count": 1,
        },
        "climax": {
            "path": "src/auth/oauth2",
            "age_days": 1095,
            "commit_count": 412,
            "contributor_count": 11,
            "churn_rate": 3.0,
            "test_coverage": 0.94,
            "dependent_count": 23,
            "file_count": 28,
            "file_type_diversity": 5,
            "deletion_ratio": 0.0,
            "contributor_spike": 0.0,
            "churn_spike": 0.0,
            "breaking_change_count": 0,
        },
        "disturbed": {
            "path": "src/legacy/soap_api",
            "age_days": 2555,
            "commit_count": 300,
            "contributor_count": 8,
            "churn_rate": 5.0,
            "test_coverage": 0.85,
            "dependent_count": 15,
            "file_count": 10,
            "file_type_diversity": 4,
            "deletion_ratio": 0.6,
            "contributor_spike": 0.0,
            "churn_spike": 0.0,
            "breaking_change_count": 0,
        },
    }
