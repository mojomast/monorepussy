"""Tests for carbon dating (stratagit.core.carbon_date)."""

import pytest
from stratagit.core.carbon_date import carbon_date


class TestCarbonDate:
    def test_basic_carbon_date(self, git_repo):
        result = carbon_date(git_repo, "README.md", 1)
        assert "file" in result
        assert "line_number" in result
        assert result["file"] == "README.md"
        assert result["line_number"] == 1

    def test_has_current_content(self, git_repo):
        result = carbon_date(git_repo, "README.md", 1)
        assert isinstance(result["current_content"], str)

    def test_has_author(self, git_repo):
        result = carbon_date(git_repo, "README.md", 1)
        assert isinstance(result["deposited_author"], str)

    def test_has_stability(self, git_repo):
        result = carbon_date(git_repo, "README.md", 1)
        assert isinstance(result["stability"], str)

    def test_invalid_file(self, git_repo):
        result = carbon_date(git_repo, "nonexistent.py", 1)
        assert result["current_content"] == ""

    def test_invalid_line(self, git_repo):
        result = carbon_date(git_repo, "README.md", 9999)
        assert result["current_content"] == ""

    def test_python_file(self, git_repo):
        result = carbon_date(git_repo, "app.py", 1)
        assert result["file"] == "app.py"
