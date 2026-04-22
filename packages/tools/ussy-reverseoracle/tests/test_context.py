from __future__ import annotations

from pathlib import Path
import subprocess

from ussy_reverseoracle.context import reconstruct_context, is_test_file


def test_is_test_file():
    assert is_test_file("test_app.py")
    assert is_test_file("pkg/foo_test.py")
    assert not is_test_file("app.py")


def test_reconstruct_context(temp_repo: Path):
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=temp_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    ctx = reconstruct_context(temp_repo, commit, "Chose Redis", "Memcached")
    assert ctx.commit_hash == commit
    assert "app.py" in ctx.interface_files
    assert "test_app.py" in ctx.test_files
    assert "requests" in ctx.dependencies
    assert ctx.file_contents["app.py"].strip().startswith("def answer")
