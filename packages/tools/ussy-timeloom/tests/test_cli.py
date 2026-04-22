from __future__ import annotations

import subprocess

from click.testing import CliRunner

from timeloom.cli import main


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
    return repo


def test_cli_weave_and_analyze(tmp_path):
    repo = _make_repo(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["weave", str(repo)])
    assert result.exit_code == 0
    assert "<svg" in result.output
    result = runner.invoke(main, ["analyze", str(repo), "--json"])
    assert result.exit_code == 0
    assert "total_crossings" in result.output


def test_cli_export_and_heatmap(tmp_path):
    repo = _make_repo(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["export", str(repo)])
    assert result.exit_code == 0
    assert "[WIF]" in result.output
    result = runner.invoke(main, ["heatmap", str(repo)])
    assert result.exit_code == 0
    assert "<svg" in result.output
