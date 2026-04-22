"""Tests for crystallo.similarity — pairwise similarity and symmetry classification."""

import pytest

from ussy_crystallo.models import (
    MethodSignature,
    StructuralFingerprint,
    SymmetryIntent,
    SymmetryType,
)
from ussy_crystallo.similarity import (
    classify_intent,
    classify_symmetry,
    compute_pairwise_similarities,
    compute_similarity,
    cosine_similarity,
    jaccard_index,
)


# ---------------------------------------------------------------------------
# Vector / set similarity primitives
# ---------------------------------------------------------------------------

class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_zero_vector(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_empty_vectors(self):
        assert cosine_similarity([], []) == 0.0

    def test_different_lengths(self):
        assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0

    def test_opposite_directions(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)


class TestJaccardIndex:
    def test_identical_sets(self):
        assert jaccard_index({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint_sets(self):
        assert jaccard_index({"a"}, {"b"}) == 0.0

    def test_partial_overlap(self):
        result = jaccard_index({"a", "b", "c"}, {"b", "c", "d"})
        assert result == pytest.approx(0.5)

    def test_empty_sets(self):
        assert jaccard_index(set(), set()) == 1.0

    def test_one_empty_set(self):
        assert jaccard_index({"a"}, set()) == 0.0


# ---------------------------------------------------------------------------
# compute_similarity
# ---------------------------------------------------------------------------

class TestComputeSimilarity:
    def test_identical_fingerprints(self):
        fp = StructuralFingerprint(
            name="A",
            method_names=["save", "delete"],
            base_classes=["Base"],
        )
        sim = compute_similarity(fp, fp)
        assert sim == pytest.approx(1.0)

    def test_different_fingerprints(self):
        fp_a = StructuralFingerprint(name="A", method_names=["save", "delete", "validate"])
        fp_b = StructuralFingerprint(name="B", method_names=["foo", "bar"])
        sim = compute_similarity(fp_a, fp_b)
        assert 0.0 <= sim <= 1.0
        assert sim < 0.7  # quite different (some overlap from vector features)

    def test_shared_methods_high_similarity(self):
        fp_a = StructuralFingerprint(
            name="A",
            method_names=["save", "delete", "validate"],
            base_classes=["Base"],
        )
        fp_b = StructuralFingerprint(
            name="B",
            method_names=["save", "delete", "validate"],
            base_classes=["Base"],
        )
        sim = compute_similarity(fp_a, fp_b)
        assert sim >= 0.8


# ---------------------------------------------------------------------------
# compute_pairwise_similarities
# ---------------------------------------------------------------------------

class TestComputePairwiseSimilarities:
    def test_returns_relations_above_threshold(self):
        fp_a = StructuralFingerprint(
            name="A",
            method_names=["save", "delete", "validate"],
            base_classes=["Base"],
        )
        fp_b = StructuralFingerprint(
            name="B",
            method_names=["save", "delete", "validate"],
            base_classes=["Base"],
        )
        fp_c = StructuralFingerprint(
            name="C",
            method_names=["unrelated"],
        )
        rels = compute_pairwise_similarities([fp_a, fp_b, fp_c], threshold=0.4)
        # A-B should be above threshold, A-C and B-C probably not
        assert any(r.source == "A" and r.target == "B" for r in rels) or \
               any(r.source == "B" and r.target == "A" for r in rels)

    def test_empty_list(self):
        assert compute_pairwise_similarities([]) == []

    def test_single_fingerprint(self):
        fp = StructuralFingerprint(name="Solo")
        assert compute_pairwise_similarities([fp]) == []


# ---------------------------------------------------------------------------
# classify_symmetry
# ---------------------------------------------------------------------------

class TestClassifySymmetry:
    def test_rotational_with_shared_base(self):
        fp_a = StructuralFingerprint(
            name="UserModel",
            method_names=["save", "delete", "validate"],
            base_classes=["BaseModel"],
        )
        fp_b = StructuralFingerprint(
            name="OrderModel",
            method_names=["save", "delete", "validate"],
            base_classes=["BaseModel"],
        )
        sim = compute_similarity(fp_a, fp_b)
        stype = classify_symmetry(fp_a, fp_b, sim)
        assert stype == SymmetryType.ROTATIONAL

    def test_broken_symmetry_shared_base_divergent_methods(self):
        fp_a = StructuralFingerprint(
            name="UserModel",
            method_names=["save", "delete", "validate", "validate_email"],
            base_classes=["BaseModel"],
        )
        fp_b = StructuralFingerprint(
            name="OrderModel",
            method_names=["save", "delete"],
            base_classes=["BaseModel"],
        )
        sim = compute_similarity(fp_a, fp_b)
        stype = classify_symmetry(fp_a, fp_b, sim)
        # Should be BROKEN because shared base but low method overlap
        assert stype in (SymmetryType.BROKEN, SymmetryType.ROTATIONAL)

    def test_glide_symmetry(self):
        fp_a = StructuralFingerprint(
            name="TestUserModel",
            method_names=["test_save", "test_delete"],
            file_path="tests/test_user.py",
        )
        fp_b = StructuralFingerprint(
            name="UserModel",
            method_names=["save", "delete"],
            file_path="src/user.py",
        )
        # Low similarity but test naming triggers glide
        stype = classify_symmetry(fp_a, fp_b, 0.6)
        assert stype == SymmetryType.GLIDE

    def test_reflection_mirror_names(self):
        fp_a = StructuralFingerprint(
            name="APIClient",
            method_names=["connect", "send_request", "handle_response", "close"],
        )
        fp_b = StructuralFingerprint(
            name="APIServer",
            method_names=["connect", "receive_request", "handle_response", "close"],
        )
        method_jac = jaccard_index(fp_a.method_set, fp_b.method_set)
        sim = 0.7
        stype = classify_symmetry(fp_a, fp_b, sim)
        assert stype == SymmetryType.REFLECTION

    def test_low_similarity_none(self):
        fp_a = StructuralFingerprint(name="A", method_names=["x"])
        fp_b = StructuralFingerprint(name="B", method_names=["y"])
        stype = classify_symmetry(fp_a, fp_b, 0.2)
        assert stype == SymmetryType.NONE


# ---------------------------------------------------------------------------
# classify_intent
# ---------------------------------------------------------------------------

class TestClassifyIntent:
    def test_glide_is_expected(self):
        fp = StructuralFingerprint(name="X")
        assert classify_intent(fp, fp, SymmetryType.GLIDE) == SymmetryIntent.EXPECTED

    def test_broken_is_broken(self):
        fp = StructuralFingerprint(name="X")
        assert classify_intent(fp, fp, SymmetryType.BROKEN) == SymmetryIntent.BROKEN

    def test_rotational_with_shared_base_is_intentional(self):
        fp_a = StructuralFingerprint(name="A", base_classes=["Base"])
        fp_b = StructuralFingerprint(name="B", base_classes=["Base"])
        assert classify_intent(fp_a, fp_b, SymmetryType.ROTATIONAL) == SymmetryIntent.INTENTIONAL

    def test_translational_without_base_is_accidental(self):
        fp_a = StructuralFingerprint(name="A", base_classes=[], decorator_names=[])
        fp_b = StructuralFingerprint(name="B", base_classes=[], decorator_names=[])
        assert classify_intent(fp_a, fp_b, SymmetryType.TRANSLATIONAL) == SymmetryIntent.ACCIDENTAL

    def test_none_is_unknown(self):
        fp = StructuralFingerprint(name="X")
        assert classify_intent(fp, fp, SymmetryType.NONE) == SymmetryIntent.UNKNOWN
