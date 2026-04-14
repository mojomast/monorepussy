"""Dead code detection — find unused exports and unreachable code."""

import ast
import os
from typing import Dict, List, Optional, Set, Tuple


class ImportCollector(ast.NodeVisitor):
    """Collect all imports from a file."""

    def __init__(self) -> None:
        self.imports: List[str] = []
        self.from_imports: Dict[str, List[str]] = {}

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            names = [alias.name for alias in node.names]
            self.from_imports.setdefault(node.module, []).extend(names)
        self.generic_visit(node)


class ExportCollector(ast.NodeVisitor):
    """Collect all top-level definitions (exports) from a file."""

    def __init__(self) -> None:
        self.exports: Set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if not node.name.startswith("_"):
            self.exports.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if not node.name.startswith("_"):
            self.exports.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if not node.name.startswith("_"):
            self.exports.add(node.name)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name) and not target.id.startswith("_"):
                self.exports.add(target.id)


def find_unused_exports(source: str, project_imports: Optional[Set[str]] = None) -> List[str]:
    """Find exported symbols that are never imported anywhere in the project.

    Args:
        source: Python source code to analyze.
        project_imports: Set of all symbols imported across the project.

    Returns:
        List of unused export names.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    collector = ExportCollector()
    collector.visit(tree)

    if project_imports is None:
        return []

    unused = collector.exports - project_imports
    return sorted(unused)


def analyze_file_dead_code(filepath: str) -> Tuple[List[str], List[str]]:
    """Analyze a file for dead code.

    Returns:
        (unused_exports, imports_list)
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except (OSError, IOError):
        return [], []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [], []

    import_collector = ImportCollector()
    import_collector.visit(tree)

    imports = import_collector.imports[:]
    for module, names in import_collector.from_imports.items():
        imports.append(module)

    # Find exports (don't check project-wide imports here)
    export_collector = ExportCollector()
    export_collector.visit(tree)

    return sorted(export_collector.exports), imports


def scan_project_dead_code(root_path: str) -> Dict[str, List[str]]:
    """Scan an entire project for potentially dead code.

    Returns:
        Dict mapping filepath -> list of potentially unused exports.
    """
    all_imports: Set[str] = set()
    file_exports: Dict[str, Set[str]] = {}

    # First pass: collect all imports and exports
    for dirpath, _dirnames, filenames in os.walk(root_path):
        # Skip hidden dirs and common non-source dirs
        dirs_to_skip = set()
        for d in _dirnames:
            if d.startswith(".") or d in ("__pycache__", "node_modules", ".git"):
                dirs_to_skip.add(d)
        _dirnames[:] = [d for d in _dirnames if d not in dirs_to_skip]

        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            filepath = os.path.join(dirpath, filename)
            relpath = os.path.relpath(filepath, root_path)

            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    source = f.read()
            except OSError:
                continue

            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue

            ic = ImportCollector()
            ic.visit(tree)

            for imp in ic.imports:
                all_imports.add(imp.split(".")[0])
            for module, names in ic.from_imports.items():
                all_imports.add(module.split(".")[-1])
                for name in names:
                    all_imports.add(name)

            ec = ExportCollector()
            ec.visit(tree)
            file_exports[relpath] = ec.exports

    # Second pass: find unused exports
    result = {}
    for filepath, exports in file_exports.items():
        unused = sorted(exports - all_imports)
        if unused:
            result[filepath] = unused

    return result
