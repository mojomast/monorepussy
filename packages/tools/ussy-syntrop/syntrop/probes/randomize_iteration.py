"""Randomize-iteration probe: shuffles the order of loops and iterations.

Inspired by Brainfuck's sequential tape model, this probe reveals hidden
dependencies on iteration order — a common source of concurrency bugs.
"""

from __future__ import annotations

import ast
import copy
import random
from typing import Any

from syntrop.ir import ProbeResult
from syntrop.probes.base import BaseProbe


class IterationRandomizer(ast.NodeTransformer):
    """AST transformer that randomizes iteration order."""

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed

    def visit_For(self, node: ast.For) -> ast.For:
        """Transform for-loops to shuffle iteration order."""
        self.generic_visit(node)

        # Wrap: for X in list(shuffled(original_iterable))
        # We insert a call to list() then shuffle in the loop body
        # Simpler: for X in _syntrop_shuffled(original_iterable)
        shuffled_iter = ast.Call(
            func=ast.Name(id="_syntrop_shuffled", ctx=ast.Load()),
            args=[node.iter],
            keywords=[],
        )
        node.iter = ast.copy_location(shuffled_iter, node.iter)
        return node

    def visit_ListComp(self, node: ast.ListComp) -> ast.ListComp:
        """Transform list comprehensions to shuffle generator order."""
        self.generic_visit(node)
        for gen in node.generators:
            shuffled_iter = ast.Call(
                func=ast.Name(id="_syntrop_shuffled", ctx=ast.Load()),
                args=[gen.iter],
                keywords=[],
            )
            gen.iter = ast.copy_location(shuffled_iter, gen.iter)
        return node

    def visit_DictComp(self, node: ast.DictComp) -> ast.DictComp:
        """Transform dict comprehensions to shuffle generator order."""
        self.generic_visit(node)
        for gen in node.generators:
            shuffled_iter = ast.Call(
                func=ast.Name(id="_syntrop_shuffled", ctx=ast.Load()),
                args=[gen.iter],
                keywords=[],
            )
            gen.iter = ast.copy_location(shuffled_iter, gen.iter)
        return node

    def visit_SetComp(self, node: ast.SetComp) -> ast.SetComp:
        """Transform set comprehensions to shuffle generator order."""
        self.generic_visit(node)
        for gen in node.generators:
            shuffled_iter = ast.Call(
                func=ast.Name(id="_syntrop_shuffled", ctx=ast.Load()),
                args=[gen.iter],
                keywords=[],
            )
            gen.iter = ast.copy_location(shuffled_iter, gen.iter)
        return node


class RandomizeIterationProbe(BaseProbe):
    """Probe that randomizes iteration order to reveal order-dependent bugs."""

    name = "randomize-iteration"
    description = "Randomize loop/iteration order to reveal order-dependent bugs"
    twist_type = "iteration"

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed

    def transform_source(self, source: str) -> str:
        """Transform source code to randomize iteration order."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        transformer = IterationRandomizer(seed=self.seed)
        tree = transformer.visit(tree)
        ast.fix_missing_locations(tree)

        # Generate the transformed code
        transformed = ast.unparse(tree)

        # Prepend the helper function
        helper = (
            "import random as _syntrop_rng\n"
            "def _syntrop_shuffled(iterable):\n"
            "    lst = list(iterable)\n"
            f"    _syntrop_rng.seed({self.seed!r})\n"
            "    _syntrop_rng.shuffle(lst)\n"
            "    return lst\n"
        )
        return helper + transformed

    def check_divergence(
        self, original_result: Any, probed_result: Any, metadata: dict[str, Any] | None = None
    ) -> ProbeResult:
        """Check if results diverge when iteration order is randomized."""
        if original_result == probed_result:
            return ProbeResult(
                probe_name=self.name,
                original_output=original_result,
                probed_output=probed_result,
                diverged=False,
                divergence_type="",
                explanation="Results match — no iteration-order dependency detected",
                severity="info",
            )

        # Check for order-only divergence (same elements, different order)
        order_only = False
        if isinstance(original_result, (list, tuple)) and isinstance(
            probed_result, (list, tuple)
        ):
            try:
                orig_sorted = sorted(original_result)
                probed_sorted = sorted(probed_result)
                if orig_sorted == probed_sorted:
                    order_only = True
            except TypeError:
                pass

        if order_only:
            return ProbeResult(
                probe_name=self.name,
                original_output=original_result,
                probed_output=probed_result,
                diverged=True,
                divergence_type="order-flip",
                explanation="Result elements are the same but in different order — "
                "the code has a hidden dependency on iteration order",
                severity="warning",
            )

        return ProbeResult(
            probe_name=self.name,
            original_output=original_result,
            probed_output=probed_result,
            diverged=True,
            divergence_type="value-change",
            explanation="Results differ when iteration order is randomized — "
            "the code depends on deterministic iteration order for correctness",
            severity="error",
        )
