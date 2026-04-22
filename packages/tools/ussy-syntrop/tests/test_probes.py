"""Tests for the semantic probes."""

import pytest

from ussy_syntrop.probes import PROBE_REGISTRY
from ussy_syntrop.probes.base import BaseProbe
from ussy_syntrop.probes.randomize_iteration import RandomizeIterationProbe
from ussy_syntrop.probes.shuffle_eval_order import ShuffleEvalOrderProbe
from ussy_syntrop.probes.alias_state import AliasStateProbe
from ussy_syntrop.probes.nondeterministic_timing import NondeterministicTimingProbe
from ussy_syntrop.ir import ProbeResult


# --- Test source code fixtures ---

SOURCE_ORDER_DEPENDENT = """
def process(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result

def main():
    return process([1, 2, 3])
"""

SOURCE_EVAL_ORDER = """
counter = [0]

def inc(x):
    counter[0] += 1
    return x

def main():
    counter[0] = 0
    result = inc(1) + inc(2) + inc(3)
    return counter[0]
"""

SOURCE_ALIAS_STATE = """
def main():
    original = [1, 2, 3]
    copy = original.copy()
    copy.append(4)
    return len(original)
"""

SOURCE_PURE = """
def main():
    return 2 + 3
"""

SOURCE_SIMPLE_ITER = """
def main():
    total = 0
    for i in [1, 2, 3, 4, 5]:
        total += i
    return total
"""

SOURCE_DICT_ITER = """
def main():
    d = {"a": 1, "b": 2, "c": 3}
    result = []
    for key in d:
        result.append(key)
    return result
"""


# --- BaseProbe tests ---

class TestBaseProbe:
    """Tests for BaseProbe ABC."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseProbe()

    def test_execute_source_valid(self):
        source = "def main(): return 42"
        result, error = BaseProbe._execute_source(source, "main", (), {})
        assert result == 42
        assert error is None

    def test_execute_source_missing_function(self):
        source = "x = 1"
        result, error = BaseProbe._execute_source(source, "main", (), {})
        assert result is None
        assert isinstance(error, NameError)

    def test_execute_source_with_error(self):
        source = "def main(): raise ValueError('boom')"
        result, error = BaseProbe._execute_source(source, "main", (), {})
        assert result is None
        assert isinstance(error, ValueError)

    def test_execute_source_with_args(self):
        source = "def main(x, y): return x + y"
        result, error = BaseProbe._execute_source(source, "main", (3, 4), {})
        assert result == 7
        assert error is None


# --- RandomizeIterationProbe tests ---

class TestRandomizeIterationProbe:
    """Tests for the randomize-iteration probe."""

    def test_probe_in_registry(self):
        assert "randomize-iteration" in PROBE_REGISTRY

    def test_probe_name(self):
        probe = RandomizeIterationProbe()
        assert probe.name == "randomize-iteration"

    def test_transform_source_adds_helper(self):
        probe = RandomizeIterationProbe(seed=42)
        transformed = probe.transform_source(SOURCE_SIMPLE_ITER)
        assert "_syntrop_shuffled" in transformed
        assert "_syntrop_rng" in transformed

    def test_transform_preserves_semantics_for_sum(self):
        """Sum is order-independent, so probe should not diverge."""
        probe = RandomizeIterationProbe(seed=42)
        result = probe.run(SOURCE_SIMPLE_ITER, "main")
        # Sum is commutative, so randomized iteration gives same result
        assert result.original_output == 15
        assert result.probed_output == 15
        assert not result.diverged

    def test_check_divergence_order_flip(self):
        probe = RandomizeIterationProbe()
        result = probe.check_divergence([1, 2, 3], [3, 2, 1])
        assert result.diverged
        assert result.divergence_type == "order-flip"

    def test_check_divergence_value_change(self):
        probe = RandomizeIterationProbe()
        result = probe.check_divergence([1, 2, 3], [4, 5, 6])
        assert result.diverged
        assert result.divergence_type == "value-change"

    def test_check_no_divergence(self):
        probe = RandomizeIterationProbe()
        result = probe.check_divergence(42, 42)
        assert not result.diverged

    def test_seed_reproducibility(self):
        """Same seed should produce same results."""
        probe1 = RandomizeIterationProbe(seed=42)
        probe2 = RandomizeIterationProbe(seed=42)
        result1 = probe1.run(SOURCE_DICT_ITER, "main")
        result2 = probe2.run(SOURCE_DICT_ITER, "main")
        assert result1.probed_output == result2.probed_output

    def test_transform_syntax_error(self):
        """Transform should return source as-is on syntax error."""
        probe = RandomizeIterationProbe()
        result = probe.transform_source("def broken(:")
        assert result == "def broken(:"

    def test_check_divergence_unsortable(self):
        """Check divergence with unsortable types."""
        probe = RandomizeIterationProbe()
        result = probe.check_divergence(
            {"a": 1}, {"b": 2}
        )
        assert result.diverged
        assert result.divergence_type == "value-change"


# --- ShuffleEvalOrderProbe tests ---

class TestShuffleEvalOrderProbe:
    """Tests for the shuffle-evaluation-order probe."""

    def test_probe_in_registry(self):
        assert "shuffle-evaluation-order" in PROBE_REGISTRY

    def test_probe_name(self):
        probe = ShuffleEvalOrderProbe()
        assert probe.name == "shuffle-evaluation-order"

    def test_transform_source_adds_helper(self):
        probe = ShuffleEvalOrderProbe(seed=42)
        transformed = probe.transform_source("def f(a, b): return a + b")
        assert "_syntrop_shuffled_args" in transformed

    def test_pure_function_no_divergence(self):
        """Pure functions with no side effects shouldn't diverge."""
        probe = ShuffleEvalOrderProbe(seed=42)
        result = probe.run(SOURCE_PURE, "main")
        assert not result.diverged

    def test_check_divergence_detected(self):
        probe = ShuffleEvalOrderProbe()
        result = probe.check_divergence(3, 5)
        assert result.diverged
        assert result.divergence_type == "eval-order-change"

    def test_check_no_divergence(self):
        probe = ShuffleEvalOrderProbe()
        result = probe.check_divergence(42, 42)
        assert not result.diverged

    def test_transform_syntax_error(self):
        probe = ShuffleEvalOrderProbe()
        result = probe.transform_source("def broken(:")
        assert result == "def broken(:"


