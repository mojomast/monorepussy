from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=str(repo), check=True, capture_output=True, text=True
    )
    return result.stdout


@pytest.fixture()
def temp_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.name", "Test User")
    git(repo, "config", "user.email", "test@example.com")
    (repo / "pyproject.toml").write_text('[project]\ndependencies = ["requests"]\n')
    (repo / "app.py").write_text("def answer():\n    return 42\n")
    (repo / "test_app.py").write_text(
        "from app import answer\n\ndef test_answer():\n    assert answer() == 42\n"
    )
    git(repo, "add", ".")
    git(repo, "commit", "-m", "initial commit")
    return repo
