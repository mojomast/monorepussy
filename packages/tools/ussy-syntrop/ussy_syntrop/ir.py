"""Intermediate Representation layer for Syntrop.

The IR captures the essential semantics of source code:
- Pure functions (no side effects)
- Data flow (what depends on what)
- Control flow (branches, loops)
- State mutations (reads/writes to shared state)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional


class IRNodeType(Enum):
    """Types of nodes in the IR tree."""

    FUNCTION = auto()
    BLOCK = auto()
    ASSIGN = auto()
    RETURN = auto()
    FOR_EACH = auto()
    FOR_RANGE = auto()
    WHILE = auto()
    IF = auto()
    CALL = auto()
    MUTATE = auto()
    ACCUM = auto()
    BINARY_OP = auto()
    UNARY_OP = auto()
    LITERAL = auto()
    IDENTIFIER = auto()
    SUBSCRIPT = auto()
    ATTRIBUTE = auto()
    COMPARE = auto()
    BOOLEAN_OP = auto()


class Mutability(Enum):
    """Mutability classification for variables."""

    IMMUTABLE = "immutable"
    ACCUMULATOR = "accumulator"
    MUTABLE = "mutable"


@dataclass
class IRNode:
    """Base node in the Syntrop IR."""

    node_type: IRNodeType
    children: list[IRNode] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)

    def pretty(self, indent: int = 0) -> str:
        """Pretty-print the IR tree."""
        prefix = "  " * indent
        label = self.node_type.name
        attrs = ""
        if self.attributes:
            attr_parts = [f"{k}={v!r}" for k, v in self.attributes.items()]
            attrs = f" ({', '.join(attr_parts)})"
        lines = [f"{prefix}{label}{attrs}"]
        for child in self.children:
            lines.append(child.pretty(indent + 1))
        return "\n".join(lines)


@dataclass
class IRFunction:
    """A function in the IR."""

    name: str
    params: list[tuple[str, Optional[str]]] = field(default_factory=list)
    return_type: Optional[str] = None
    body: IRNode = field(default_factory=lambda: IRNode(IRNodeType.BLOCK))

    def pretty(self) -> str:
        """Pretty-print the function IR."""
        params_str = ", ".join(
            f"{name}: {typ}" if typ else name for name, typ in self.params
        )
        ret = f" -> {self.return_type}" if self.return_type else ""
        header = f"FUNC {self.name}({params_str}){ret}:"
        return header + "\n" + self.body.pretty(1)


@dataclass
class IRModule:
    """A module containing multiple IR functions."""

    name: str = "<module>"
    functions: list[IRFunction] = field(default_factory=list)
    globals_: list[tuple[str, Mutability, Any]] = field(default_factory=list)

    def pretty(self) -> str:
        """Pretty-print the module IR."""
        lines = [f"MODULE {self.name}:"]
        for gname, mut, val in self.globals_:
            lines.append(f"  GLOBAL {gname} [{mut.value}] = {val!r}")
        for func in self.functions:
            lines.append(func.pretty())
        return "\n".join(lines)


@dataclass
class ProbeResult:
    """Result from running a semantic probe on code."""

    probe_name: str
    original_output: Any = None
    probed_output: Any = None
    diverged: bool = False
    divergence_type: str = ""
    explanation: str = ""
    severity: str = "info"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanResult:
    """Result from scanning a file/directory for behavioral assumptions."""

    path: str
    assumptions: list[dict[str, Any]] = field(default_factory=list)
    probe_results: list[ProbeResult] = field(default_factory=list)
    summary: str = ""


@dataclass
class DiffResult:
    """Result from comparing behavior across probe modes."""

    file_path: str
    modes_compared: list[str] = field(default_factory=list)
    divergences: list[dict[str, Any]] = field(default_factory=list)
    consistent: bool = True
    summary: str = ""
