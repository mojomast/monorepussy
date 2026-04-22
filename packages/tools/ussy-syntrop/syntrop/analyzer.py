"""Python source analyzer that extracts behavioral assumptions.

Scans Python source code to detect patterns that may rely on implicit
assumptions about evaluation order, state mutation, iteration order, etc.
"""

from __future__ import annotations

import ast
import textwrap
from dataclasses import dataclass, field
from typing import Any, Optional

from syntrop.ir import Mutability


@dataclass
class BehavioralAssumption:
    """An assumption about execution semantics found in code."""

    kind: str  # iteration-order, eval-order, state-aliasing, timing, etc.
    description: str
    line: int
    col: int = 0
    code_snippet: str = ""
    severity: str = "warning"  # info, warning, error
    related_probes: list[str] = field(default_factory=list)


class AssumptionScanner(ast.NodeVisitor):
    """AST visitor that detects behavioral assumptions in Python code."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.source_lines = source.splitlines()
        self.assumptions: list[BehavioralAssumption] = []

    def _snippet(self, lineno: int, col_offset: int = 0) -> str:
        """Get a code snippet for a given line number."""
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return ""

    def visit_For(self, node: ast.For) -> None:
        """Check for iteration-order assumptions in for-loops."""
        # Iterating over dicts assumes order
        if isinstance(node.iter, ast.Call):
            func = node.iter.func
            if isinstance(func, ast.Name) and func.id in ("dict", "sorted"):
                self.assumptions.append(
                    BehavioralAssumption(
                        kind="iteration-order",
                        description=f"Loop iterates over result of {func.id}(), "
                        "which may have non-deterministic order",
                        line=node.lineno,
                        col=node.col_offset,
                        code_snippet=self._snippet(node.lineno),
                        severity="warning",
                        related_probes=["randomize-iteration"],
                    )
                )
            if isinstance(func, ast.Attribute) and func.attr == "keys":
                self.assumptions.append(
                    BehavioralAssumption(
                        kind="iteration-order",
                        description="Loop iterates over dict.keys(), "
                        "assuming deterministic key order",
                        line=node.lineno,
                        col=node.col_offset,
                        code_snippet=self._snippet(node.lineno),
                        severity="warning",
                        related_probes=["randomize-iteration"],
                    )
                )

        # Iterating over a set assumes no particular order
        if isinstance(node.iter, ast.Call):
            func = node.iter.func
            if isinstance(func, ast.Name) and func.id == "set":
                self.assumptions.append(
                    BehavioralAssumption(
                        kind="iteration-order",
                        description="Loop iterates over a set, which has "
                        "non-deterministic iteration order",
                        line=node.lineno,
                        col=node.col_offset,
                        code_snippet=self._snippet(node.lineno),
                        severity="warning",
                        related_probes=["randomize-iteration"],
                    )
                )

        # Check if loop body modifies the iterable being iterated
        iter_id = None
        if isinstance(node.iter, ast.Name):
            iter_id = node.iter.id
        if iter_id:
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Attribute):
                        if (
                            isinstance(child.func.value, ast.Name)
                            and child.func.value.id == iter_id
                            and child.func.attr
                            in ("append", "extend", "insert", "remove", "pop")
                        ):
                            self.assumptions.append(
                                BehavioralAssumption(
                                    kind="state-mutation-during-iteration",
                                    description=f"Loop modifies iterable "
                                    f"'{iter_id}' while iterating over it",
                                    line=node.lineno,
                                    col=node.col_offset,
                                    code_snippet=self._snippet(node.lineno),
                                    severity="error",
                                    related_probes=[
                                        "randomize-iteration",
                                        "alias-state",
                                    ],
                                )
                            )
                            break

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check for evaluation-order assumptions in function calls."""
        if len(node.args) > 1:
            self.assumptions.append(
                BehavioralAssumption(
                    kind="eval-order",
                    description=f"Function call with {len(node.args)} arguments "
                    "assumes left-to-right evaluation order",
                    line=node.lineno,
                    col=node.col_offset,
                    code_snippet=self._snippet(node.lineno),
                    severity="info",
                    related_probes=["shuffle-evaluation-order"],
                )
            )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check for state aliasing assumptions."""
        # Multiple assignment targets (a = b = expr) creates aliases
        if len(node.targets) > 1:
            self.assumptions.append(
                BehavioralAssumption(
                    kind="state-aliasing",
                    description="Multiple assignment targets create aliases "
                    "that may share state",
                    line=node.lineno,
                    col=node.col_offset,
                    code_snippet=self._snippet(node.lineno),
                    severity="info",
                    related_probes=["alias-state"],
                )
            )
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Check for augmented assignment (+=, etc.) that assumes atomicity."""
        self.assumptions.append(
            BehavioralAssumption(
                kind="timing-atomicity",
                description=f"Augmented assignment ({ast.dump(node.op)}) "
                "assumes read-modify-write is atomic",
                line=node.lineno,
                col=node.col_offset,
                code_snippet=self._snippet(node.lineno),
                severity="info",
                related_probes=["nondeterministic-timing"],
            )
        )
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        """Check for chained comparisons with side effects."""
        if len(node.ops) > 1:
            self.assumptions.append(
                BehavioralAssumption(
                    kind="eval-order",
                    description="Chained comparison assumes left-to-right "
                    "short-circuit evaluation",
                    line=node.lineno,
                    col=node.col_offset,
                    code_snippet=self._snippet(node.lineno),
                    severity="info",
                    related_probes=["shuffle-evaluation-order"],
                )
            )
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        """Check for dict literal assumptions."""
        # Dict literals with duplicate keys
        if node.keys:
            seen_keys: list[str] = []
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    if key.value in seen_keys:
                        self.assumptions.append(
                            BehavioralAssumption(
                                kind="state-aliasing",
                                description=f"Dict literal has duplicate key "
                                f"'{key.value}', last wins",
                                line=node.lineno,
                                col=node.col_offset,
                                code_snippet=self._snippet(node.lineno),
                                severity="warning",
                                related_probes=["alias-state"],
                            )
                        )
                    seen_keys.append(key.value)
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        """Check for list comprehension assumptions."""
        for gen in node.generators:
            if gen.is_async:
                continue
            # comprehension nodes don't have lineno in Python 3.11; use node's line
            lineno = getattr(gen, "lineno", node.lineno)
            col_offset = getattr(gen, "col_offset", node.col_offset)
            self.assumptions.append(
                BehavioralAssumption(
                    kind="iteration-order",
                    description="List comprehension assumes deterministic "
                    "iteration order of generator",
                    line=lineno,
                    col=col_offset,
                    code_snippet=self._snippet(lineno),
                    severity="info",
                    related_probes=["randomize-iteration"],
                )
            )
        self.generic_visit(node)


def scan_source(source: str) -> list[BehavioralAssumption]:
    """Scan Python source code for behavioral assumptions.

    Args:
        source: Python source code as a string.

    Returns:
        List of detected behavioral assumptions.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    scanner = AssumptionScanner(source)
    scanner.visit(tree)
    return scanner.assumptions


def scan_file(path: str) -> list[BehavioralAssumption]:
    """Scan a Python file for behavioral assumptions.

    Args:
        path: Path to the Python file.

    Returns:
        List of detected behavioral assumptions.
    """
    with open(path, "r") as f:
        source = f.read()
    return scan_source(source)
