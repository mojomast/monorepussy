from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os

import yaml


@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = "gpt-4"
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"


@dataclass
class AnalysisConfig:
    max_evolution_commits: int = 50
    test_timeout: int = 120
    min_test_pass_rate: float = 0.0


@dataclass
class GenerationConfig:
    temperature: float = 0.2
    max_tokens: int = 4096


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)


def load_config(repo_path: str | Path | None = None) -> AppConfig:
    config = AppConfig()
    if repo_path is not None:
        config_path = Path(repo_path) / ".reverseoracle" / "config.yaml"
        if config_path.exists():
            data = yaml.safe_load(config_path.read_text()) or {}
            _apply_config(config, data)
    config.llm.base_url = os.environ.get(
        "REVERSEORACLE_LLM_BASE_URL", config.llm.base_url
    )
    config.llm.model = os.environ.get("REVERSEORACLE_LLM_MODEL", config.llm.model)
    return config


def _apply_config(config: AppConfig, data: dict[str, Any]) -> None:
    llm = data.get("llm", {})
    analysis = data.get("analysis", {})
    generation = data.get("generation", {})
    for key, value in llm.items():
        if hasattr(config.llm, key):
            setattr(config.llm, key, value)
    for key, value in analysis.items():
        if hasattr(config.analysis, key):
            setattr(config.analysis, key, value)
    for key, value in generation.items():
        if hasattr(config.generation, key):
            setattr(config.generation, key, value)
