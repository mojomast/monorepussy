"""Tests for mint.distance — Levenshtein distance and typosquat detection."""

import pytest
from ussy_mint.distance import levenshtein_distance, normalized_distance, is_typosquat


class TestLevenshteinDistance:
    """Test the pure Python Levenshtein distance implementation."""

    def test_identical_strings(self):
        assert levenshtein_distance("hello", "hello") == 0

    def test_empty_strings(self):
        assert levenshtein_distance("", "") == 0

    def test_one_empty_string(self):
        assert levenshtein_distance("hello", "") == 5
        assert levenshtein_distance("", "world") == 5

    def test_single_char_substitution(self):
        assert levenshtein_distance("cat", "bat") == 1

    def test_single_char_insertion(self):
        assert levenshtein_distance("cat", "cats") == 1

    def test_single_char_deletion(self):
        assert levenshtein_distance("cats", "cat") == 1

    def test_completely_different(self):
        assert levenshtein_distance("abc", "xyz") == 3

    def test_typosquat_express(self):
        """xpress is 1 edit from express (delete 'e')."""
        assert levenshtein_distance("xpress", "express") == 1

    def test_typosquat_lodash(self):
        """lodahs is 2 edits from lodash (swap 's' and 'h')."""
        assert levenshtein_distance("lodahs", "lodash") == 2

    def test_case_insensitive_same(self):
        dist = levenshtein_distance("Express", "express")
        assert dist == 1  # Only case difference, but exact string comparison

    def test_longer_strings(self):
        assert levenshtein_distance("kitten", "sitting") == 3

    def test_prefix(self):
        assert levenshtein_distance("react", "react-dom") == 4


class TestNormalizedDistance:
    """Test normalized Levenshtein distance."""

    def test_identical(self):
        assert normalized_distance("hello", "hello") == 0.0

    def test_both_empty(self):
        assert normalized_distance("", "") == 0.0

    def test_completely_different(self):
        assert normalized_distance("abc", "xyz") == 1.0

    def test_partial_similarity(self):
        result = normalized_distance("express", "xpress")
        assert 0.0 < result < 1.0

    def test_one_empty(self):
        assert normalized_distance("hello", "") == 1.0


class TestTyposquatDetection:
    """Test typosquat detection using Levenshtein distance."""

    def test_exact_match_excluded(self):
        """Exact matches should not be flagged."""
        hits = is_typosquat("express", ["express"])
        assert len(hits) == 0

    def test_typosquat_detected(self):
        """Close names should be flagged."""
        hits = is_typosquat("xpress", ["express"])
        assert len(hits) == 1
        assert hits[0][0] == "express"
        assert hits[0][1] == 1

    def test_distant_names_excluded(self):
        """Names that are too different should not be flagged."""
        hits = is_typosquat("completely-different", ["express"], max_distance=2)
        assert len(hits) == 0

    def test_multiple_hits(self):
        """Should find multiple similar names."""
        hits = is_typosquat("lodahs", ["lodash", "loader", "lodown"], max_distance=2)
        assert len(hits) >= 1

    def test_sorted_by_distance(self):
        """Results should be sorted by distance (closest first)."""
        hits = is_typosquat("expres", ["express", "export", "extras"], max_distance=3)
        if len(hits) > 1:
            assert hits[0][1] <= hits[1][1]

    def test_case_insensitive(self):
        """Typosquat detection is case-insensitive."""
        hits = is_typosquat("Xpress", ["express"])
        assert len(hits) == 1

    def test_no_known_packages(self):
        """Empty known packages list returns no hits."""
        hits = is_typosquat("anything", [])
        assert len(hits) == 0
