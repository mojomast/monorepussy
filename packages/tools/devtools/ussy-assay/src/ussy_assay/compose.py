"""Composition analysis — break down each function into its elements."""

from __future__ import annotations

from pathlib import Path

from ussy_assay.classifier import classify_source
from ussy_assay.models import FunctionAnalysis, ModuleAnalysis, Category
from ussy_assay.scanner import _resolve_paths, read_source


def compose_function(func: FunctionAnalysis) -> dict[str, dict]:
    """Return detailed composition for a single function.

    Returns dict mapping category -> {lines, percentage, icon, display_name}.
    """
    result: dict[str, dict] = {}
    total = func.total_lines

    for cat_value, count in func.category_counts.items():
        try:
            cat = Category(cat_value)
        except ValueError:
            cat = Category.UNKNOWN
        pct = round(count / total * 100, 1) if total > 0 else 0.0
        result[cat_value] = {
            "lines": count,
            "percentage": pct,
            "icon": cat.icon,
            "display_name": cat.display_name,
        }

    return result


def compose_module(file_path: str | Path) -> list[dict]:
    """Return composition for every function in a file."""
    p = Path(file_path)
    source = read_source(p)
    func_analyses = classify_source(source, str(p))

    results: list[dict] = []
    for func in func_analyses:
        comp = compose_function(func)
        results.append({
            "name": func.name,
            "total_lines": func.total_lines,
            "grade": func.grade,
            "composition": comp,
        })
    return results


def compose_bar(percentage: float, width: int = 12) -> str:
    """Render a simple ASCII bar for a percentage.

    Uses filled blocks (■) for the percentage and empty blocks (░) for the rest.
    """
    filled = round(percentage / 100 * width)
    filled = max(0, min(width, filled))
    return "\u25a0" * filled + "\u2591" * (width - filled)
