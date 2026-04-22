"""Shared test fixtures for stratagit tests."""

import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone

import pytest


@pytest.fixture
def git_repo(tmp_path):
    """Create a minimal git repository with some commits."""
    repo = tmp_path / "test-repo"
    repo.mkdir()

    # Init repo
    subprocess.run(["git", "init"], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(repo), capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=str(repo), capture_output=True, check=True,
    )

    # Create initial commit
    (repo / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(repo), capture_output=True, check=True,
    )

    # Add Python file
    (repo / "app.py").write_text("def hello():\n    print('hello')\n\ndef world():\n    print('world')\n")
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add app with hello and world functions"],
        cwd=str(repo), capture_output=True, check=True,
    )

    # Add JS file
    (repo / "index.js").write_text("function main() {\n  console.log('hi');\n}\n")
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add JavaScript entry point"],
        cwd=str(repo), capture_output=True, check=True,
    )

    return str(repo)


@pytest.fixture
def rich_repo(tmp_path):
    """Create a more complex repo with branches, merges, and deletions."""
    repo = tmp_path / "rich-repo"
    repo.mkdir()

    # Init
    subprocess.run(["git", "init"], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "rich@test.com"],
        cwd=str(repo), capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Rich Tester"],
        cwd=str(repo), capture_output=True, check=True,
    )

    # Initial commit
    (repo / "main.py").write_text("# main\nimport os\n\ndef run():\n    pass\n\nclass App:\n    def start(self):\n        pass\n")
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial main.py"],
        cwd=str(repo), capture_output=True, check=True,
    )

    # Add more code
    (repo / "utils.py").write_text("def helper():\n    return True\n\ndef deprecated_func():\n    pass\n")
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add utils module"],
        cwd=str(repo), capture_output=True, check=True,
    )

    # Create a feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feature/test"],
        cwd=str(repo), capture_output=True, check=True,
    )
    (repo / "feature.py").write_text("def new_feature():\n    return 'new'\n")
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add new feature"],
        cwd=str(repo), capture_output=True, check=True,
    )

    # Merge back
    subprocess.run(
        ["git", "checkout", "master"],
        cwd=str(repo), capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "merge", "--no-ff", "feature/test", "-m", "Merge feature/test"],
        cwd=str(repo), capture_output=True, check=True,
    )

    # Delete utils.py (creates a fossil)
    (repo / "utils.py").unlink()
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Remove utils module"],
        cwd=str(repo), capture_output=True, check=True,
    )

    return str(repo)
