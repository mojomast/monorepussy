from __future__ import annotations

from pathlib import Path
import subprocess

from reverseoracle.config import AppConfig
from reverseoracle.context import reconstruct_context
from reverseoracle.generator import (
    build_prompt,
    extract_code_blocks,
    generate_counterfactual,
)


def test_prompt_and_blocks(temp_repo: Path):
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=temp_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    ctx = reconstruct_context(temp_repo, commit, "Chose Redis", "Memcached")
    system, user = build_prompt(ctx)
    assert "Chose Redis" in user
    assert system
    assert extract_code_blocks("```python\nprint(1)\n```") == ["print(1)"]


def test_generate_counterfactual_writes_files(temp_repo: Path):
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=temp_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    ctx = reconstruct_context(temp_repo, commit, "Chose Redis", "Memcached")
    config = AppConfig()
    artifact = generate_counterfactual(
        temp_repo,
        ctx,
        config,
        llm_callable=lambda *args, **kwargs: (
            "```python\ndef answer():\n    return 7\n```"
        ),
    )
    assert Path(artifact.path, "counterfactual.py").exists()
