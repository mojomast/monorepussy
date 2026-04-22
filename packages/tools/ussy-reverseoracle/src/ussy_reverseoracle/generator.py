from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from uuid import uuid4
import ast
import re

from .config import AppConfig
from .llm import call_llm
from .models import CounterfactualArtifact, DecisionContext


def build_prompt(context: DecisionContext) -> tuple[str, str]:
    system_prompt = "You generate counterfactual implementations that preserve the given interface and tests."
    user_prompt = [
        f"Decision: {context.description}",
        f"Alternative: {context.alternative}",
        "Interface contract:",
    ]
    for path, content in context.file_contents.items():
        user_prompt.append(f"### {path}\n{content}")
    user_prompt.append("Tests:")
    for path, content in context.test_contents.items():
        user_prompt.append(f"### {path}\n{content}")
    if context.dependencies:
        user_prompt.append("Dependencies: " + ", ".join(context.dependencies))
    if context.requirements_text:
        user_prompt.append("Requirements context:\n" + context.requirements_text)
    return system_prompt, "\n\n".join(user_prompt)


def extract_code_blocks(text: str) -> list[str]:
    blocks = re.findall(
        r"```(?:python|py)?\n(.*?)```", text, flags=re.DOTALL | re.IGNORECASE
    )
    if blocks:
        return [block.strip() for block in blocks if block.strip()]
    return [text.strip()]


def validate_python(code: str) -> None:
    ast.parse(code)


def generate_counterfactual(
    repo_path: str | Path,
    context: DecisionContext,
    config: AppConfig,
    *,
    llm_callable=call_llm,
) -> CounterfactualArtifact:
    system_prompt, user_prompt = build_prompt(context)
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
    primary = blocks[0]
    validate_python(primary)
    cf_id = str(uuid4())
    cf_dir = Path(repo_path) / ".reverseoracle" / "counterfactuals" / cf_id
    cf_dir.mkdir(parents=True, exist_ok=True)
    (cf_dir / "counterfactual.py").write_text(primary)
    (cf_dir / "response.txt").write_text(response)
    return CounterfactualArtifact(
        id=cf_id, path=str(cf_dir), source=primary, prompt=user_prompt
    )
