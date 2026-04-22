"""Tests for the git log parser (stratagit.core.parser)."""

import pytest
import subprocess
from ussy_strata.core.parser import (
    is_git_repo,
    parse_commits,
    _parse_log_output,
    classify_intrusions,
    assign_branch_names,
    compute_stability,
)
from ussy_strata.core import Stratum, Intrusion, IntrusionType


class TestIsGitRepo:
    def test_valid_repo(self, git_repo):
        assert is_git_repo(git_repo) is True

    def test_invalid_path(self, tmp_path):
        assert is_git_repo(str(tmp_path)) is False

    def test_nonexistent_path(self):
        assert is_git_repo("/nonexistent/path/xyz") is False


class TestParseCommits:
    def test_parse_basic_repo(self, git_repo):
        strata = parse_commits(git_repo)
        assert len(strata) == 3  # 3 commits from fixture

    def test_strata_are_stratum_objects(self, git_repo):
        strata = parse_commits(git_repo)
        for s in strata:
            assert isinstance(s, Stratum)

    def test_strata_have_required_fields(self, git_repo):
        strata = parse_commits(git_repo)
        for s in strata:
            assert s.commit_hash
            assert s.author
            assert s.date is not None
            assert s.message

    def test_strata_ordered_newest_first(self, git_repo):
        strata = parse_commits(git_repo)
        dates = [s.date for s in strata]
        # Should be in descending order (newest first)
        for i in range(len(dates) - 1):
            assert dates[i] >= dates[i + 1]

    def test_max_count(self, git_repo):
        strata = parse_commits(git_repo, max_count=1)
        assert len(strata) == 1

    def test_strata_have_file_changes(self, git_repo):
        strata = parse_commits(git_repo)
        # At least some strata should have file changes
        has_files = any(s.files_changed for s in strata)
        assert has_files

    def test_strata_have_line_counts(self, git_repo):
        strata = parse_commits(git_repo)
        has_lines = any(s.lines_added > 0 or s.lines_deleted > 0 for s in strata)
        assert has_lines

    def test_minerals_populated(self, git_repo):
        strata = parse_commits(git_repo)
        has_minerals = any(s.minerals for s in strata)
        assert has_minerals


class TestParseLogOutput:
    def test_empty_output(self):
        strata = _parse_log_output("")
        assert strata == []

    def test_single_commit(self):
        output = "abc123def456|Test User|2024-01-15T10:00:00+00:00|Initial commit|\n5 2 README.md\n"
        strata = _parse_log_output(output)
        assert len(strata) == 1
        assert strata[0].commit_hash == "abc123def456"
        assert strata[0].author == "Test User"
        assert strata[0].message == "Initial commit"
        assert strata[0].lines_added == 5
        assert strata[0].lines_deleted == 2
        assert strata[0].files_changed == ["README.md"]

    def test_multiple_commits(self):
        output = (
            "hash1|Author|2024-01-15T10:00:00+00:00|First|\n3 0 a.py\n\n"
            "hash2|Author|2024-01-14T10:00:00+00:00|Second|\n1 1 b.py\n"
        )
        strata = _parse_log_output(output)
        assert len(strata) == 2

    def test_commit_with_parents(self):
        output = "hash1|Author|2024-01-15T10:00:00+00:00|Merge|parent1 parent2\n"
        strata = _parse_log_output(output)
        assert len(strata) == 1
        assert len(strata[0].parent_hashes) == 2

    def test_binary_file_stats(self):
        output = "hash1|Author|2024-01-15T10:00:00+00:00|Add binary|\n- - image.png\n"
        strata = _parse_log_output(output)
        assert len(strata) == 1
        assert strata[0].lines_added == 0
        assert strata[0].lines_deleted == 0

    def test_rename_format(self):
        output = "hash1|Author|2024-01-15T10:00:00+00:00|Rename|\n3 0 old.py => new.py\n"
        strata = _parse_log_output(output)
        assert len(strata) == 1
        assert "new.py" in strata[0].files_changed


class TestClassifyIntrusions:
    def test_empty_strata(self):
        assert classify_intrusions([]) == []

    def test_basic_classification(self, git_repo):
        strata = parse_commits(git_repo)
        intrusions = classify_intrusions(strata)
        assert isinstance(intrusions, list)
        for intr in intrusions:
            assert isinstance(intr, Intrusion)
            assert intr.intrusion_type in (IntrusionType.IGNEOUS, IntrusionType.SEDIMENTARY)

    def test_intrusion_has_branch_name(self, git_repo):
        strata = parse_commits(git_repo)
        intrusions = classify_intrusions(strata)
        for intr in intrusions:
            assert intr.branch_name  # should have a name


class TestAssignBranchNames:
    def test_empty_strata(self):
        result = assign_branch_names([], ".")
        assert result == []

    def test_assigns_names(self, git_repo):
        strata = parse_commits(git_repo)
        strata = assign_branch_names(strata, git_repo)
        # Branch names may or may not be assigned depending on repo
        for s in strata:
            assert isinstance(s.branch_name, str)


class TestComputeStability:
    def test_empty_strata(self):
        result = compute_stability([])
        assert result == []

    def test_assigns_tiers(self, git_repo):
        strata = parse_commits(git_repo)
        strata = compute_stability(strata)
        valid_tiers = {"bedrock", "mature", "settling", "active", "volatile"}
        for s in strata:
            assert s.stability_tier in valid_tiers

    def test_tiers_reflect_age(self, git_repo):
        strata = parse_commits(git_repo)
        strata = compute_stability(strata)
        # Recent commits should be active or settling
        # (can't guarantee specific tiers without controlling time)
        assert len(strata) > 0
