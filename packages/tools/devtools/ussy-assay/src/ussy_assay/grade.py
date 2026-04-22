"""Grade calculation — measure the precious logic percentage."""

from __future__ import annotations

from pathlib import Path

from ussy_assay.classifier import classify_source
from ussy_assay.models import FunctionAnalysis, ModuleAnalysis, ProjectAnalysis, GradeTrend
from ussy_assay.scanner import _resolve_paths, read_source


def grade_project(path: str | Path) -> ProjectAnalysis:
    """Compute grade for an entire project directory or file."""
    files = _resolve_paths(path)
    modules: list[ModuleAnalysis] = []

    for fpath in files:
        source = read_source(fpath)
        if not source:
            continue
        func_analyses = classify_source(source, str(fpath))
        mod = ModuleAnalysis(
            file_path=str(fpath),
            functions=func_analyses,
        )
        modules.append(mod)

    return ProjectAnalysis(modules=modules)


def grade_module(file_path: str | Path) -> ModuleAnalysis:
    """Compute grade for a single Python file."""
    p = Path(file_path)
    source = read_source(p)
    func_analyses = classify_source(source, str(p))
    return ModuleAnalysis(
        file_path=str(p),
        functions=func_analyses,
    )


def compute_trends(
    current: ProjectAnalysis,
    previous: ProjectAnalysis | None = None,
) -> list[GradeTrend]:
    """Compute grade trends by matching function names between runs."""
    if previous is None:
        return [
            GradeTrend(function_name=f.name, current_grade=f.grade)
            for f in current.all_functions
        ]

    prev_map: dict[str, float] = {}
    for mod in previous.modules:
        for func in mod.functions:
            key = f"{mod.file_path}::{func.name}"
            prev_map[key] = func.grade

    trends: list[GradeTrend] = []
    for mod in current.modules:
        for func in mod.functions:
            key = f"{mod.file_path}::{func.name}"
            prev = prev_map.get(key, 0.0)
            trends.append(GradeTrend(
                function_name=func.name,
                current_grade=func.grade,
                previous_grade=prev,
            ))
    return trends


def grade_label(grade: float) -> str:
    """Return a human-readable label for a grade percentage."""
    if grade >= 75:
        return "High-grade ore"
    if grade >= 50:
        return "Medium-grade ore"
    if grade >= 25:
        return "Low-grade ore"
    return "Tailings"
