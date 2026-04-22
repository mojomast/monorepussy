"""Crack scanner — detects flaws, workarounds, and tech debt markers in code.

Uses Python's stdlib ast module for AST-based analysis and regex for
pattern matching on comments.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Optional

from .models import Crack, CrackType, ModuleMetrics, TrendDirection


# Patterns for TODO/FIXME/HACK detection
TODO_PATTERNS = [
    re.compile(r'#\s*TODO', re.IGNORECASE),
    re.compile(r'#\s*FIXME', re.IGNORECASE),
    re.compile(r'#\s*HACK', re.IGNORECASE),
    re.compile(r'#\s*XXX', re.IGNORECASE),
    re.compile(r'#\s*BODGE', re.IGNORECASE),
    re.compile(r'#\s*WORKAROUND', re.IGNORECASE),
]

# Complexity thresholds
HIGH_COMPLEXITY_THRESHOLD = 10
GOD_CLASS_METHOD_THRESHOLD = 12
GOD_CLASS_COMPLEXITY_THRESHOLD = 50


class CrackScanner:
    """Scans Python source files for cracks (flaws, tech debt markers)."""

    def __init__(
        self,
        high_complexity_threshold: int = HIGH_COMPLEXITY_THRESHOLD,
        god_class_method_threshold: int = GOD_CLASS_METHOD_THRESHOLD,
        god_class_complexity_threshold: int = GOD_CLASS_COMPLEXITY_THRESHOLD,
    ):
        self.high_complexity_threshold = high_complexity_threshold
        self.god_class_method_threshold = god_class_method_threshold
        self.god_class_complexity_threshold = god_class_complexity_threshold

    def scan_file(self, file_path: str) -> list[Crack]:
        """Scan a single Python file for cracks."""
        cracks: list[Crack] = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
        except (OSError, IOError):
            return cracks

        # Parse AST
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return cracks

        lines = source.splitlines()

        # 1. Detect TODO/FIXME/HACK comments
        cracks.extend(self._detect_todo_cracks(file_path, lines))

        # 2. Detect high complexity functions
        cracks.extend(self._detect_complexity_cracks(file_path, tree))

        # 3. Detect missing error handling
        cracks.extend(self._detect_missing_error_handling(file_path, tree))

        # 4. Detect god classes
        cracks.extend(self._detect_god_classes(file_path, tree))

        return cracks

    def scan_directory(self, directory: str) -> list[Crack]:
        """Recursively scan a directory for cracks."""
        cracks: list[Crack] = []
        dir_path = Path(directory)

        if not dir_path.is_dir():
            return cracks

        for py_file in dir_path.rglob("*.py"):
            cracks.extend(self.scan_file(str(py_file)))

        return cracks

    def _detect_todo_cracks(self, file_path: str, lines: list[str]) -> list[Crack]:
        """Detect TODO/FIXME/HACK comment cracks."""
        cracks: list[Crack] = []

        for i, line in enumerate(lines, start=1):
            for pattern in TODO_PATTERNS:
                if pattern.search(line):
                    # Determine severity based on keyword
                    line_upper = line.upper()
                    if 'HACK' in line_upper or 'XXX' in line_upper:
                        severity = 6.0
                    elif 'FIXME' in line_upper:
                        severity = 5.0
                    else:
                        severity = 3.0

                    # Adjust severity based on context
                    stripped = line.strip()
                    severity = min(10.0, severity + len(stripped) / 50.0)

                    cracks.append(Crack(
                        crack_type=CrackType.TODO_FIXME_HACK,
                        file_path=file_path,
                        line_number=i,
                        severity=round(severity, 1),
                        description=stripped[:80],
                    ))
                    break  # Only one crack per line

        return cracks

    def _detect_complexity_cracks(self, file_path: str, tree: ast.AST) -> list[Crack]:
        """Detect functions/methods with high cyclomatic complexity."""
        cracks: list[Crack] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._cyclomatic_complexity(node)
                if complexity > self.high_complexity_threshold:
                    severity = min(10.0, 3.0 + (complexity - self.high_complexity_threshold) * 0.5)
                    cracks.append(Crack(
                        crack_type=CrackType.HIGH_COMPLEXITY,
                        file_path=file_path,
                        line_number=node.lineno,
                        severity=round(severity, 1),
                        description=f"Function '{node.name}' has cyclomatic complexity {complexity}",
                        details=f"Threshold is {self.high_complexity_threshold}",
                    ))

        return cracks

    def _detect_missing_error_handling(self, file_path: str, tree: ast.AST) -> list[Crack]:
        """Detect potential missing error handling patterns."""
        cracks: list[Crack] = []

        for node in ast.walk(tree):
            # Functions that call potentially-exception-raising operations
            # but have no try/except
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                has_try = any(
                    isinstance(child, ast.Try)
                    for child in ast.walk(node)
                )
                has_risky_call = False
                risky_names = set()

                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func_name = self._get_call_name(child)
                        if func_name and any(
                            risky in func_name
                            for risky in ('open', 'connect', 'request', 'fetch',
                                          'read', 'write', 'delete', 'execute',
                                          'query', 'socket')
                        ):
                            has_risky_call = True
                            risky_names.add(func_name)

                if has_risky_call and not has_try:
                    severity = min(10.0, 4.0 + len(risky_names) * 1.5)
                    cracks.append(Crack(
                        crack_type=CrackType.MISSING_ERROR_HANDLING,
                        file_path=file_path,
                        line_number=node.lineno,
                        severity=round(severity, 1),
                        description=f"Function '{node.name}' calls {', '.join(risky_names)} without try/except",
                        details=f"{len(risky_names)} unhandled error path(s)",
                    ))

        return cracks

    def _detect_god_classes(self, file_path: str, tree: ast.AST) -> list[Crack]:
        """Detect god classes (too many methods and/or too much complexity)."""
        cracks: list[Crack] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [
                    n for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                num_methods = len(methods)
                total_complexity = sum(
                    self._cyclomatic_complexity(m) for m in methods
                )

                if (num_methods >= self.god_class_method_threshold or
                        total_complexity >= self.god_class_complexity_threshold):
                    severity = min(10.0, 5.0 + num_methods * 0.3 + total_complexity * 0.05)
                    cracks.append(Crack(
                        crack_type=CrackType.GOD_CLASS,
                        file_path=file_path,
                        line_number=node.lineno,
                        severity=round(severity, 1),
                        description=f"Class '{node.name}' ({num_methods} methods, cyclomatic {total_complexity})",
                        details=f"Method threshold: {self.god_class_method_threshold}, "
                                f"Complexity threshold: {self.god_class_complexity_threshold}",
                    ))

        return cracks

    def compute_module_metrics(self, file_path: str) -> ModuleMetrics:
        """Compute module-level metrics for a Python file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
        except (OSError, IOError):
            return ModuleMetrics(file_path=file_path)

        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return ModuleMetrics(file_path=file_path)

        lines = source.splitlines()
        loc = len([l for l in lines if l.strip() and not l.strip().startswith('#')])

        # Cyclomatic complexity (sum of all functions)
        total_complexity = 0
        num_methods = 0
        max_nesting = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_complexity += self._cyclomatic_complexity(node)
                num_methods += 1
                nesting = self._max_nesting_depth(node)
                max_nesting = max(max_nesting, nesting)

        # Complexity normalized by LOC (per 100 LOC)
        complexity_normalized = (total_complexity / max(loc, 1)) * 100

        # Adjust for nesting depth
        complexity_normalized *= (1 + max_nesting * 0.1)

        # Count imports for fan-out
        fan_out = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                fan_out += 1

        return ModuleMetrics(
            file_path=file_path,
            complexity=round(complexity_normalized, 2),
            lines_of_code=loc,
            cyclomatic_complexity=total_complexity,
            num_methods=num_methods,
            fan_out=fan_out,
            nesting_depth=max_nesting,
        )

    @staticmethod
    def _cyclomatic_complexity(node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function node."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Decision points
            if isinstance(child, (ast.If, ast.IfExp)):
                complexity += 1
            elif isinstance(child, ast.For):
                complexity += 1
            elif isinstance(child, ast.While):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
            elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                complexity += 1
            # Boolean operators
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            # Ternary
            elif isinstance(child, ast.IfExp):
                complexity += 1

        return complexity

    @staticmethod
    def _max_nesting_depth(node: ast.AST, current: int = 0) -> int:
        """Calculate maximum nesting depth within a function."""
        max_depth = current

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With,
                                  ast.Try, ast.ExceptHandler)):
                child_depth = CrackScanner._max_nesting_depth(child, current + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = CrackScanner._max_nesting_depth(child, current)
                max_depth = max(max_depth, child_depth)

        return max_depth

    @staticmethod
    def _get_call_name(call_node: ast.Call) -> Optional[str]:
        """Extract a readable name from a Call node."""
        func = call_node.func
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            return func.attr
        return None


def detect_circular_dependencies(
    import_graph: dict[str, set[str]]
) -> list[tuple[str, ...]]:
    """Detect circular dependencies in an import graph.

    Args:
        import_graph: Mapping from module name to set of imported module names.

    Returns:
        List of cycles, each cycle represented as a tuple of module names.
    """
    cycles: list[tuple[str, ...]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in import_graph.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = tuple(path[cycle_start:])
                if len(cycle) > 1:
                    cycles.append(cycle)

        path.pop()
        rec_stack.discard(node)

    for node in import_graph:
        if node not in visited:
            dfs(node)

    return cycles


def build_import_graph(directory: str) -> dict[str, set[str]]:
    """Build an import graph from a directory of Python files.

    Returns:
        Mapping from module path to set of module paths it imports.
    """
    graph: dict[str, set[str]] = {}
    dir_path = Path(directory)

    if not dir_path.is_dir():
        return graph

    # First pass: collect all modules
    modules: dict[str, str] = {}  # module_name -> file_path
    for py_file in dir_path.rglob("*.py"):
        rel = py_file.relative_to(dir_path)
        module_name = str(rel.with_suffix("")).replace(os.sep, ".")
        modules[module_name] = str(py_file)

    # Second pass: resolve imports
    for module_name, file_path in modules.items():
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
            tree = ast.parse(source, filename=file_path)
        except (OSError, SyntaxError):
            continue

        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in modules:
                        imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module in modules:
                    imports.add(node.module)

        graph[module_name] = imports

    return graph
