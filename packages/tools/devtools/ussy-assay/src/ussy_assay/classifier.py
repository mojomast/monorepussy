"""AST-based statement classifier — the heart of Assay.

Classifies each line of a Python function into one of the Category enums
using heuristic pattern matching on the AST.
"""

from __future__ import annotations

import ast
import re
from typing import Optional

from ussy_assay.models import Category, ClassifiedLine, FunctionAnalysis

# ---------------------------------------------------------------------------
# Pattern constants
# ---------------------------------------------------------------------------

_LOGGING_NAMES = frozenset({"logger", "log", "logging", "LOGGER", "LOG"})
_DEBUG_LOG_METHODS = frozenset({"debug", "trace"})
_LOG_METHODS = frozenset({"debug", "trace", "info", "warning", "warn", "error", "critical", "exception", "log"})

_FRAMEWORK_PATTERNS = re.compile(
    r"^(request|response|session|db|database|cursor|conn|connection|"
    r"client|api|app|flask|django|fastapi|sqlalchemy|orm|"
    r"redis|mongo|boto|urllib|httpx|aiohttp|requests)\b",
    re.IGNORECASE,
)

_TODO_PATTERN = re.compile(r"#\s*(TODO|FIXME|HACK|XXX|BUG|WORKAROUND)\b", re.IGNORECASE)
_COMMENTED_CODE_PATTERN = re.compile(r"^\s*#\s*(def |class |import |from |if |for |while |return |raise |assert )")

# Names that suggest validation / guard behaviour
_VALIDATION_NAMES = frozenset({
    "validate", "check", "assert", "verify", "ensure", "require",
    "is_valid", "is_valid", "is_allowed", "is_permitted",
    "must_", "should_", "guard", "precondition",
})

_ERROR_NAMES = frozenset({
    "raise", "except", "try", "finally", "error", "exception",
    "handle_error", "catch",
})


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def classify_source(source: str, file_path: str = "<string>") -> list[FunctionAnalysis]:
    """Parse *source* and classify every function definition found."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    analyses: list[FunctionAnalysis] = []
    source_lines = source.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            analysis = _classify_function(node, source_lines, file_path)
            analyses.append(analysis)

    return analyses


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _classify_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source_lines: list[str],
    file_path: str,
) -> FunctionAnalysis:
    """Classify every line in a single function."""
    start = node.lineno
    end = getattr(node, "end_lineno", start)
    lines: list[ClassifiedLine] = []

    # Build a map of line_number -> ast node(s) for fine classification
    line_categories = _build_line_category_map(node, source_lines)

    for line_no in range(start, end + 1):
        idx = line_no - 1
        content = source_lines[idx] if idx < len(source_lines) else ""
        stripped = content.strip()

        # Skip blank lines
        if not stripped:
            continue

        is_comment = stripped.startswith("#")

        # Determine category — explicit line map takes precedence
        cat = line_categories.get(line_no, None)
        if cat is None:
            cat = _classify_line_heuristic(content, line_no, node, source_lines)

        lines.append(ClassifiedLine(
            line_number=line_no,
            content=content,
            category=cat,
            is_comment=is_comment,
        ))

    return FunctionAnalysis(
        name=node.name,
        file_path=file_path,
        start_line=start,
        end_line=end,
        lines=lines,
    )


def _build_line_category_map(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source_lines: list[str],
) -> dict[int, Category]:
    """Walk AST children of *node* and map line numbers to categories."""
    mapping: dict[int, Category] = {}

    for child in ast.walk(node):
        # Error handling
        if isinstance(child, ast.ExceptHandler):
            for ln in _node_lines(child):
                mapping.setdefault(ln, Category.ERROR_HANDLING)

        # Try/except — the try itself
        if isinstance(child, ast.Try):
            for ln in _node_lines(child):
                if ln not in mapping:
                    mapping[ln] = Category.ERROR_HANDLING

        # Raise statements
        if isinstance(child, ast.Raise):
            for ln in _node_lines(child):
                mapping[ln] = Category.ERROR_HANDLING

        # Assert — validation
        if isinstance(child, ast.Assert):
            for ln in _node_lines(child):
                mapping[ln] = Category.VALIDATION

        # Logging calls
        if isinstance(child, ast.Call):
            if _is_logging_call(child):
                cat = Category.SLAG if _is_debug_log(child) else Category.LOGGING
                for ln in _node_lines(child):
                    mapping[ln] = cat
            elif _is_framework_call(child):
                for ln in _node_lines(child):
                    mapping[ln] = Category.FRAMEWORK

    return mapping


def _classify_line_heuristic(
    content: str,
    line_no: int,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source_lines: list[str],
) -> Category:
    """Heuristic classification when AST map doesn't cover a line."""
    stripped = content.strip()

    # Comments
    if stripped.startswith("#"):
        if _TODO_PATTERN.search(stripped):
            return Category.SLAG
        if _COMMENTED_CODE_PATTERN.match(stripped):
            return Category.SLAG
        return Category.UNKNOWN  # regular comments

    # Decorators — framework
    if stripped.startswith("@"):
        return Category.FRAMEWORK

    # logging patterns in raw text
    if re.search(r"(logger|logging|LOG)\.\w+\(", stripped):
        if re.search(r"\.(debug|trace)\(", stripped):
            return Category.SLAG
        return Category.LOGGING

    # print in non-test code
    if re.search(r"\bprint\s*\(", stripped):
        return Category.LOGGING

    # Guard / validation patterns
    if re.match(r"^\s*(if\s+.*:\s*$|if\s+not\s+|if\s+\w+\s+is\s+None)", stripped):
        # Check if next non-blank line is return/raise — suggests guard clause
        next_content = _next_non_blank(line_no, source_lines)
        if next_content and (
            next_content.strip().startswith("return ")
            or next_content.strip().startswith("raise ")
            or next_content.strip() == "return"
        ):
            return Category.VALIDATION

    # Error message construction
    if re.search(r'(Error|Exception|err_msg|error_msg|error_message)\s*=\s*["\']', stripped):
        return Category.ERROR_HANDLING

    # return/raise in error context
    if re.match(r"^\s*raise\s+", stripped):
        return Category.ERROR_HANDLING

    # Pass in except/finally — error handling
    if stripped == "pass":
        return Category.UNKNOWN

    # Type checking / validation calls
    if re.search(r"\b(isinstance|issubclass|hasattr|type\()\b", stripped):
        return Category.VALIDATION

    # Default: business logic
    return Category.BUSINESS


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _node_lines(node: ast.AST) -> range:
    """Return range of line numbers covered by an AST node."""
    start = getattr(node, "lineno", -1)
    end = getattr(node, "end_lineno", start)
    if start == -1:
        return range(0)
    return range(start, end + 1)


