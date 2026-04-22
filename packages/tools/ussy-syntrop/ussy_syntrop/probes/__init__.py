"""Semantic probes: lightweight transformations that apply esolang-inspired semantic twists.

Each probe modifies the execution semantics of Python code to reveal
implicit assumptions. These are the practical, CI-friendly mode of Syntrop.
"""

from ussy_syntrop.probes.randomize_iteration import RandomizeIterationProbe
from ussy_syntrop.probes.shuffle_eval_order import ShuffleEvalOrderProbe
from ussy_syntrop.probes.alias_state import AliasStateProbe
from ussy_syntrop.probes.nondeterministic_timing import NondeterministicTimingProbe

PROBE_REGISTRY: dict[str, type] = {
    "randomize-iteration": RandomizeIterationProbe,
    "shuffle-evaluation-order": ShuffleEvalOrderProbe,
    "alias-state": AliasStateProbe,
    "nondeterministic-timing": NondeterministicTimingProbe,
}

__all__ = [
    "PROBE_REGISTRY",
    "RandomizeIterationProbe",
    "ShuffleEvalOrderProbe",
    "AliasStateProbe",
    "NondeterministicTimingProbe",
]
