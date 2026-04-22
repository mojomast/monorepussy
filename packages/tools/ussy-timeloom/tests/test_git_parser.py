from __future__ import annotations

import subprocess

from timeloom.git_parser import classify_commit_type, parse_repo


def _make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init"], cwd=repo, check=True, capture_output=True, text=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
    (repo / "a.txt").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: add a"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    (repo / "a.txt").write_text("two\n", encoding="utf-8")
    (repo / "b.txt").write_text("new\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt", "b.txt"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "fix: repair a and add b"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return repo


def test_classify_commit_type():
    assert classify_commit_type("feat: add parser") == "feature"
    assert classify_commit_type("fix: hotfix") == "fix"
    assert classify_commit_type("chore") == "other"


def test_parse_repo_builds_matrix(tmp_path):
    repo = _make_repo(tmp_path)
    matrix = parse_repo(str(repo))
    assert matrix.files == ["a.txt", "b.txt"]
    assert len(matrix.commits) == 2
    assert matrix.matrix == [[1, 1], [0, 1]]
    assert matrix.commits[0].change_type == "feature"


def test_parse_repo_respects_last_and_max_files(tmp_path):
    repo = _make_repo(tmp_path)
    matrix = parse_repo(str(repo), last=1, max_files=1)
    assert len(matrix.commits) == 1
    assert len(matrix.files) == 1
