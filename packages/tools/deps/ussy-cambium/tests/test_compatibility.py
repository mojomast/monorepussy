"""Tests for Cambium compatibility module."""

from __future__ import annotations

import os

import pytest

from cambium.compatibility import (
    compute_compatibility,
    compute_compatibility_from_files,
    compute_compatibility_from_source,
    compute_type_similarity,
    compute_version_overlap,
    jaccard_similarity,
)
from cambium.extractor import extract_interface
from cambium.models import InterfaceInfo


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestJaccardSimilarity:
    """Tests for jaccard_similarity."""

    def test_identical_sets(self):
        assert jaccard_similarity({"a", "b"}, {"a", "b"}) == pytest.approx(1.0)

    def test_disjoint_sets(self):
        assert jaccard_similarity({"a"}, {"b"}) == pytest.approx(0.0)

    def test_partial_overlap(self):
        result = jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert result == pytest.approx(2.0 / 4.0)

    def test_empty_sets(self):
        assert jaccard_similarity(set(), set()) == pytest.approx(1.0)

    def test_one_empty(self):
        assert jaccard_similarity({"a"}, set()) == pytest.approx(0.0)


class TestComputeTypeSimilarity:
    """Tests for compute_type_similarity."""

    def test_identical_interfaces(self):
        a = InterfaceInfo(name="a", exported_types={"Foo"}, exported_functions={"bar"})
        b = InterfaceInfo(name="b", exported_types={"Foo"}, exported_functions={"bar"})
        assert compute_type_similarity(a, b) == pytest.approx(1.0)

    def test_different_interfaces(self):
        a = InterfaceInfo(name="a", exported_types={"Foo"}, exported_functions={"bar"})
        b = InterfaceInfo(name="b", exported_types={"Baz"}, exported_functions={"qux"})
        assert compute_type_similarity(a, b) == pytest.approx(0.0)

    def test_partial_overlap(self):
        a = InterfaceInfo(name="a", exported_types={"Foo", "Bar"}, exported_functions={"baz"})
        b = InterfaceInfo(name="b", exported_types={"Foo"}, exported_functions={"baz", "qux"})
        result = compute_type_similarity(a, b)
        assert 0 < result < 1.0


class TestComputeVersionOverlap:
    """Tests for compute_version_overlap."""

    def test_full_overlap(self):
        result = compute_version_overlap(("2.0.0", "3.0.0"), ("2.0.0", "3.0.0"))
        assert result == pytest.approx(1.0)

    def test_no_overlap(self):
        result = compute_version_overlap(("1.0.0", "2.0.0"), ("3.0.0", "4.0.0"))
        assert result == pytest.approx(0.0)

    def test_partial_overlap(self):
        result = compute_version_overlap(("2.0.0", "4.0.0"), ("3.0.0", "5.0.0"))
        # Overlap: 3.0-4.0, Union: 2.0-5.0, ratio = 1.0/3.0
        assert result == pytest.approx(1.0 / 3.0, rel=0.02)


class TestComputeCompatibility:
    """Tests for compute_compatibility."""

    def test_identical_interfaces(self):
        a = InterfaceInfo(name="a", exported_types={"X"}, exported_functions={"f"})
        b = InterfaceInfo(name="b", exported_types={"X"}, exported_functions={"f"})
        score = compute_compatibility(a, b)
        assert score.composite > 0.5

    def test_no_overlap_interfaces(self):
        a = InterfaceInfo(name="a", exported_types={"X"}, exported_functions={"f"})
        b = InterfaceInfo(name="b", exported_types={"Y"}, exported_functions={"g"})
        score = compute_compatibility(a, b)
        assert score.type_similarity == pytest.approx(0.0)

    def test_from_source(self):
        consumer = "class A:\n    def foo(self): pass\n"
        provider = "class A:\n    def foo(self): pass\n"
        score = compute_compatibility_from_source(consumer, provider)
        assert score.composite > 0.0

    def test_from_files(self):
        consumer_path = os.path.join(FIXTURES_DIR, "consumer.py")
        provider_path = os.path.join(FIXTURES_DIR, "provider.py")
        score = compute_compatibility_from_files(consumer_path, provider_path)
        # Both have AuthClient, so should have some compatibility
        assert score.type_similarity > 0.0

    def test_with_version_ranges(self):
        a = InterfaceInfo(name="a", exported_types={"X"}, exported_functions={"f"})
        b = InterfaceInfo(name="b", exported_types={"X"}, exported_functions={"f"})
        score = compute_compatibility(
            a, b,
            consumer_version_range=("2.0.0", "3.0.0"),
            provider_version_range=("2.0.0", "3.0.0"),
        )
        assert score.version_overlap == pytest.approx(1.0)
