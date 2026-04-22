from __future__ import annotations

from pathlib import Path
import subprocess

from .config import AppConfig
from .llm import call_llm
from .generator import extract_code_blocks, validate_python
from .models import DecisionContext, EvolutionStep


def post_decision_commits(
    repo_path: str | Path, commit_hash: str, paths: list[str]
) -> list[str]:
    if not paths:
        result = subprocess.run(
            ["git", "log", "--format=%H", f"{commit_hash}..HEAD"],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
            text=True,
        )
    else:
        result = subprocess.run(
            ["git", "log", "--format=%H", f"{commit_hash}..HEAD", "--", *paths],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
            text=True,
        )
    commits = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    commits.reverse()
    return commits


def git_show_diff(repo_path: str | Path, commit: str, paths: list[str]) -> str:
    cmd = ["git", "show", commit, "--"]
    if paths:
        cmd.extend(paths)
    result = subprocess.run(
        cmd, cwd=str(repo_path), check=True, capture_output=True, text=True
    )
    return result.stdout


def evolve_counterfactual(
    repo_path: str | Path,
    counterfactual_path: str | Path,
    context: DecisionContext,
    config: AppConfig,
    *,
    llm_callable=call_llm,
) -> list[EvolutionStep]:
    current = Path(counterfactual_path) / "counterfactual.py"
    if not current.exists():
        return []
    paths = context.interface_files or list(context.file_contents.keys())
    steps: list[EvolutionStep] = []
    for commit in post_decision_commits(repo_path, context.commit_hash, paths)[
        : config.analysis.max_evolution_commits
    ]:
        diff = git_show_diff(repo_path, commit, paths)
        system_prompt = "Apply the intent of the diff to the counterfactual code while preserving its alternative design."
        user_prompt = f"Counterfactual code:\n{current.read_text()}\n\nReal timeline diff:\n{diff}"
        response = llm_callable(
            system_prompt,
            user_prompt,
            model=config.llm.model,
            base_url=config.llm.base_url,
            api_key_env=config.llm.api_key_env,
            temperature=config.generation.temperature,
            max_tokens=config.generation.max_tokens,
        )
        blocks = extract_code_blocks(response)
        candidate = blocks[0]
        validate_python(candidate)
        current.write_text(candidate)
        steps.append(
            EvolutionStep(commit=commit, diff=diff, prompt=user_prompt, applied=True)
        )
    return steps
