"""Core utilities for AST parsing helpers."""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Line/column range for a node in source code."""

    start_line: int
    start_col: int
    end_line: int
    end_col: int


@dataclass(frozen=True, slots=True)
class FunctionInfo:
    """Metadata extracted from a function or method definition."""

    name: str
    location: SourceLocation
    is_async: bool
    args_count: int
    has_varargs: bool
    has_kwargs: bool
    decorators: list[str]
    docstring: str | None
    complexity: int


@dataclass(frozen=True, slots=True)
class ClassInfo:
    """Metadata extracted from a class definition."""

    name: str
    location: SourceLocation
    bases: list[str]
    methods: list[FunctionInfo]
    docstring: str | None


def parse_source(source: str, filename: str = "<unknown>") -> ast.AST:
    """Parse Python source into an AST.

    Args:
        source: Python source code.
        filename: Filename for error messages.

    Returns:
        Parsed AST module node.

    Raises:
        SyntaxError: If the source is invalid.
    """
    return ast.parse(source, filename=filename)


def _get_docstring(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
) -> str | None:
    """Return the docstring of a node, or ``None`` if absent."""
    doc = ast.get_docstring(node)
    return doc


def _node_location(node: ast.AST) -> SourceLocation:
    """Build a :class:`SourceLocation` from an AST node."""
    assert hasattr(node, "lineno")
    assert hasattr(node, "col_offset")
    assert hasattr(node, "end_lineno")
    assert hasattr(node, "end_col_offset")
    return SourceLocation(
        start_line=node.lineno,  # type: ignore[attr-defined]
        start_col=node.col_offset,  # type: ignore[attr-defined]
        end_line=node.end_lineno,  # type: ignore[attr-defined]
        end_col=node.end_col_offset,  # type: ignore[attr-defined]
    )


def _extract_decorators(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
) -> list[str]:
    """Return decorator names as strings."""
    names: list[str] = []
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name):
            names.append(decorator.id)
        elif isinstance(decorator, ast.Attribute):
            names.append(f"{ast.unparse(decorator.value)}.{decorator.attr}")
        elif isinstance(decorator, ast.Call):
            names.append(ast.unparse(decorator.func))
    return names


def _count_args(args: ast.arguments) -> tuple[int, bool, bool]:
    """Return (positional_count, has_varargs, has_kwargs)."""
    pos = len(args.args) + len(args.posonlyargs)
    has_varargs = args.vararg is not None
    has_kwargs = args.kwarg is not None
    return pos, has_varargs, has_kwargs


def get_cyclomatic_complexity(node: ast.AST) -> int:
    """Calculate cyclomatic complexity for an AST node.

    Complexity starts at 1 and increments for each branch point:
    ``if``, ``for``, ``while``, ``except``, ``with``, ``assert``,
    comprehensions, boolean operators, and ternary expressions.

    Args:
        node: AST node (typically a function or method definition).

    Returns:
        Cyclomatic complexity score.
    """
    complexity = 1

    for child in ast.walk(node):
        if child is node:
            continue
        if isinstance(
            child,
            (
                ast.If,
                ast.For,
                ast.While,
                ast.ExceptHandler,
                ast.With,
                ast.Assert,
                ast.ListComp,
                ast.SetComp,
                ast.GeneratorExp,
                ast.DictComp,
                ast.BoolOp,
                ast.IfExp,
            ),
        ):
            complexity += 1
        elif isinstance(child, ast.Match):
            complexity += len(child.cases)

    return complexity


def extract_functions(tree: ast.AST) -> list[FunctionInfo]:
    """Extract top-level and nested function definitions from an AST.

    Args:
        tree: Parsed AST module.

    Returns:
        List of :class:`FunctionInfo` objects.
    """
    functions: list[FunctionInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            pos, has_varargs, has_kwargs = _count_args(node.args)
            functions.append(
                FunctionInfo(
                    name=node.name,
                    location=_node_location(node),
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    args_count=pos,
                    has_varargs=has_varargs,
                    has_kwargs=has_kwargs,
                    decorators=_extract_decorators(node),
                    docstring=_get_docstring(node),
                    complexity=get_cyclomatic_complexity(node),
                )
            )

    return functions


def extract_classes(tree: ast.AST) -> list[ClassInfo]:
    """Extract class definitions from an AST.

    Args:
        tree: Parsed AST module.

    Returns:
        List of :class:`ClassInfo` objects.
    """
    classes: list[ClassInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods: list[FunctionInfo] = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    pos, has_varargs, has_kwargs = _count_args(item.args)
                    methods.append(
                        FunctionInfo(
                            name=item.name,
                            location=_node_location(item),
                            is_async=isinstance(item, ast.AsyncFunctionDef),
                            args_count=pos,
                            has_varargs=has_varargs,
                            has_kwargs=has_kwargs,
                            decorators=_extract_decorators(item),
                            docstring=_get_docstring(item),
                            complexity=get_cyclomatic_complexity(item),
                        )
                    )

            bases: list[str] = []
            for base in node.bases:
                bases.append(ast.unparse(base))

            classes.append(
                ClassInfo(
                    name=node.name,
                    location=_node_location(node),
                    bases=bases,
                    methods=methods,
                    docstring=_get_docstring(node),
                )
            )

    return classes
