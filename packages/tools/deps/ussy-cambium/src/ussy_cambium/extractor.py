"""AST-based interface extraction for Python source files."""

from __future__ import annotations

import ast
from typing import Any

from ussy_cambium.models import InterfaceInfo


def extract_interface(source: str, module_name: str = "") -> InterfaceInfo:
    """Extract interface information from Python source code using AST parsing.

    Returns an InterfaceInfo with exported types, functions, method signatures,
    and preconditions.
    """
    info = InterfaceInfo(name=module_name)

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return info

    _all_names: set[str] = set()

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                _all_names.add(elt.value)

        elif isinstance(node, ast.ClassDef):
            info.exported_types.add(node.name)
            methods: list[str] = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)
                    sig_parts = _extract_signature(item)
                    info.method_signatures[f"{node.name}.{item.name}"] = sig_parts
            # Also add class-level attributes (assignments in class body)
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    methods.append(item.target.id)

        elif isinstance(node, ast.FunctionDef):
            info.exported_functions.add(node.name)
            sig_parts = _extract_signature(node)
            info.method_signatures[node.name] = sig_parts

        elif isinstance(node, ast.AsyncFunctionDef):
            info.exported_functions.add(node.name)
            sig_parts = _extract_signature(node)
            info.method_signatures[node.name] = sig_parts

    # If __all__ is defined, filter to only exported names
    if _all_names:
        info.exported_types = info.exported_types & _all_names
        info.exported_functions = info.exported_functions & _all_names
        info.method_signatures = {
            k: v for k, v in info.method_signatures.items()
            if k.split(".")[0] in _all_names or k in _all_names
        }

    # Extract preconditions from docstrings or assertions
    info.preconditions = _extract_preconditions(tree)

    return info


def _extract_signature(func_node: ast.FunctionDef) -> list[str]:
    """Extract parameter signature from a function AST node."""
    params: list[str] = []
    args = func_node.args

    for arg in args.posonlyargs:
        params.append(_format_arg(arg))

    for arg in args.args:
        if arg.arg != "self":
            params.append(_format_arg(arg))

    if args.vararg:
        params.append(f"*{args.vararg.arg}")

    for arg in args.kwonlyargs:
        params.append(_format_arg(arg))

    if args.kwarg:
        params.append(f"**{args.kwarg.arg}")

    return params


def _format_arg(arg: ast.arg) -> str:
    """Format a single argument with type annotation if present."""
    name = arg.arg
    if arg.annotation:
        ann = ast.unparse(arg.annotation) if hasattr(ast, "unparse") else ""
        if ann:
            return f"{name}: {ann}"
    return name


def _extract_preconditions(tree: ast.Module) -> list[str]:
    """Extract precondition-like assertions from AST."""
    preconditions: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            if isinstance(node.test, ast.Compare):
                if isinstance(node.test.left, ast.Name):
                    preconditions.append(node.test.left.id)
            elif isinstance(node.test, ast.Name):
                preconditions.append(node.test.id)

    return preconditions


def extract_interface_from_file(path: str) -> InterfaceInfo:
    """Extract interface from a Python source file."""
    try:
        with open(path, "r") as f:
            source = f.read()
    except (OSError, IOError):
        return InterfaceInfo(name=path)

    module_name = path.rsplit("/", 1)[-1].replace(".py", "") if "/" in path else path.replace(".py", "")
    return extract_interface(source, module_name)


def extract_interfaces_from_directory(directory: str) -> dict[str, InterfaceInfo]:
    """Extract interfaces from all Python files in a directory."""
    import os

    result: dict[str, InterfaceInfo] = {}
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            if fname.endswith(".py") and not fname.startswith("__"):
                fpath = os.path.join(root, fname)
                info = extract_interface_from_file(fpath)
                if info.name:
                    result[info.name] = info

    return result
