"""Similarity detection — pairwise structural comparison of code units."""

from __future__ import annotations

import math
from itertools import combinations

from ussy_crystallo.models import (
    StructuralFingerprint,
    SymmetryIntent,
    SymmetryRelation,
    SymmetryType,
)


# ---------------------------------------------------------------------------
# Vector similarity
# ---------------------------------------------------------------------------

def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two equal-length feature vectors."""
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


def jaccard_index(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard similarity coefficient for two sets of strings."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Pairwise similarity
# ---------------------------------------------------------------------------

def compute_similarity(
    fp_a: StructuralFingerprint, fp_b: StructuralFingerprint
) -> float:
    """Overall similarity score combining vector and set similarity."""
    vec_sim = cosine_similarity(fp_a.feature_vector, fp_b.feature_vector)
    method_jac = jaccard_index(fp_a.method_set, fp_b.method_set)
    attr_jac = jaccard_index(fp_a.attribute_set, fp_b.attribute_set)
    base_jac = jaccard_index(set(fp_a.base_classes), set(fp_b.base_classes))

    # Weighted combination — method overlap is the strongest signal
    total = 0.30 * vec_sim + 0.35 * method_jac + 0.15 * attr_jac + 0.20 * base_jac
    return total


def compute_pairwise_similarities(
    fingerprints: list[StructuralFingerprint],
    threshold: float = 0.4,
) -> list[SymmetryRelation]:
    """Compute pairwise similarity for all fingerprints above threshold."""
    relations: list[SymmetryRelation] = []
    for fp_a, fp_b in combinations(fingerprints, 2):
        sim = compute_similarity(fp_a, fp_b)
        if sim >= threshold:
            rel = _build_relation(fp_a, fp_b, sim)
            relations.append(rel)
    return relations


# ---------------------------------------------------------------------------
# Symmetry classification
# ---------------------------------------------------------------------------

def classify_symmetry(
    fp_a: StructuralFingerprint, fp_b: StructuralFingerprint, similarity: float
) -> SymmetryType:
    """Classify the symmetry type between two fingerprints."""
    if similarity < 0.4:
        return SymmetryType.NONE

    method_sim = jaccard_index(fp_a.method_set, fp_b.method_set)
    base_sim = jaccard_index(set(fp_a.base_classes), set(fp_b.base_classes))
    attr_sim = jaccard_index(fp_a.attribute_set, fp_b.attribute_set)

    # Check for glide symmetry (test mirrors source)
    a_name_lower = fp_a.name.lower()
    b_name_lower = fp_b.name.lower()
    is_glide = (
        a_name_lower.startswith("test") and not b_name_lower.startswith("test")
    ) or (
        b_name_lower.startswith("test") and not a_name_lower.startswith("test")
    )
    # Also check file paths for test/ pattern
    a_in_test = "test" in fp_a.file_path.lower()
    b_in_test = "test" in fp_b.file_path.lower()
    if (a_in_test and not b_in_test) or (b_in_test and not a_in_test):
        is_glide = True

    if is_glide and similarity >= 0.5:
        return SymmetryType.GLIDE

    # Reflection: high method overlap + high attribute overlap + mirror naming
    mirror_names = _are_mirror_names(fp_a.name, fp_b.name)
    if mirror_names and method_sim >= 0.6:
        return SymmetryType.REFLECTION

    # Broken symmetry: shared base but divergent methods
    if base_sim >= 0.5 and method_sim < 0.5 and similarity >= 0.4:
        return SymmetryType.BROKEN

    # Rotational: same structure, different roles — shared base, high method overlap
    if base_sim >= 0.5 and method_sim >= 0.5:
        return SymmetryType.ROTATIONAL

    # High method overlap without shared base → translational or rotational
    if method_sim >= 0.6:
        if attr_sim >= 0.5:
            return SymmetryType.ROTATIONAL
        return SymmetryType.TRANSLATIONAL

    # Translational: moderate similarity, repeated pattern
    if similarity >= 0.5:
        return SymmetryType.TRANSLATIONAL

    return SymmetryType.NONE


def classify_intent(
    fp_a: StructuralFingerprint,
    fp_b: StructuralFingerprint,
    symmetry_type: SymmetryType,
) -> SymmetryIntent:
    """Determine whether the symmetry is intentional, accidental, etc."""
    match symmetry_type:
        case SymmetryType.GLIDE:
            return SymmetryIntent.EXPECTED
        case SymmetryType.BROKEN:
            return SymmetryIntent.BROKEN
        case SymmetryType.ROTATIONAL | SymmetryType.REFLECTION:
            # Intentional if they share a base class
            shared_bases = set(fp_a.base_classes) & set(fp_b.base_classes)
            if shared_bases:
                return SymmetryIntent.INTENTIONAL
            # Check for shared decorator (like @dataclass)
            shared_decs = set(fp_a.decorator_names) & set(fp_b.decorator_names)
            if shared_decs:
                return SymmetryIntent.INTENTIONAL
            return SymmetryIntent.ACCIDENTAL
        case SymmetryType.TRANSLATIONAL:
            shared_bases = set(fp_a.base_classes) & set(fp_b.base_classes)
            shared_decs = set(fp_a.decorator_names) & set(fp_b.decorator_names)
            if shared_bases or shared_decs:
                return SymmetryIntent.INTENTIONAL
            return SymmetryIntent.ACCIDENTAL
        case _:
            return SymmetryIntent.UNKNOWN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_relation(
    fp_a: StructuralFingerprint, fp_b: StructuralFingerprint, similarity: float
) -> SymmetryRelation:
    """Build a SymmetryRelation from two fingerprints and their similarity score."""
    sym_type = classify_symmetry(fp_a, fp_b, similarity)
    intent = classify_intent(fp_a, fp_b, sym_type)

    # Compute method set differences
    methods_a = fp_a.method_set
    methods_b = fp_b.method_set

    missing_in_target = sorted(methods_a - methods_b)
    missing_in_source = sorted(methods_b - methods_a)

    attrs_a = fp_a.attribute_set
    attrs_b = fp_b.attribute_set
    extra_in_source = sorted(attrs_a - attrs_b)
    extra_in_target = sorted(attrs_b - attrs_a)

    # Confidence: higher when shared bases exist
    shared_bases = set(fp_a.base_classes) & set(fp_b.base_classes)
    confidence = similarity
    if shared_bases:
        confidence = min(1.0, confidence + 0.1)

    return SymmetryRelation(
        source=fp_a.name,
        target=fp_b.name,
        symmetry_type=sym_type,
        intent=intent,
        similarity=round(similarity, 4),
        confidence=round(confidence, 4),
        missing_in_source=missing_in_source,
        missing_in_target=missing_in_target,
        extra_in_source=extra_in_source,
        extra_in_target=extra_in_target,
    )


_MIRROR_PREFIXES = [
    ("client", "server"),
    ("server", "client"),
    ("sender", "receiver"),
    ("receiver", "sender"),
    ("producer", "consumer"),
    ("consumer", "producer"),
    ("reader", "writer"),
    ("writer", "reader"),
    ("input", "output"),
    ("output", "input"),
    ("src", "dst"),
    ("dst", "src"),
]


def _are_mirror_names(name_a: str, name_b: str) -> bool:
    """Heuristic check for mirror-image naming conventions."""
    a = name_a.lower().replace("_", "")
    b = name_b.lower().replace("_", "")
    for prefix_a, prefix_b in _MIRROR_PREFIXES:
        if a.startswith(prefix_a) and b.startswith(prefix_b):
            return True
    # Also check if one name contains the complement
    for prefix_a, prefix_b in _MIRROR_PREFIXES:
        if prefix_a in a and prefix_b in b:
            return True
    return False
