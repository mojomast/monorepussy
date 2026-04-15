"""Alloy detection — find functions with mixed/interleaved concerns."""

from __future__ import annotations

from assay.models import (
    Category,
    FunctionAnalysis,
    AlloyInfo,
    ModuleAnalysis,
    ProjectAnalysis,
)

# Minimum number of distinct concerns to qualify as alloyed
_ALLOY_THRESHOLD = 3

# Minimum number of category alternations to count as interleaved
_INTERLEAVE_THRESHOLD = 2


def detect_alloys(functions: list[FunctionAnalysis]) -> list[AlloyInfo]:
    """Detect alloyed functions from a list of function analyses."""
    results: list[AlloyInfo] = []

    for func in functions:
        if func.concern_count < _ALLOY_THRESHOLD:
            continue

        interleaving = _count_interleavings(func)

        if interleaving >= _INTERLEAVE_THRESHOLD:
            suggestions = _generate_suggestions(func)
            info = AlloyInfo(
                function=func,
                concern_count=func.concern_count,
                interleaving_count=interleaving,
                suggestions=suggestions,
            )
            results.append(info)

    return results


def _count_interleavings(func: FunctionAnalysis) -> int:
    """Count the number of times the category sequence switches between
    non-unknown, non-slag categories."""
    if not func.lines:
        return 0

    # Build sequence of categories (skip unknown/slag)
    seq: list[Category] = []
    for ln in func.lines:
        if ln.category in (Category.UNKNOWN, Category.SLAG):
            continue
        seq.append(ln.category)

    if len(seq) < 2:
        return 0

    # Count transitions between different categories
    transitions = 0
    prev = seq[0]
    for cat in seq[1:]:
        if cat != prev:
            transitions += 1
        prev = cat

    return transitions


def _generate_suggestions(func: FunctionAnalysis) -> list[str]:
    """Generate refinement suggestions for an alloyed function."""
    suggestions: list[str] = []

    # Find the largest non-business concern
    non_biz = {
        cat: cnt
        for cat, cnt in func.category_counts.items()
        if cat not in (Category.BUSINESS.value, Category.UNKNOWN.value)
        and cnt > 0
    }

    if not non_biz:
        return suggestions

    sorted_concerns = sorted(non_biz.items(), key=lambda x: x[1], reverse=True)

    for cat_val, count in sorted_concerns[:2]:
        try:
            cat = Category(cat_val)
        except ValueError:
            continue
        name = cat.display_name
        if cat == Category.VALIDATION:
            suggestions.append(f"Extract validation to decorator (save {count} lines)")
        elif cat == Category.LOGGING:
            suggestions.append(f"Extract logging to wrapper (save {count} lines)")
        elif cat == Category.ERROR_HANDLING:
            suggestions.append(f"Extract error handling to middleware (save {count} lines)")
        elif cat == Category.FRAMEWORK:
            suggestions.append(f"Extract framework calls to repository (save {count} lines)")
        else:
            suggestions.append(f"Extract {name.lower()} (save {count} lines)")

    return suggestions


def find_pure_functions(functions: list[FunctionAnalysis], min_grade: float = 70.0) -> list[FunctionAnalysis]:
    """Find high-grade functions (mostly business logic)."""
    return [
        func for func in functions
        if func.grade >= min_grade and func.concern_count <= 2
    ]


def analyze_project_alloys(project: ProjectAnalysis) -> dict:
    """Full alloy analysis for a project, returning alloyed + pure."""
    all_funcs = project.all_functions
    alloyed = detect_alloys(all_funcs)
    pure = find_pure_functions(all_funcs)

    return {
        "alloyed": alloyed,
        "pure": pure,
    }
