"""Alias-state probe: makes variables share memory to reveal identity bugs.

Inspired by Befunge's 2D grid where code and data share the same space,
this probe reveals hidden assumptions about variable identity vs. equality.
When variables share underlying storage, modifications to one affect the other.
"""

from __future__ import annotations

import ast
import re
from typing import Any

from syntrop.ir import ProbeResult
from syntrop.probes.base import BaseProbe


class StateAliaser(ast.NodeTransformer):
    """AST transformer that introduces state aliasing between variables."""

    def __init__(self, alias_groups: list[list[str]] | None = None) -> None:
        """Initialize with optional alias groups.

        Each alias group is a list of variable names that should share storage.
        If not provided, the transformer will heuristically create aliases.
        """
        self.alias_groups = alias_groups or []

    def visit_Module(self, node: ast.Module) -> ast.Module:
        """Insert alias setup at the top of the module."""
        self.generic_visit(node)

        if not self.alias_groups:
            return node

        alias_stmts = []
        for group in self.alias_groups:
            if len(group) < 2:
                continue
            # When any variable in the group is assigned, all others get the same value
            # We'll insert a helper class that proxies shared state
            alias_stmts.append(
                ast.parse(
                    f"_syntrop_alias_{group[0]} = _SyntropAlias()\n"
                ).body[0]
            )
            for name in group:
                alias_stmts.append(
                    ast.parse(
                        f"{name} = _syntrop_alias_{group[0]}\n"
                    ).body[0]
                )

        node.body = alias_stmts + node.body
        return node


class AliasStateProbe(BaseProbe):
    """Probe that introduces state aliasing between variables."""

    name = "alias-state"
    description = "Make variables share memory to reveal identity vs. equality bugs"
    twist_type = "state"

    def __init__(self, alias_groups: list[list[str]] | None = None) -> None:
        self.alias_groups = alias_groups

    def transform_source(self, source: str) -> str:
        """Transform source code to introduce state aliasing.

        This is a heuristic transformation: we look for patterns where
        variables are assigned from the same mutable object, and we
        make them truly share the same reference.
        """
        # Simple approach: replace copy/deepcopy calls with identity
        # and add mutation tracking
        transformed = source

        # Replace .copy() with direct reference (for lists and dicts)
        transformed = re.sub(
            r'(\w+)\.copy\(\)',
            r'\1  # syntrop: alias-state removed .copy()',
            transformed,
        )

        # Replace list() wrapping of existing lists with direct reference
        transformed = re.sub(
            r'list\((\w+)\)',
            r'\1  # syntrop: alias-state removed list() copy',
            transformed,
        )

        # Replace dict() wrapping of existing dicts with direct reference
        transformed = re.sub(
            r'dict\((\w+)\)',
            r'\1  # syntrop: alias-state removed dict() copy',
            transformed,
        )

        # Prepend mutation tracker
        helper = (
            "class _SyntropMutationTracker:\n"
            "    def __init__(self, obj):\n"
            "        object.__setattr__(self, '_obj', obj)\n"
            "    def __getattr__(self, name):\n"
            "        return getattr(object.__getattribute__(self, '_obj'), name)\n"
            "    def __repr__(self):\n"
            "        return repr(object.__getattribute__(self, '_obj'))\n"
        )
        return helper + transformed

    def check_divergence(
        self, original_result: Any, probed_result: Any, metadata: dict[str, Any] | None = None
    ) -> ProbeResult:
        """Check if results diverge when state aliasing is introduced."""
        if original_result == probed_result:
            return ProbeResult(
                probe_name=self.name,
                original_output=original_result,
                probed_output=probed_result,
                diverged=False,
                divergence_type="",
                explanation="Results match — no state-aliasing dependency detected",
                severity="info",
            )

        return ProbeResult(
            probe_name=self.name,
            original_output=original_result,
            probed_output=probed_result,
            diverged=True,
            divergence_type="state-alias",
            explanation="Results differ when variables share storage — "
            "the code depends on variables having independent storage (identity vs equality)",
            severity="warning",
        )
