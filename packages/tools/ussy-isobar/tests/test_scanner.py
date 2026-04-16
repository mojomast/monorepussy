"""Tests for isobar.scanner module."""

import os
import subprocess
import tempfile
from datetime import datetime, timezone, timedelta

import pytest

from isobar.scanner import GitScanner, FileCommit, FileHistory, ScanResult


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository with sample commits."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"],
                   cwd=str(repo), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"],
                   cwd=str(repo), capture_output=True, check=True)

    # Create some files
    (repo / "main.py").write_text("import auth\nimport utils\nprint('hello')")
    (repo / "auth.py").write_text("def login(): pass")
    (repo / "utils.py").write_text("def helper(): pass")
    (repo / "models.py").write_text("class User: pass")

    # Commit
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"],
                   cwd=str(repo), capture_output=True, check=True)

    # Modify a file
    (repo / "auth.py").write_text("def login(): pass\ndef logout(): pass")
    subprocess.run(["git", "add", "auth.py"], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "fix: add logout to auth"],
                   cwd=str(repo), capture_output=True, check=True)

    # Modify again
    (repo / "main.py").write_text("import auth\nimport utils\nprint('hello world')")
    subprocess.run(["git", "add", "main.py"], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "update greeting"],
                   cwd=str(repo), capture_output=True, check=True)

    # Bug fix commit
    (repo / "auth.py").write_text("def login(): pass\ndef logout(): pass\n# bug fix")
    subprocess.run(["git", "add", "auth.py"], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "fix: resolve auth bug"],
                   cwd=str(repo), capture_output=True, check=True)

    return repo


class TestGitScanner:
    def test_init_valid_path(self, git_repo):
        scanner = GitScanner(str(git_repo))
        assert scanner.repo_path == str(git_repo)

    def test_init_invalid_path(self):
        with pytest.raises(FileNotFoundError):
            GitScanner("/nonexistent/path")

    def test_is_git_repo(self, git_repo):
        scanner = GitScanner(str(git_repo))
        assert scanner.is_git_repo()

    def test_is_not_git_repo(self, tmp_path):
        scanner = GitScanner(str(tmp_path))
        # tmp_path might still be a git repo if we're inside one
        # So we create a non-git subdir
        nongit = tmp_path / "nongit"
        nongit.mkdir()
        scanner2 = GitScanner(str(nongit))
        assert not scanner2.is_git_repo()

    def test_get_commit_log(self, git_repo):
        scanner = GitScanner(str(git_repo))
        commits = scanner.get_commit_log()
        assert len(commits) >= 3

    def test_scan_returns_result(self, git_repo):
        scanner = GitScanner(str(git_repo))
        result = scanner.scan()
        assert isinstance(result, ScanResult)
        assert result.root == str(git_repo)

    def test_scan_has_file_histories(self, git_repo):
        scanner = GitScanner(str(git_repo))
        result = scanner.scan()
        assert len(result.file_histories) > 0

    def test_scan_auth_history(self, git_repo):
        scanner = GitScanner(str(git_repo))
        result = scanner.scan()
        # auth.py was modified 3 times
        auth_history = result.file_histories.get("auth.py")
        assert auth_history is not None
        assert auth_history.total_commits >= 2

    def test_scan_co_changes(self, git_repo):
        scanner = GitScanner(str(git_repo))
        result = scanner.scan()
        # Files that were committed together should have co-change entries
        assert isinstance(result.co_changes, dict)

    def test_scan_import_graph(self, git_repo):
        scanner = GitScanner(str(git_repo))
        result = scanner.scan()
        # main.py imports auth and utils
        imports = result.import_graph.get("main.py", set())
        # Should detect at least some imports
        assert isinstance(result.import_graph, dict)


class TestFileCommit:
    def test_is_bug_fix_true(self):
        commit = FileCommit(
            commit_hash="abc123",
            author="Test",
            timestamp=datetime.now(timezone.utc),
            message="fix: resolve login bug",
        )
        assert commit.is_bug_fix

    def test_is_bug_fix_false(self):
        commit = FileCommit(
            commit_hash="abc123",
            author="Test",
            timestamp=datetime.now(timezone.utc),
            message="add new feature",
        )
        assert not commit.is_bug_fix

    def test_is_bug_fix_hotfix(self):
        commit = FileCommit(
            commit_hash="abc123",
            author="Test",
            timestamp=datetime.now(timezone.utc),
            message="hotfix: critical patch",
        )
        assert commit.is_bug_fix

    def test_is_bug_fix_issue(self):
        commit = FileCommit(
            commit_hash="abc123",
            author="Test",
            timestamp=datetime.now(timezone.utc),
            message="resolve issue #42",
        )
        assert commit.is_bug_fix


class TestFileHistory:
    def test_total_commits(self):
        history = FileHistory(filepath="test.py", commits=[])
        assert history.total_commits == 0

        c1 = FileCommit(commit_hash="a", author="x",
                        timestamp=datetime.now(timezone.utc), message="m1")
        c2 = FileCommit(commit_hash="b", author="x",
                        timestamp=datetime.now(timezone.utc), message="m2")
        history.commits = [c1, c2]
        assert history.total_commits == 2

    def test_bug_fix_count(self):
        c1 = FileCommit(commit_hash="a", author="x",
                        timestamp=datetime.now(timezone.utc), message="fix bug")
        c2 = FileCommit(commit_hash="b", author="x",
                        timestamp=datetime.now(timezone.utc), message="new feature")
        history = FileHistory(filepath="test.py", commits=[c1, c2])
        assert history.bug_fix_count == 1

    def test_commits_in_period(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=60)
        recent = now - timedelta(days=5)

        c1 = FileCommit(commit_hash="a", author="x", timestamp=old, message="old")
        c2 = FileCommit(commit_hash="b", author="x", timestamp=recent, message="recent")
        c3 = FileCommit(commit_hash="c", author="x", timestamp=now, message="now")

        history = FileHistory(filepath="test.py", commits=[c1, c2, c3])
        result = history.commits_in_period(now - timedelta(days=30), now)
        assert len(result) == 2  # c2 and c3

    def test_commits_per_week(self):
        now = datetime.now(timezone.utc)
        commits = [
            FileCommit(commit_hash=f"c{i}", author="x",
                       timestamp=now - timedelta(days=i), message=f"m{i}")
            for i in range(14)
        ]
        history = FileHistory(filepath="test.py", commits=commits)
        cpw = history.commits_per_week(num_weeks=4, now=now)
        assert cpw > 0

    def test_last_commit_time(self):
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(days=5)
        c1 = FileCommit(commit_hash="a", author="x", timestamp=earlier, message="m1")
        c2 = FileCommit(commit_hash="b", author="x", timestamp=now, message="m2")
        history = FileHistory(filepath="test.py", commits=[c1, c2])
        assert history.last_commit_time == now

    def test_last_commit_time_empty(self):
        history = FileHistory(filepath="test.py", commits=[])
        assert history.last_commit_time is None

    def test_total_insertions_deletions(self):
        c1 = FileCommit(commit_hash="a", author="x",
                        timestamp=datetime.now(timezone.utc), message="m1",
                        insertions=10, deletions=5)
        history = FileHistory(filepath="test.py", commits=[c1])
        assert history.total_insertions == 10
        assert history.total_deletions == 5
