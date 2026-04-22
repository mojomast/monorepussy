from __future__ import annotations

from pathlib import Path
import subprocess

from click.testing import CliRunner

from ussy_reverseoracle.cli import main


def _commit(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_cli_mark_and_list(temp_repo: Path):
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "mark",
            str(temp_repo),
            _commit(temp_repo),
            "--description",
            "Chose Redis",
            "--alternative",
            "Memcached",
        ],
    )
    assert result.exit_code == 0
    result = runner.invoke(main, ["list-marks", str(temp_repo)])
    assert result.exit_code == 0
    assert "Chose Redis" in result.output
