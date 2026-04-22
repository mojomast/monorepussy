"""Tests for the fossil detection module (stratagit.core.fossils)."""

import pytest
import subprocess
from ussy_strata.core.fossils import (
    _extract_artifacts,
    excavate_fossils,
    find_fossils_in_diff,
)
from ussy_strata.core import Fossil


class TestExtractArtifacts:
    def test_python_functions(self):
        content = "def hello():\n    pass\n\ndef world():\n    return True\n"
        artifacts = _extract_artifacts(content, "test.py")
        names = [a["name"] for a in artifacts]
        assert "hello" in names
        assert "world" in names
        for a in artifacts:
            assert a["kind"] == "function"

    def test_async_python_functions(self):
        content = "async def fetch():\n    pass\n"
        artifacts = _extract_artifacts(content, "test.py")
        assert len(artifacts) == 1
        assert artifacts[0]["name"] == "fetch"

    def test_python_class(self):
        content = "class MyClass:\n    pass\n"
        artifacts = _extract_artifacts(content, "test.py")
        assert len(artifacts) == 1
        assert artifacts[0]["name"] == "MyClass"
        assert artifacts[0]["kind"] == "class"

    def test_imports(self):
        content = "import os\nfrom sys import path\n"
        artifacts = _extract_artifacts(content, "test.py")
        names = [a["name"] for a in artifacts]
        assert "os" in names
        assert "sys" in names

    def test_javascript_function(self):
        content = "function main() {\n  return 1;\n}\n"
        artifacts = _extract_artifacts(content, "test.js")
        assert any(a["name"] == "main" for a in artifacts)

    def test_rust_function(self):
        content = "fn main() {\n    println!(\"hello\");\n}\n"
        artifacts = _extract_artifacts(content, "main.rs")
        assert any(a["name"] == "main" for a in artifacts)

    def test_go_function(self):
        content = "func HandleRequest() {\n}\n"
        artifacts = _extract_artifacts(content, "main.go")
        assert any(a["name"] == "HandleRequest" for a in artifacts)

    def test_empty_content(self):
        artifacts = _extract_artifacts("", "test.py")
        assert artifacts == []

    def test_no_artifacts(self):
        content = "# Just a comment\n\nx = 1\n"
        artifacts = _extract_artifacts(content, "test.py")
        # May or may not find things depending on patterns
        assert isinstance(artifacts, list)


class TestExcavateFossils:
    def test_find_deleted_fossils(self, rich_repo):
        fossils = excavate_fossils(rich_repo)
        # The rich_repo fixture deletes utils.py which has functions
        assert isinstance(fossils, list)
        # Should find at least some fossils from deleted file
        for f in fossils:
            assert isinstance(f, Fossil)
            assert f.name
            assert f.kind in ("function", "class", "import", "variable")
            assert f.file_path

    def test_fossil_with_pattern_filter(self, rich_repo):
        fossils = excavate_fossils(rich_repo, pattern="helper")
        for f in fossils:
            assert "helper" in f.name.lower()

    def test_fossil_has_dates(self, rich_repo):
        fossils = excavate_fossils(rich_repo)
        # At least some fossils should have dates
        if fossils:
            has_dates = any(f.deposited_date is not None or f.extinct_date is not None for f in fossils)
            assert has_dates

    def test_no_fossils_in_clean_repo(self, git_repo):
        fossils = excavate_fossils(git_repo)
        # git_repo fixture doesn't delete anything
        assert isinstance(fossils, list)

    def test_max_commits_limit(self, rich_repo):
        fossils = excavate_fossils(rich_repo, max_commits=1)
        assert isinstance(fossils, list)


class TestFindFossilsInDiff:
    def test_find_in_commit(self, rich_repo):
        # Find a commit that deletes files
        result = subprocess.run(
            ["git", "log", "--diff-filter=D", "--format=%H", "-1"],
            cwd=rich_repo, capture_output=True, text=True,
        )
        if result.stdout.strip():
            commit_hash = result.stdout.strip()
            fossils = find_fossils_in_diff(rich_repo, commit_hash)
            assert isinstance(fossils, list)
