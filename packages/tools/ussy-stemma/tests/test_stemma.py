"""Tests for the stemma builder module."""

from stemma.collation import collate
from stemma.models import Witness, WitnessRole
from stemma.stemma_builder import (
    build_stemma,
    build_variant_matrix,
    compute_distance_matrix,
    shared_errors,
)


class TestBuildVariantMatrix:
    def test_basic_matrix(self, all_witnesses):
        collation = collate(all_witnesses)
        matrix = build_variant_matrix(collation)
        # Matrix should have entries for each witness
        for w in all_witnesses:
            assert w.label in matrix

    def test_no_variants(self):
        a = Witness(label="A", source="a.py", lines=["x = 1"])
        b = Witness(label="B", source="b.py", lines=["x = 1"])
        collation = collate([a, b])
        matrix = build_variant_matrix(collation)
        # No variant positions -> empty lists
        for label in matrix:
            assert matrix[label] == []


class TestSharedErrors:
    def test_shared_errors_found(self, all_witnesses):
        collation = collate(all_witnesses)
        errors = shared_errors(collation)
        # D and E share >= 0 (scribal error from common source)
        assert len(errors) > 0

    def test_no_shared_errors_identical(self):
        a = Witness(label="A", source="a.py", lines=["x = 1"])
        b = Witness(label="B", source="b.py", lines=["x = 1"])
        collation = collate([a, b])
        errors = shared_errors(collation)
        assert len(errors) == 0


class TestComputeDistanceMatrix:
    def test_basic_distances(self, all_witnesses):
        distances = compute_distance_matrix(all_witnesses)
        # Should have distances for all pairs
        labels = [w.label for w in all_witnesses]
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                assert (labels[i], labels[j]) in distances

    def test_identical_witnesses_zero_distance(self):
        a = Witness(label="A", source="a.py", lines=["x = 1", "y = 2"])
        b = Witness(label="B", source="b.py", lines=["x = 1", "y = 2"])
        distances = compute_distance_matrix([a, b])
        assert distances[("A", "B")] == 0.0


class TestBuildStemma:
    def test_basic_stemma(self, all_witnesses):
        collation = collate(all_witnesses)
        tree = build_stemma(collation)
        assert tree.root is not None
        assert len(tree.nodes) > 0

    def test_stemma_has_archetype(self, all_witnesses):
        collation = collate(all_witnesses)
        tree = build_stemma(collation)
        archetype = tree.archetype
        assert archetype is not None
        assert archetype.role == WitnessRole.ARCHETYPE

    def test_stemma_has_terminal_nodes(self, all_witnesses):
        collation = collate(all_witnesses)
        tree = build_stemma(collation)
        terminals = tree.terminal_nodes
        assert len(terminals) > 0

    def test_single_witness_stemma(self):
        w = Witness(label="A", source="a.py", lines=["x = 1"])
        collation = collate([w])
        tree = build_stemma(collation)
        assert tree.root is not None
        assert tree.root.label == "A"

    def test_empty_stemma(self):
        collation = collate([])
        tree = build_stemma(collation)
        assert tree.root is None

    def test_two_witness_stemma(self):
        a = Witness(label="A", source="a.py", lines=["x = 1", "y = 2"])
        b = Witness(label="B", source="b.py", lines=["x = 1", "y = 3"])
        collation = collate([a, b])
        tree = build_stemma(collation)
        assert tree.root is not None
        assert len(tree.nodes) >= 2
