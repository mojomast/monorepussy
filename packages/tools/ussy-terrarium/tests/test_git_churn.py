"""Tests for the git churn analysis module."""

import os
import subprocess
import tempfile
from datetime import datetime, timezone

import pytest

from terrarium.metrics.git_churn import (
    get_git_log,
    get_churn_for_file,
    get_all_file_churn,
)


@pytest.fixture
def git_repo():
    """Create a temporary git repository with some commits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmpdir, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmpdir, capture_output=True,
        )

        # Create files and commit
        readme = os.path.join(tmpdir, "README.md")
        with open(readme, "w") as f:
            f.write("# Test Project\n")
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmpdir, capture_output=True,
        )

        # Create a Python file
        main_py = os.path.join(tmpdir, "main.py")
        with open(main_py, "w") as f:
            f.write("def main():\n    pass\n")
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add main.py"],
            cwd=tmpdir, capture_output=True,
        )

        # Modify main.py
        with open(main_py, "w") as f:
            f.write("def main():\n    print('hello')\n")
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update main.py"],
            cwd=tmpdir, capture_output=True,
        )

        yield tmpdir


class TestGetGitLog:
    """Tests for git log retrieval."""

    def test_get_log_for_file(self, git_repo):
        """Get git log for a specific file."""
        filepath = os.path.join(git_repo, "main.py")
        entries = get_git_log(filepath)
        assert len(entries) >= 2
        assert "hash" in entries[0]
        assert "date" in entries[0]
        assert "author" in entries[0]

    def test_get_log_with_since(self, git_repo):
        """Git log with --since filter."""
        filepath = os.path.join(git_repo, "main.py")
        entries = get_git_log(filepath, since="1 year ago")
        assert isinstance(entries, list)

    def test_get_log_nonexistent_file(self, git_repo):
        """Non-existent file returns empty list."""
        filepath = os.path.join(git_repo, "nonexistent.py")
        entries = get_git_log(filepath)
        assert entries == []

    def test_log_dates_are_timezone_aware(self, git_repo):
        """Returned dates should be timezone-aware."""
        filepath = os.path.join(git_repo, "main.py")
        entries = get_git_log(filepath)
        if entries:
            assert entries[0]["date"].tzinfo is not None


class TestGetChurnForFile:
    """Tests for file-level churn calculation."""

    def test_churn_for_tracked_file(self, git_repo):
        """Calculate churn for a git-tracked file."""
        filepath = os.path.join(git_repo, "main.py")
        churn_rate, commit_count, age_days, days_since = get_churn_for_file(filepath)
        assert commit_count >= 2
        assert churn_rate > 0
        assert age_days >= 0

    def test_churn_for_untracked_file(self, git_repo):
        """Untracked file has no churn data."""
        filepath = os.path.join(git_repo, "new_file.py")
        with open(filepath, "w") as f:
            f.write("# new\n")
        churn_rate, commit_count, age_days, days_since = get_churn_for_file(filepath)
        assert commit_count == 0


class TestGetAllFileChurn:
    """Tests for project-wide churn analysis."""

    def test_get_all_churn(self, git_repo):
        """Get churn data for all tracked files."""
        churn_data = get_all_file_churn(git_repo)
        assert isinstance(churn_data, dict)
        # Should have at least README.md and main.py
        assert len(churn_data) >= 2

    def test_non_git_directory(self):
        """Non-git directory returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            churn_data = get_all_file_churn(tmpdir)
            assert churn_data == {}
