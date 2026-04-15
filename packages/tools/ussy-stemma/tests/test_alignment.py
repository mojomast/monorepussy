"""Tests for the alignment module."""

from stemma.alignment import (
    line_similarity,
    needleman_wunsch,
    pairwise_distance,
    align_witnesses,
)
from stemma.models import Witness


class TestLineSimilarity:
    def test_identical_lines(self):
        assert line_similarity("x = 1", "x = 1") == 1.0

    def test_completely_different(self):
        assert line_similarity("foo bar", "baz qux") == 0.0

    def test_partial_overlap(self):
        sim = line_similarity("charge = calc(order)", "charge = compute(order)")
        assert 0.0 < sim < 1.0

    def test_empty_strings(self):
        assert line_similarity("", "") == 1.0
        assert line_similarity("x", "") == 0.0
        assert line_similarity("", "x") == 0.0


class TestNeedlemanWunsch:
    def test_identical_sequences(self):
        seq = ["x = 1", "y = 2", "z = 3"]
        alignment, score = needleman_wunsch(seq, seq)
        # Should align perfectly
        for ai, bi in alignment:
            assert ai == bi

    def test_different_sequences(self):
        a = ["x = 1", "y = 2", "z = 3"]
        b = ["x = 1", "w = 4", "z = 3"]
        alignment, score = needleman_wunsch(a, b)
        assert len(alignment) >= max(len(a), len(b))

    def test_one_empty(self):
        a = ["x = 1", "y = 2"]
        b: list[str] = []
        alignment, score = needleman_wunsch(a, b)
        assert len(alignment) == 2
        for ai, bi in alignment:
            assert bi is None  # gaps

    def test_both_empty(self):
        alignment, score = needleman_wunsch([], [])
        assert alignment == []
        assert score == 0

    def test_insertion(self):
        a = ["x = 1", "z = 3"]
        b = ["x = 1", "y = 2", "z = 3"]
        alignment, score = needleman_wunsch(a, b)
        assert len(alignment) >= 3


class TestPairwiseDistance:
    def test_identical_witnesses(self):
        w = Witness(label="A", source="a.py", lines=["x = 1", "y = 2"])
        assert pairwise_distance(w, w) == 0.0

    def test_different_witnesses(self):
        a = Witness(label="A", source="a.py", lines=["x = 1", "y = 2"])
        b = Witness(label="B", source="b.py", lines=["a = 9", "b = 8", "c = 7"])
        dist = pairwise_distance(a, b)
        assert dist > 0.0

    def test_similar_witnesses(self):
        a = Witness(label="A", source="a.py", lines=["x = 1", "y = 2", "z = 3"])
        b = Witness(label="B", source="b.py", lines=["x = 1", "y = 5", "z = 3"])
        dist = pairwise_distance(a, b)
        assert 0.0 < dist < 1.0


class TestAlignWitnesses:
    def test_single_witness(self):
        w = Witness(label="A", source="a.py", lines=["x = 1", "y = 2"])
        aligned = align_witnesses([w])
        assert len(aligned) == 2
        assert aligned[0]["A"] == "x = 1"
        assert aligned[1]["A"] == "y = 2"

    def test_two_witnesses(self):
        a = Witness(label="A", source="a.py", lines=["x = 1", "y = 2"])
        b = Witness(label="B", source="b.py", lines=["x = 1", "y = 2"])
        aligned = align_witnesses([a, b])
        assert len(aligned) >= 2

    def test_empty_witnesses(self):
        aligned = align_witnesses([])
        assert aligned == {}

    def test_different_length_witnesses(self):
        a = Witness(label="A", source="a.py", lines=["x = 1", "y = 2", "z = 3"])
        b = Witness(label="B", source="b.py", lines=["x = 1", "z = 3"])
        aligned = align_witnesses([a, b])
        assert len(aligned) >= 2