# --- AliasStateProbe tests ---

class TestAliasStateProbe:
    """Tests for the alias-state probe."""

    def test_probe_in_registry(self):
        assert "alias-state" in PROBE_REGISTRY

    def test_probe_name(self):
        probe = AliasStateProbe()
        assert probe.name == "alias-state"

    def test_transform_removes_copy(self):
        source = "x = items.copy()"
        probe = AliasStateProbe()
        transformed = probe.transform_source(source)
        assert "alias-state removed .copy()" in transformed

    def test_transform_removes_list_copy(self):
        source = "x = list(items)"
        probe = AliasStateProbe()
        transformed = probe.transform_source(source)
        assert "alias-state removed list() copy" in transformed

    def test_transform_removes_dict_copy(self):
        source = "x = dict(data)"
        probe = AliasStateProbe()
        transformed = probe.transform_source(source)
        assert "alias-state removed dict() copy" in transformed

    def test_transform_adds_mutation_tracker(self):
        probe = AliasStateProbe()
        transformed = probe.transform_source("x = 1")
        assert "_SyntropMutationTracker" in transformed

    def test_check_divergence(self):
        probe = AliasStateProbe()
        result = probe.check_divergence([1, 2, 3], [1, 2, 3, 4])
        assert result.diverged
        assert result.divergence_type == "state-alias"

    def test_check_no_divergence(self):
        probe = AliasStateProbe()
        result = probe.check_divergence(42, 42)
        assert not result.diverged

    def test_run_with_copy_produces_divergence(self):
        """Code using .copy() should diverge when copy is removed."""
        probe = AliasStateProbe()
        result = probe.run(SOURCE_ALIAS_STATE, "main")
        # Original: len(original) == 3 (copy doesn't affect original)
        # Probed: .copy() removed, so modifying "copy" modifies "original"
        # The probed code's len(original) should be 4 instead of 3
        assert result.original_output == 3
        assert result.probed_output == 4
        assert result.diverged


# --- NondeterministicTimingProbe tests ---

class TestNondeterministicTimingProbe:
    """Tests for the nondeterministic-timing probe."""

    def test_probe_in_registry(self):
        assert "nondeterministic-timing" in PROBE_REGISTRY

    def test_probe_name(self):
        probe = NondeterministicTimingProbe()
        assert probe.name == "nondeterministic-timing"

    def test_transform_adds_delay_helper(self):
        probe = NondeterministicTimingProbe(seed=42)
        transformed = probe.transform_source("x = 1\ny = 2")
        assert "_syntrop_delay" in transformed

    def test_pure_function_no_divergence(self):
        """Pure functions shouldn't be affected by timing."""
        probe = NondeterministicTimingProbe(seed=42, max_delay=0.0001)
        result = probe.run(SOURCE_PURE, "main")
        assert not result.diverged

    def test_check_divergence(self):
        probe = NondeterministicTimingProbe()
        result = probe.check_divergence(42, 43)
        assert result.diverged
        assert result.divergence_type == "timing"

    def test_check_no_divergence(self):
        probe = NondeterministicTimingProbe()
        result = probe.check_divergence(42, 42)
        assert not result.diverged

    def test_transform_syntax_error(self):
        probe = NondeterministicTimingProbe()
        result = probe.transform_source("def broken(:")
        assert result == "def broken(:"

    def test_max_delay_configurable(self):
        probe = NondeterministicTimingProbe(max_delay=0.5)
        assert probe.max_delay == 0.5


# --- Registry tests ---

class TestProbeRegistry:
    """Tests for the probe registry."""

    def test_all_probes_registered(self):
        expected = [
            "randomize-iteration",
            "shuffle-evaluation-order",
            "alias-state",
            "nondeterministic-timing",
        ]
        for name in expected:
            assert name in PROBE_REGISTRY

    def test_registry_classes_are_base_probe_subclasses(self):
        for name, cls in PROBE_REGISTRY.items():
            assert issubclass(cls, BaseProbe)

    def test_registry_classes_can_be_instantiated(self):
        for name, cls in PROBE_REGISTRY.items():
            probe = cls()
            assert isinstance(probe, BaseProbe)
