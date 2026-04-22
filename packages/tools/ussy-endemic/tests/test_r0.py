"""Tests for endemic.r0 module."""

import pytest

from ussy_endemic.models import Pattern, PatternType, PatternStatus, TransmissionTree, TransmissionEvent, TransmissionVector
from ussy_endemic.r0 import (
    compute_r0_for_patterns,
    determine_status,
    estimate_r0_from_counts,
    estimate_r0_from_tree,
    estimate_r0_mle,
)


class TestEstimateR0FromTree:
    def test_empty_tree(self):
        tree = TransmissionTree(pattern_name="test")
        assert estimate_r0_from_tree(tree) == 0.0

    def test_simple_tree(self):
        tree = TransmissionTree(pattern_name="test", index_case="a.py")
        tree.add_event(TransmissionEvent(
            pattern_name="test", source_module="a.py", target_module="b.py"
        ))
        tree.add_event(TransmissionEvent(
            pattern_name="test", source_module="a.py", target_module="c.py"
        ))
        tree.add_event(TransmissionEvent(
            pattern_name="test", source_module="b.py", target_module="d.py"
        ))
        r0 = estimate_r0_from_tree(tree)
        assert r0 > 0

    def test_chain_tree(self):
        """Linear chain: each module infects one other."""
        tree = TransmissionTree(pattern_name="test", index_case="a.py")
        tree.add_event(TransmissionEvent(
            pattern_name="test", source_module="a.py", target_module="b.py"
        ))
        tree.add_event(TransmissionEvent(
            pattern_name="test", source_module="b.py", target_module="c.py"
        ))
        tree.add_event(TransmissionEvent(
            pattern_name="test", source_module="c.py", target_module="d.py"
        ))
        r0 = estimate_r0_from_tree(tree)
        assert r0 == 1.0  # Each source infects exactly 1


class TestEstimateR0FromCounts:
    def test_basic(self):
        r0 = estimate_r0_from_counts(new_infections=6, existing_infections=2)
        assert r0 == 3.0

    def test_zero_existing(self):
        r0 = estimate_r0_from_counts(new_infections=5, existing_infections=0)
        assert r0 == 0.0

    def test_dying(self):
        r0 = estimate_r0_from_counts(new_infections=1, existing_infections=5)
        assert r0 == 0.2


class TestEstimateR0MLE:
    def test_empty(self):
        assert estimate_r0_mle([]) == 0.0

    def test_simple(self):
        r0 = estimate_r0_mle([2, 3, 1, 4])
        assert r0 == 2.5

    def test_zeros(self):
        r0 = estimate_r0_mle([0, 0, 0])
        assert r0 == 0.0


class TestDetermineStatus:
    def test_spreading(self):
        assert determine_status(2.5, 0.2) == PatternStatus.SPREADING

    def test_dying(self):
        assert determine_status(0.5, 0.2) == PatternStatus.DYING

    def test_endemic_near_one(self):
        assert determine_status(1.0, 0.3) == PatternStatus.ENDEMIC

    def test_endemic_high_prevalence(self):
        assert determine_status(2.0, 0.9) == PatternStatus.ENDEMIC

    def test_eliminated(self):
        assert determine_status(0.01, 0.0) == PatternStatus.ELIMINATED


class TestComputeR0ForPatterns:
    def test_with_prevalence(self):
        patterns = [
            Pattern(name="test", prevalence_count=10, total_modules=50),
        ]
        result = compute_r0_for_patterns(patterns)
        assert len(result) == 1
        assert result[0].r0 > 0

    def test_with_tree(self):
        tree = TransmissionTree(pattern_name="test", index_case="a.py")
        tree.add_event(TransmissionEvent(
            pattern_name="test", source_module="a.py", target_module="b.py"
        ))
        tree.add_event(TransmissionEvent(
            pattern_name="test", source_module="a.py", target_module="c.py"
        ))

        patterns = [
            Pattern(name="test", prevalence_count=3, total_modules=10),
        ]
        result = compute_r0_for_patterns(patterns, trees={"test": tree})
        assert result[0].r0 > 0

    def test_with_infection_history(self):
        patterns = [
            Pattern(name="test", prevalence_count=5, total_modules=20),
        ]
        history = {"test": {"new_infections": 10, "existing_infections": 5}}
        result = compute_r0_for_patterns(patterns, infection_history=history)
        assert result[0].r0 == 2.0

    def test_zero_prevalence(self):
        patterns = [
            Pattern(name="test", prevalence_count=0, total_modules=50),
        ]
        result = compute_r0_for_patterns(patterns)
        assert result[0].r0 == 0.0
        assert result[0].status == PatternStatus.ELIMINATED
