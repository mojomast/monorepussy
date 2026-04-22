"""Crucible map — locate the most valuable code by density × usage."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

from ussy_assay.classifier import classify_source
from ussy_assay.models import (
    CrucibleEntry,
    FunctionAnalysis,
    ModuleAnalysis,
    ProjectAnalysis,
)
from ussy_assay.scanner import _resolve_paths, read_source


def count_callers(project: ProjectAnalysis) -> dict[str, int]:
    """Count how many times each function name is called across the project.

    Returns a mapping of function_name -> caller_count.
    """
    calls: Counter[str] = Counter()

    for mod in project.modules:
        try:
            source = read_source(Path(mod.file_path))
            if not source:
                continue
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _call_name(node)
                if name:
                    calls[name] += 1

    return dict(calls)


def _call_name(call: ast.Call) -> str | None:
    """Extract a simple function name from a Call node."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def build_crucible(
    project: ProjectAnalysis,
    top_n: int = 10,
    bottom_n: int = 10,
) -> dict:
    """Build a crucible map — ranked list of most/least valuable functions.

    Value score = grade × (caller_count + 1).
    """
    caller_map = count_callers(project)

    entries: list[CrucibleEntry] = []
    for func in project.all_functions:
        caller_count = caller_map.get(func.name, 0)
        entries.append(CrucibleEntry(
            function=func,
            caller_count=caller_count,
        ))

    # Sort by value score descending
    entries.sort(key=lambda e: e.value_score, reverse=True)

    top = entries[:top_n]
    bottom = sorted(entries[-bottom_n:], key=lambda e: e.value_score) if len(entries) > bottom_n else []

    # Bottom are those with low grade
    low_grade = sorted(entries, key=lambda e: e.function.grade)[:bottom_n]

    return {
        "top": top,
        "bottom": low_grade,
        "all": entries,
    }


def crucible_rank_emoji(entry: CrucibleEntry) -> str:
    """Return an emoji rank for a crucible entry."""
    grade = entry.function.grade
    if grade >= 80:
        return "\U0001f48e\U0001f48e\U0001f48e"  # 💎💎💎
    if grade >= 60:
        return "\U0001f48e\U0001f48e"  # 💎💎
    if grade >= 40:
        return "\U0001f48e"  # 💎
    return "\u26a0\ufe0f"  # ⚠️
