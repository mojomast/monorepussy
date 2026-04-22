"""AST parser — extract structural fingerprints from Python source files."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

from ussy_crystallo.models import MethodSignature, StructuralFingerprint


def parse_file(file_path: str | Path) -> list[StructuralFingerprint]:
    """Parse a single Python file and extract structural fingerprints.

    Returns one fingerprint per top-level class and function definition.
    """
    path = Path(file_path)
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    fingerprints: list[StructuralFingerprint] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            fp = _extract_class(node, str(path))
            fingerprints.append(fp)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fp = _extract_function(node, str(path))
            fingerprints.append(fp)

    return fingerprints


def parse_directory(directory: str | Path) -> list[StructuralFingerprint]:
    """Walk a directory tree and parse all Python files."""
    directory = Path(directory)
    if not directory.is_dir():
        if directory.is_file():
            return parse_file(directory)
        return []

    fingerprints: list[StructuralFingerprint] = []
    for py_file in sorted(directory.rglob("*.py")):
        fingerprints.extend(parse_file(py_file))
    return fingerprints


def _extract_class(node: ast.ClassDef, file_path: str) -> StructuralFingerprint:
    """Extract a structural fingerprint from a class definition."""
    method_names: list[str] = []
    method_sigs: list[MethodSignature] = []
    attribute_names: list[str] = []
    base_classes: list[str] = []
    decorator_names: list[str] = []
    function_count = 0
    class_count = 0
    has_init = False
    is_abstract = False

    # Base classes
    for base in node.bases:
        base_name = _node_to_name(base)
        if base_name:
            base_classes.append(base_name)

    # Decorators
    for dec in node.decorator_list:
        dec_name = _node_to_name(dec)
        if dec_name:
            decorator_names.append(dec_name)
            if dec_name in ("abstractmethod", "abstract"):
                is_abstract = True

    # Body items
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.FunctionDef) or isinstance(child, ast.AsyncFunctionDef):
            method_names.append(child.name)
            method_sigs.append(_extract_method_sig(child))
            if child.name == "__init__":
                has_init = True
        elif isinstance(child, ast.Assign):
            for target in child.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    attribute_names.append(target.id)
        elif isinstance(child, ast.AnnAssign) and child.target:
            if isinstance(child.target, ast.Name) and not child.target.id.startswith("_"):
                attribute_names.append(child.target.id)
        elif isinstance(child, ast.ClassDef):
            class_count += 1

    # Check for ABC import pattern
    for base in base_classes:
        if base in ("ABC", "ABCMeta"):
            is_abstract = True

    return StructuralFingerprint(
        name=node.name,
        file_path=file_path,
        kind="class",
        method_names=method_names,
        method_signatures=method_sigs,
        attribute_names=attribute_names,
        base_classes=base_classes,
        decorator_names=decorator_names,
        function_count=function_count,
        class_count=class_count,
        has_init=has_init,
        is_abstract=is_abstract,
    )


def _extract_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str
) -> StructuralFingerprint:
    """Extract a structural fingerprint from a function definition."""
    decorator_names: list[str] = []
    for dec in node.decorator_list:
        dec_name = _node_to_name(dec)
        if dec_name:
            decorator_names.append(dec_name)

    is_async = isinstance(node, ast.AsyncFunctionDef)
    is_classmethod = any(d == "classmethod" for d in decorator_names)
    is_staticmethod = any(d == "staticmethod" for d in decorator_names)
    has_return_annotation = node.returns is not None

    # Count arguments (excluding self/cls)
    arg_count = len(node.args.args)
    if arg_count > 0 and node.args.args[0].arg in ("self", "cls"):
        arg_count -= 1

    sig = MethodSignature(
        name=node.name,
        arg_count=arg_count,
        has_return_annotation=has_return_annotation,
        is_async=is_async,
        is_classmethod=is_classmethod,
        is_staticmethod=is_staticmethod,
        decorator_names=decorator_names,
    )

    return StructuralFingerprint(
        name=node.name,
        file_path=file_path,
        kind="function",
        method_signatures=[sig],
        decorator_names=decorator_names,
        has_init=False,
        is_abstract=False,
        is_async=is_async,
    )


def _extract_method_sig(node: ast.FunctionDef | ast.AsyncFunctionDef) -> MethodSignature:
    """Extract a MethodSignature from a function definition node."""
    decorator_names: list[str] = []
    for dec in node.decorator_list:
        dec_name = _node_to_name(dec)
        if dec_name:
            decorator_names.append(dec_name)

    is_async = isinstance(node, ast.AsyncFunctionDef)
    is_classmethod = "classmethod" in decorator_names
    is_staticmethod = "staticmethod" in decorator_names
    has_return_annotation = node.returns is not None

    arg_count = len(node.args.args)
    if arg_count > 0 and node.args.args[0].arg in ("self", "cls"):
        arg_count -= 1

    return MethodSignature(
        name=node.name,
        arg_count=arg_count,
        has_return_annotation=has_return_annotation,
        is_async=is_async,
        is_classmethod=is_classmethod,
        is_staticmethod=is_staticmethod,
        decorator_names=decorator_names,
    )


def _node_to_name(node: ast.expr) -> str:
    """Best-effort conversion of an AST node to a readable name string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _node_to_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _node_to_name(node.func)
    if isinstance(node, ast.Subscript):
        return _node_to_name(node.value)
    return ""
