"""Slag detection — identify removable waste in code."""

from __future__ import annotations

import re
from pathlib import Path

from assay.classifier import classify_source
from assay.models import Category, SlagItem, SlagReport, FunctionAnalysis
from assay.scanner import _resolve_paths, read_source


# ---------------------------------------------------------------------------
# Slag detection patterns
# ---------------------------------------------------------------------------

_TODO_PATTERN = re.compile(r"#\s*(TODO|FIXME|HACK|XXX|BUG|WORKAROUND)\b", re.IGNORECASE)
_COMMENTED_CODE_PATTERN = re.compile(
    r"^\s*#\s*(def |class |import |from |if |for |while |return |raise |assert )"
)
_DEBUG_LOG_PATTERN = re.compile(
    r"(logger|logging|LOG)\.(debug|trace)\s*\("
)
_UNREACHABLE_EXCEPT_PATTERN = re.compile(
    r"except\s+(UnicodeError|BufferError|BytesWarning|SystemExit|KeyboardInterrupt)\s*:"
)


def detect_slag_in_function(
    func: FunctionAnalysis,
    source_lines: list[str] | None = None,
) -> list[SlagItem]:
    """Detect slag items within a single function's lines."""
    items: list[SlagItem] = []

    for ln in func.lines:
        # Category already flagged as slag
        if ln.category == Category.SLAG:
            items.append(SlagItem(
                file_path=func.file_path,
                line_number=ln.line_number,
                content=ln.content.strip(),
                slag_type=_classify_slag_type(ln.content),
            ))
            continue

        # Additional heuristic checks on content
        stripped = ln.content.strip()

        # Debug logging not caught by AST
        if _DEBUG_LOG_PATTERN.search(stripped) and ln.category != Category.SLAG:
            items.append(SlagItem(
                file_path=func.file_path,
                line_number=ln.line_number,
                content=stripped,
                slag_type="debug_log",
            ))

        # Unreachable except branches
        if _UNREACHABLE_EXCEPT_PATTERN.search(stripped):
            items.append(SlagItem(
                file_path=func.file_path,
                line_number=ln.line_number,
                content=stripped,
                slag_type="unreachable_branch",
            ))

    return items


def _classify_slag_type(content: str) -> str:
    """Determine the specific type of slag."""
    stripped = content.strip()
    if _TODO_PATTERN.search(stripped):
        return "todo_comment"
    if _COMMENTED_CODE_PATTERN.match(stripped):
        return "commented_out"
    if _DEBUG_LOG_PATTERN.search(stripped):
        return "debug_log"
    if _UNREACHABLE_EXCEPT_PATTERN.search(stripped):
        return "unreachable_branch"
    return "other_slag"


def detect_slag_in_source(file_path: str | Path) -> SlagReport:
    """Detect all slag in a single Python source file."""
    p = Path(file_path)
    source = read_source(p)
    if not source:
        return SlagReport()

    source_lines = source.splitlines()
    func_analyses = classify_source(source, str(p))

    all_items: list[SlagItem] = []

    # Check within functions
    for func in func_analyses:
        items = detect_slag_in_function(func, source_lines)
        all_items.extend(items)

    # Also scan for module-level slag (comments outside functions)
    all_items.extend(_scan_module_level_slag(source_lines, str(p)))

    return SlagReport(items=all_items)


def detect_slag_in_project(path: str | Path) -> SlagReport:
    """Detect all slag in a project directory."""
    files = _resolve_paths(path)
    all_items: list[SlagItem] = []

    for fpath in files:
        report = detect_slag_in_source(fpath)
        all_items.extend(report.items)

    return SlagReport(items=all_items)


def _scan_module_level_slag(
    source_lines: list[str], file_path: str
) -> list[SlagItem]:
    """Scan for slag outside function bodies (module-level)."""
    items: list[SlagItem] = []

    for i, line in enumerate(source_lines, start=1):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue

        if _TODO_PATTERN.search(stripped):
            items.append(SlagItem(
                file_path=file_path,
                line_number=i,
                content=stripped,
                slag_type="todo_comment",
            ))
        elif _COMMENTED_CODE_PATTERN.match(stripped):
            items.append(SlagItem(
                file_path=file_path,
                line_number=i,
                content=stripped,
                slag_type="commented_out",
            ))

    return items


def grade_improvement_estimate(
    current_grade: float,
    total_lines: int,
    slag_lines: int,
) -> float:
    """Estimate grade improvement if all slag were removed."""
    if total_lines <= 0:
        return current_grade
    current_business = current_grade / 100 * total_lines
    new_total = max(1, total_lines - slag_lines)
    return round(current_business / new_total * 100, 1)
