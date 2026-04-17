"""Shuffle-evaluation-order probe: randomizes function argument evaluation order.

Inspired by INTERCAL's COME FROM semantics, this probe reveals hidden
assumptions about the order in which function arguments are evaluated.
In Python, arguments are evaluated left-to-right, but other languages
(and this probe) may evaluate them in any order.
"""

from __future__ import annotations

import ast
import random
from typing import Any

from syntrop.ir import ProbeResult
from syntrop.probes.base import BaseProbe


class EvalOrderShuffler(ast.NodeTransformer):
    """AST transformer that wraps function arguments to shuffle evaluation order."""

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed

    def visit_Call(self, node: ast.Call) -> ast.Call:
        """Transform function calls to shuffle argument evaluation order."""
        self.generic_visit(node)

        if len(node.args) <= 1:
            return node

        # Wrap each argument in a thunk-capture call that records evaluation order
        # We replace: f(a, b, c) with f(*_syntrop_shuffled_args([lambda: a, lambda: b, lambda: c]))
        thunks = []
        for arg in node.args:
            thunk = ast.Lambda(
                args=ast.arguments(
                    posonlyargs=[],
                    args=[],
                    vararg=None,
                    kwonlyargs=[],
                    kw_defaults=[],
                    kwarg=None,
                    defaults=[],
                ),
                body=arg,
            )
            thunks.append(thunk)

        list_of_thunks = ast.List(elts=thunks, ctx=ast.Load())

        call = ast.Call(
            func=ast.Name(id="_syntrop_shuffled_args", ctx=ast.Load()),
            args=[list_of_thunks],
            keywords=[],
        )
        starred = ast.Starred(value=call, ctx=ast.Load())

        node.args = [starred]
        return node


class ShuffleEvalOrderProbe(BaseProbe):
    """Probe that shuffles function argument evaluation order."""

    name = "shuffle-evaluation-order"
    description = "Randomize function argument evaluation order to reveal eval-order bugs"
    twist_type = "evaluation"

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed

    def transform_source(self, source: str) -> str:
        """Transform source code to shuffle evaluation order."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        transformer = EvalOrderShuffler(seed=self.seed)
        tree = transformer.visit(tree)
        ast.fix_missing_locations(tree)

        transformed = ast.unparse(tree)

        # Prepend the helper function
        helper = (
            "import random as _syntrop_rng\n"
            "def _syntrop_shuffled_args(thunks):\n"
            "    order = list(range(len(thunks)))\n"
            f"    _syntrop_rng.seed({self.seed!r})\n"
            "    _syntrop_rng.shuffle(order)\n"
            "    results = [None] * len(thunks)\n"
            "    for i, idx in enumerate(order):\n"
            "        results[order.index(idx)] = thunks[idx]()\n"
            "    return results\n"
        )
        return helper + transformed

    def check_divergence(
        self, original_result: Any, probed_result: Any, metadata: dict[str, Any] | None = None
    ) -> ProbeResult:
        """Check if results diverge when evaluation order is shuffled."""
        if original_result == probed_result:
            return ProbeResult(
                probe_name=self.name,
                original_output=original_result,
                probed_output=probed_result,
                diverged=False,
                divergence_type="",
                explanation="Results match — no evaluation-order dependency detected",
                severity="info",
            )

        return ProbeResult(
            probe_name=self.name,
            original_output=original_result,
            probed_output=probed_result,
            diverged=True,
            divergence_type="eval-order-change",
            explanation="Results differ when argument evaluation order is shuffled — "
            "the code depends on left-to-right argument evaluation",
            severity="error",
        )
