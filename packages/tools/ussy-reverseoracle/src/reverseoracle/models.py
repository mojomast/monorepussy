from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any


@dataclass
class DecisionContext:
    commit_hash: str
    description: str
    alternative: str
    interface_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    requirements_text: str = ""
    file_contents: dict[str, str] = field(default_factory=dict)
    test_contents: dict[str, str] = field(default_factory=dict)


@dataclass
class CounterfactualArtifact:
    id: str
    path: str
    source: str
    prompt: str


@dataclass
class EvolutionStep:
    commit: str
    diff: str
    prompt: str
    applied: bool


@dataclass
class EvaluationStats:
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    total: int = 0
    duration_seconds: float = 0.0
    output: str = ""


@dataclass
class CodeMetrics:
    loc: int = 0
    function_count: int = 0
    class_count: int = 0
    dependency_count: int = 0


@dataclass
class EvaluationResult:
    baseline: EvaluationStats
    counterfactual: EvaluationStats
    baseline_metrics: CodeMetrics
    counterfactual_metrics: CodeMetrics
    diff_added: int = 0
    diff_removed: int = 0
    diff_modified: int = 0


@dataclass
class AnalysisReport:
    id: str
    decision: str
    commit_hash: str
    alternative: str
    repo_path: str
    counterfactual_path: str
    context: DecisionContext
    evolution: list[EvolutionStep]
    evaluation: EvaluationResult

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Mark:
    id: str
    commit: str
    description: str
    alternative: str
    module_path: str | None
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
