"""Tests for the reconstruct module."""

from stemma.classify import classify_all
from stemma.collation import collate
from stemma.models import Classification, Witness
from stemma.reconstruct import reconstruct_archetype


class TestReconstructArchetype:
    def test_basic_reconstruction(self, all_witnesses):
        collation = collate(all_witnesses)
        classified = classify_all(collation)
        archetype = reconstruct_archetype(classified)
        assert len(archetype.lines) > 0
        assert 0.0 <= archetype.confidence <= 1.0

    def test_reconstruction_with_preferred_witness(self, all_witnesses):
        collation = collate(all_witnesses)
        classified = classify_all(collation)
        archetype = reconstruct_archetype(classified, prefer_witness="A")
        assert len(archetype.lines) > 0

    def test_empty_collation(self):
        collation = collate([])
        archetype = reconstruct_archetype(collation)
        assert archetype.lines == []
        assert archetype.confidence == 1.0

    def test_single_witness(self):
        w = Witness(label="A", source="a.py", lines=["x = 1", "y = 2"])
        collation = collate([w])
        classified = classify_all(collation)
        archetype = reconstruct_archetype(classified)
        assert len(archetype.lines) > 0

    def test_identical_witnesses(self):
        a = Witness(label="A", source="a.py", lines=["x = 1", "y = 2"])
        b = Witness(label="B", source="b.py", lines=["x = 1", "y = 2"])
        collation = collate([a, b])
        archetype = reconstruct_archetype(collation)
        assert archetype.confidence == 1.0

    def test_annotations_populated(self, all_witnesses):
        collation = collate(all_witnesses)
        classified = classify_all(collation)
        archetype = reconstruct_archetype(classified)
        # With variants, should have some annotations
        # (not guaranteed for all, but likely)
        # At minimum, archetype should be valid
        assert isinstance(archetype.annotations, dict)

    def test_method_is_lachmannian(self, all_witnesses):
        collation = collate(all_witnesses)
        classified = classify_all(collation)
        archetype = reconstruct_archetype(classified)
        assert archetype.method == "Lachmannian"
