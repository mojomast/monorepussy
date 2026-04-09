from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import ast
import difflib
import os
import re
import subprocess
import sys
import time
from typing import Iterable

from .models import CodeMetrics, EvaluationResult, EvaluationStats


def run_pytest(repo_path: str | Path, timeout: int) -> EvaluationStats:
    start = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    duration = time.time() - start
    output = (proc.stdout or "") + (proc.stderr or "")
    passed = _count_from_output(output, r"(\d+) passed")
    failed = _count_from_output(output, r"(\d+) failed")
    skipped = _count_from_output(output, r"(\d+) skipped")
    total = passed + failed + skipped
    return EvaluationStats(
        passed=passed,
        failed=failed,
        skipped=skipped,
        total=total,
        duration_seconds=duration,
        output=output,
    )


def _count_from_output(output: str, pattern: str) -> int:
    match = re.search(pattern, output)
    return int(match.group(1)) if match else 0


def _iter_python_files(root: str | Path) -> Iterable[Path]:
    root = Path(root)
    for path in root.rglob("*.py"):
        if ".reverseoracle" in path.parts:
            continue
        yield path


def analyze_metrics(root: str | Path) -> CodeMetrics:
    loc = 0
    function_count = 0
    class_count = 0
    deps: set[str] = set()
    stdlib = getattr(sys, "stdlib_module_names", set())
    for path in _iter_python_files(root):
        text = path.read_text()
        loc += sum(1 for line in text.splitlines() if line.strip())
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_count += 1
            elif isinstance(node, ast.ClassDef):
                class_count += 1
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    root_name = alias.name.split(".")[0]
                    if root_name not in stdlib:
                        deps.add(root_name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_name = node.module.split(".")[0]
                    if root_name not in stdlib and node.level == 0:
                        deps.add(root_name)
    return CodeMetrics(
        loc=loc,
        function_count=function_count,
        class_count=class_count,
        dependency_count=len(deps),
    )


def diff_summary(
    baseline_root: str | Path, counterfactual_root: str | Path
) -> tuple[int, int, int]:
    baseline_lines = _collect_files(baseline_root)
    counter_lines = _collect_files(counterfactual_root)
    diff = list(difflib.unified_diff(baseline_lines, counter_lines))
    added = sum(
        1 for line in diff if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1 for line in diff if line.startswith("-") and not line.startswith("---")
    )
    modified = min(added, removed)
    return added, removed, modified


def _collect_files(root: str | Path) -> list[str]:
    lines: list[str] = []
    for path in _iter_python_files(root):
        rel = path.relative_to(root)
        lines.append(f"FILE:{rel}")
        lines.extend(path.read_text().splitlines())
    return lines


def evaluate(
    baseline_root: str | Path, counterfactual_root: str | Path, timeout: int
) -> EvaluationResult:
    baseline = run_pytest(baseline_root, timeout)
    counterfactual = run_pytest(counterfactual_root, timeout)
    baseline_metrics = analyze_metrics(baseline_root)
    counterfactual_metrics = analyze_metrics(counterfactual_root)
    added, removed, modified = diff_summary(baseline_root, counterfactual_root)
    return EvaluationResult(
        baseline=baseline,
        counterfactual=counterfactual,
        baseline_metrics=baseline_metrics,
        counterfactual_metrics=counterfactual_metrics,
        diff_added=added,
        diff_removed=removed,
        diff_modified=modified,
    )
