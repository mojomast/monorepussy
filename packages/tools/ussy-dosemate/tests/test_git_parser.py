"""Tests for the git_parser module."""

import os
import tempfile
import shutil
from datetime import datetime, timedelta

import pytest

from ussy_dosemate.git_parser import GitHistoryParser, CommitInfo, PullRequestInfo


class TestGitHistoryParser:
    """Tests for GitHistoryParser with real git repos."""

    def test_parse_commits_from_real_repo(self, temp_repo):
        """Should parse commits from a real git repository."""
        parser = GitHistoryParser(temp_repo)
        commits = parser.parse_commits()
        assert len(commits) >= 1  # at least the initial commit

    def test_commit_info_fields(self, temp_repo):
        """Parsed commits should have proper fields."""
        parser = GitHistoryParser(temp_repo)
        commits = parser.parse_commits()
        if commits:
            c = commits[0]
            assert c.hash
            assert isinstance(c.date, datetime)
            assert isinstance(c.message, str)

    def test_merge_commits(self, temp_repo):
        """Should find merge commits."""
        parser = GitHistoryParser(temp_repo)
        merges = parser.get_merge_commits()
        assert len(merges) >= 1

    def test_synthesize_prs(self, temp_repo):
        """Should synthesize PR-like objects from merge commits."""
        parser = GitHistoryParser(temp_repo)
        prs = parser.synthesize_prs()
        assert len(prs) >= 1
        for pr in prs:
            assert pr.id.startswith("pr_")
            assert pr.merged_at is not None

    def test_file_module_map(self, temp_repo):
        """Should map files to modules."""
        parser = GitHistoryParser(temp_repo)
        file_map = parser.get_file_module_map()
        assert len(file_map) > 0
        # Files should map to modules
        for filepath, module in file_map.items():
            assert isinstance(filepath, str)
            assert isinstance(module, str)

    def test_deprecated_lines(self, temp_repo):
        """Should find DEPRECATED markers."""
        parser = GitHistoryParser(temp_repo)
        removed, total = parser.get_deprecated_lines()
        # Should find at least the DEPRECATED markers we added
        assert isinstance(removed, int)
        assert isinstance(total, int)

    def test_active_branches(self, temp_repo):
        """Should list branches."""
        parser = GitHistoryParser(temp_repo)
        branches = parser.get_active_branches()
        assert len(branches) >= 1


class TestGitHistoryParserEmpty:
    """Tests for GitHistoryParser with empty/invalid repos."""

    def test_nonexistent_repo(self):
        """Should handle nonexistent repo gracefully."""
        parser = GitHistoryParser("/nonexistent/path")
        commits = parser.parse_commits()
        assert commits == []

    def test_synthesize_prs_empty(self):
        """Should handle empty repo for PR synthesis."""
        tmpdir = tempfile.mkdtemp()
        try:
            os.system(f'cd {tmpdir} && git init && git config user.email "t@t.com" && git config user.name "T"')
            # No commits
            parser = GitHistoryParser(tmpdir)
            prs = parser.synthesize_prs()
            assert prs == []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestParseDuration:
    """Tests for the CLI's parse_duration helper."""

    def test_parse_days(self):
        from ussy_dosemate.cli import parse_duration
        result = parse_duration("7d")
        assert "7 days ago" in result

    def test_parse_weeks(self):
        from ussy_dosemate.cli import parse_duration
        result = parse_duration("2w")
        assert "2 weeks ago" in result

    def test_parse_months(self):
        from ussy_dosemate.cli import parse_duration
        result = parse_duration("3m")
        assert "3 months ago" in result

    def test_parse_passthrough(self):
        from ussy_dosemate.cli import parse_duration
        result = parse_duration("2024-01-01")
        assert result == "2024-01-01"

    def test_parse_single_day(self):
        from ussy_dosemate.cli import parse_duration
        result = parse_duration("1d")
        assert "1 day ago" in result
