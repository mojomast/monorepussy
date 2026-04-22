from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from ussy_churn.mining import mine_repository


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True)
    (repo / "pkg").mkdir()
    (repo / "pkg" / "a.py").write_text("print('a')\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "first"], cwd=repo, check=True, capture_output=True)
    (repo / "pkg" / "a.py").write_text("print('a2')\n", encoding="utf-8")
    (repo / "pkg" / "b.py").write_text("print('b')\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "second"], cwd=repo, check=True, capture_output=True)
    return repo


def test_mine_repository_groups_modules(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    commits = mine_repository(repo, max_commits=10, depth=1)
    assert len(commits) == 2
    assert commits[-1].modules == ("pkg",)
    assert commits[-1].files