def _is_logging_call(call: ast.Call) -> bool:
    """Check if a Call node is a logging call like logger.info(...)."""
    func = call.func
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name) and func.value.id in _LOGGING_NAMES:
            return True
        if isinstance(func.value, ast.Attribute):
            if isinstance(func.value.value, ast.Name) and func.value.value.id in _LOGGING_NAMES:
                return True
    return False


def _is_debug_log(call: ast.Call) -> bool:
    """Check if a logging call is at debug/trace level (slag)."""
    func = call.func
    if isinstance(func, ast.Attribute):
        if func.attr in _DEBUG_LOG_METHODS:
            return True
        # logger.log(logging.DEBUG, ...)
        if func.attr == "log" and call.args:
            first_arg = call.args[0]
            if (
                isinstance(first_arg, ast.Attribute)
                and isinstance(first_arg.value, ast.Name)
                and first_arg.value.id == "logging"
                and first_arg.attr in ("DEBUG", "NOTSET")
            ):
                return True
    return False


def _is_framework_call(call: ast.Call) -> bool:
    """Check if a Call node appears to interact with external frameworks."""
    func = call.func
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            name = func.value.id.lower()
            if _FRAMEWORK_PATTERNS.match(name):
                return True
            # Common ORM / framework method patterns
            if func.attr in (
                "execute", "fetchone", "fetchall", "commit", "rollback",
                "query", "filter", "save", "delete", "update",
                "get", "post", "put", "patch", "delete",
                "render", "redirect", "jsonify",
            ):
                return True
    if isinstance(func, ast.Name):
        if func.id in ("super",):
            return Category.FRAMEWORK  # type: ignore[return-value]
    return False


def _next_non_blank(line_no: int, source_lines: list[str]) -> Optional[str]:
    """Return the next non-blank line after *line_no*."""
    for i in range(line_no, len(source_lines)):
        if source_lines[i].strip():
            return source_lines[i]
    return None
