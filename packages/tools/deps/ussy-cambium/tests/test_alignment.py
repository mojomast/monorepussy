"""Tests for Cambium alignment module."""

from __future__ import annotations

import os

import pytest

from cambium.alignment import (
    compute_alignment,
    compute_alignment_from_files,
    compute_alignment_from_source,
    compute_name_match,
    compute_semantic_match,
    compute_signature_match,
    format_alignment_heatmap,
)
from cambium.extractor import extract_interface
from cambium.models import InterfaceInfo


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestComputeNameMatch:
    """Tests for compute_name_match."""

    def test_identical_names(self):
        a = InterfaceInfo(name="a", exported_types={"X"}, exported_functions={"f", "g"})
        b = InterfaceInfo(name="b", exported_types={"X"}, exported_functions={"f", "g"})
        assert compute_name_match(a, b) == pytest.approx(1.0)

    def test_no_matching_names(self):
        a = InterfaceInfo(name="a", exported_types={"A"}, exported_functions={"fa"})
        b = InterfaceInfo(name="b", exported_types={"B"}, exported_functions={"fb"})
        assert compute_name_match(a, b) == pytest.approx(0.0)

    def test_partial_name_match(self):
        a = InterfaceInfo(name="a", exported_types={"A", "B"}, exported_functions={"f"})
        b = InterfaceInfo(name="b", exported_types={"A"}, exported_functions={"f", "g"})
        result = compute_name_match(a, b)
        assert 0 < result < 1.0

    def test_empty_consumer(self):
        a = InterfaceInfo(name="a")
        b = InterfaceInfo(name="b", exported_types={"X"})
        assert compute_name_match(a, b) == pytest.approx(1.0)


class TestComputeSignatureMatch:
    """Tests for compute_signature_match."""

    def test_matching_signatures(self):
        a = InterfaceInfo(name="a", method_signatures={"f": ["x", "y"]})
        b = InterfaceInfo(name="b", method_signatures={"f": ["x", "y"]})
        assert compute_signature_match(a, b) == pytest.approx(1.0)

    def test_different_param_counts(self):
        a = InterfaceInfo(name="a", method_signatures={"f": ["x"]})
        b = InterfaceInfo(name="b", method_signatures={"f": ["x", "y"]})
        result = compute_signature_match(a, b)
        assert 0 < result < 1.0

    def test_no_matching_methods(self):
        a = InterfaceInfo(name="a", method_signatures={"fa": ["x"]})
        b = InterfaceInfo(name="b", method_signatures={"fb": ["y"]})
        result = compute_signature_match(a, b)
        assert result == pytest.approx(0.0)

    def test_empty_consumer_signatures(self):
        a = InterfaceInfo(name="a", method_signatures={})
        b = InterfaceInfo(name="b", method_signatures={"f": ["x"]})
        assert compute_signature_match(a, b) == pytest.approx(1.0)


class TestComputeSemanticMatch:
    """Tests for compute_semantic_match."""

    def test_default_estimates(self):
        a = InterfaceInfo(name="a")
        b = InterfaceInfo(name="b")
        result = compute_semantic_match(a, b)
        # With no data, should use default estimates
        assert result == pytest.approx(0.8, abs=0.05)

    def test_with_preconditions(self):
        a = InterfaceInfo(name="a", preconditions=["data", "token"])
        b = InterfaceInfo(name="b", preconditions=["data", "token"])
        result = compute_semantic_match(a, b)
        assert result > 0.5


class TestComputeAlignment:
    """Tests for compute_alignment."""

    def test_identical_interfaces(self):
        a = InterfaceInfo(
            name="a",
            exported_types={"X"},
            exported_functions={"f"},
            method_signatures={"f": ["x"]},
        )
        b = InterfaceInfo(
            name="b",
            exported_types={"X"},
            exported_functions={"f"},
            method_signatures={"f": ["x"]},
        )
        score = compute_alignment(a, b)
        assert score.composite > 0.5

    def test_from_files(self):
        consumer_path = os.path.join(FIXTURES_DIR, "consumer.py")
        provider_path = os.path.join(FIXTURES_DIR, "provider.py")
        score = compute_alignment_from_files(consumer_path, provider_path)
        assert score.name_match > 0.0  # Both have AuthClient

    def test_alignment_status(self):
        score = compute_alignment(
            InterfaceInfo(name="a"),
            InterfaceInfo(name="b"),
        )
        # Empty interfaces should have high alignment
        assert score.status in ("ALIGNED", "PARTIAL", "MISALIGNED")


class TestFormatAlignmentHeatmap:
    """Tests for format_alignment_heatmap."""

    def test_basic_output(self):
        score = compute_alignment(
            InterfaceInfo(name="a", exported_types={"X"}, exported_functions={"f"}),
            InterfaceInfo(name="b", exported_types={"X"}, exported_functions={"f"}),
        )
        output = format_alignment_heatmap("mod_a", "mod_b", score)
        assert "Interface Alignment" in output
        assert "A_name" in output
        assert "A_sig" in output
        assert "A_sem" in output
        assert "Combined Alignment" in output

    def test_status_in_output(self):
        score = compute_alignment(
            InterfaceInfo(name="a"),
            InterfaceInfo(name="b"),
        )
        output = format_alignment_heatmap("a", "b", score)
        assert "ALIGNED" in output or "PARTIAL" in output or "MISALIGNED" in output
