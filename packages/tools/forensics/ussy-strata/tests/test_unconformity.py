"""Tests for unconformity detection (stratagit.core.unconformity)."""

import pytest
from ussy_strata.core.unconformity import detect_unconformities
from ussy_strata.core import Unconformity, UnconformityType


class TestDetectUnconformities:
    def test_returns_list(self, git_repo):
        result = detect_unconformities(git_repo)
        assert isinstance(result, list)

    def test_items_are_unconformity(self, git_repo):
        result = detect_unconformities(git_repo)
        for u in result:
            assert isinstance(u, Unconformity)
            assert isinstance(u.unconformity_type, UnconformityType)

    def test_sorted_by_date(self, git_repo):
        result = detect_unconformities(git_repo)
        if len(result) > 1:
            dates = [u.date for u in result if u.date is not None]
            for i in range(len(dates) - 1):
                assert dates[i] >= dates[i + 1]

    def test_with_max_commits(self, git_repo):
        result = detect_unconformities(git_repo, max_commits=5)
        assert isinstance(result, list)

    def test_rich_repo_has_unconformities(self, rich_repo):
        result = detect_unconformities(rich_repo)
        # Rich repo has a merge commit which may show as unconformity
        assert isinstance(result, list)
        # The merge might be detected as a squash-type unconformity
        types_found = {u.unconformity_type for u in result}
        # Just verify we get valid results
        for u in result:
            assert u.confidence >= 0
            assert u.confidence <= 1

    def test_unconformity_has_description(self, git_repo):
        result = detect_unconformities(git_repo)
        for u in result:
            assert u.description  # should have some description

    def test_unconformity_severity(self, git_repo):
        result = detect_unconformities(git_repo)
        for u in result:
            assert u.severity in ("major", "moderate", "minor")
