from __future__ import annotations

from pathlib import Path
import subprocess

from ussy_reverseoracle.config import AppConfig
from ussy_reverseoracle.context import reconstruct_context
from ussy_reverseoracle.evolution import post_decision_commits, evolve_counterfactual


def test_post_decision_commits_empty(temp_repo: Path):
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=temp_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    ctx = reconstruct_context(temp_repo, commit, "decision", "alt")
    assert post_decision_commits(temp_repo, commit, ctx.interface_files) == []


def test_evolve_counterfactual_no_steps(temp_repo: Path):
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=temp_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    ctx = reconstruct_context(temp_repo, commit, "decision", "alt")
    cf = temp_repo / ".reverseoracle" / "counterfactuals" / "x"
    cf.mkdir(parents=True)
    (cf / "counterfactual.py").write_text("def answer():\n    return 42\n")
    steps = evolve_counterfactual(
        temp_repo,
        cf,
        ctx,
        AppConfig(),
        llm_callable=lambda *args, **kwargs: (
            "```python\ndef answer():\n    return 42\n```"
        ),
    )
    assert steps == []
