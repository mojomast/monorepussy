"""Nondeterministic-timing probe: introduces random delays to reveal timing bugs.

Inspired by INTERCAL's COME FROM random control flow, this probe reveals
hidden assumptions about the atomicity or ordering of operations,
simulating race conditions in single-threaded code.
"""

from __future__ import annotations

import ast
import random
from typing import Any

from ussy_syntrop.ir import ProbeResult
from ussy_syntrop.probes.base import BaseProbe


class TimingInjector(ast.NodeTransformer):
    """AST transformer that injects random timing delays."""

    def __init__(self, seed: int | None = None, max_delay: float = 0.001) -> None:
        self.seed = seed
        self.max_delay = max_delay

    def visit_Assign(self, node: ast.Assign) -> list[ast.stmt]:
        """Insert random delays after assignments."""
        self.generic_visit(node)

        # Add a delay call after each assignment
        delay_call = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="_syntrop_delay", ctx=ast.Load()),
                args=[],
                keywords=[],
            )
        )
        ast.copy_location(delay_call, node)
        return [node, delay_call]

    def visit_AugAssign(self, node: ast.AugAssign) -> list[ast.stmt]:
        """Insert random delays after augmented assignments."""
        self.generic_visit(node)

        delay_call = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="_syntrop_delay", ctx=ast.Load()),
                args=[],
                keywords=[],
            )
        )
        ast.copy_location(delay_call, node)
        return [node, delay_call]


class NondeterministicTimingProbe(BaseProbe):
    """Probe that introduces random timing delays to reveal timing-dependent bugs."""

    name = "nondeterministic-timing"
    description = "Introduce random delays to reveal timing/atomicity bugs"
    twist_type = "timing"

    def __init__(self, seed: int | None = None, max_delay: float = 0.001) -> None:
        self.seed = seed
        self.max_delay = max_delay

    def transform_source(self, source: str) -> str:
        """Transform source code to inject random timing delays."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        injector = TimingInjector(seed=self.seed, max_delay=self.max_delay)
        tree = injector.visit(tree)
        ast.fix_missing_locations(tree)

        transformed = ast.unparse(tree)

        # Prepend helper
        helper = (
            "import random as _syntrop_rng\n"
            "import time as _syntrop_time\n"
            f"_syntrop_rng.seed({self.seed!r})\n"
            f"def _syntrop_delay():\n"
            f"    _syntrop_time.sleep(_syntrop_rng.random() * {self.max_delay})\n"
        )
        return helper + transformed

    def check_divergence(
        self, original_result: Any, probed_result: Any, metadata: dict[str, Any] | None = None
    ) -> ProbeResult:
        """Check if results diverge when timing delays are introduced."""
        if original_result == probed_result:
            return ProbeResult(
                probe_name=self.name,
                original_output=original_result,
                probed_output=probed_result,
                diverged=False,
                divergence_type="",
                explanation="Results match — no timing-dependent behavior detected",
                severity="info",
            )

        return ProbeResult(
            probe_name=self.name,
            original_output=original_result,
            probed_output=probed_result,
            diverged=True,
            divergence_type="timing",
            explanation="Results differ when random delays are introduced — "
            "the code depends on specific timing or atomicity of operations",
            severity="warning",
        )
