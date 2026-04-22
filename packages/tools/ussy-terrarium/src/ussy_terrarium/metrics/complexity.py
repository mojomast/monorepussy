"""Cyclomatic complexity analysis via Python's AST module."""

import ast
import os
from typing import Dict, List, Optional, Tuple

from .models import ModuleMetrics


class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor that computes cyclomatic complexity for each function."""

    def __init__(self) -> None:
        self.functions: List[Dict] = []
        self._current_function: Optional[str] = None
        self._current_complexity: int = 0
        self._current_line: int = 0

    def _complexity_nodes(self) -> tuple:
        """AST node types that increase complexity."""
        return (
            ast.If, ast.For, ast.While, ast.ExceptHandler,
            ast.With, ast.BoolOp,
        )

    def _increment_complexity(self, node: ast.AST) -> None:
        if self._current_function is not None:
            self._current_complexity += 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        old_function = self._current_function
        old_complexity = self._current_complexity
        old_line = self._current_line

        self._current_function = node.name
        self._current_complexity = 1  # Base complexity
        self._current_line = node.lineno

        self.generic_visit(node)

        self.functions.append({
            "name": self._current_function,
            "line": self._current_line,
            "complexity": self._current_complexity,
        })

        self._current_function = old_function
        self._current_complexity = old_complexity
        self._current_line = old_line

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_If(self, node: ast.If) -> None:
        self._increment_complexity(node)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._increment_complexity(node)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._increment_complexity(node)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._increment_complexity(node)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self._increment_complexity(node)
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Each 'and'/'or' beyond the first adds complexity
        self._increment_complexity(node)
        self.generic_visit(node)


def analyze_complexity(source: str) -> Tuple[int, List[Dict]]:
    """Analyze cyclomatic complexity of Python source code.

    Args:
        source: Python source code string.

    Returns:
        (total_complexity, list of function info dicts)
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0, []

    visitor = ComplexityVisitor()
    visitor.visit(tree)

    total = sum(f["complexity"] for f in visitor.functions)
    return total, visitor.functions


def analyze_file_complexity(filepath: str) -> Tuple[int, List[Dict]]:
    """Analyze cyclomatic complexity of a Python file.

    Returns:
        (total_complexity, list of function info dicts)
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except (OSError, IOError):
        return 0, []

    return analyze_complexity(source)


def analyze_directory_complexity(root_path: str) -> Dict[str, Tuple[int, List[Dict]]]:
    """Analyze complexity for all Python files in a directory tree.

    Returns:
        Dict mapping relative path -> (total_complexity, functions list)
    """
    results = {}
    for dirpath, _dirnames, filenames in os.walk(root_path):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            filepath = os.path.join(dirpath, filename)
            relpath = os.path.relpath(filepath, root_path)
            results[relpath] = analyze_file_complexity(filepath)
    return results
