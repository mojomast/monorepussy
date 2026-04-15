"""Tests for the collation module."""

from pathlib import Path

import pytest

from stemma.collation import (
    collate,
    collate_path,
    identify_variation_units,
    load_witnesses,
    load_witnesses_from_strings,
)
from stemma.models import VariantType, Witness


class TestLoadWitnesses:
    def test_load_from_directory(self, fixtures_dir):
        witnesses = load_witnesses(fixtures_dir)
        assert len(witnesses) == 5
        labels = {w.label for w in witnesses}
        assert "A" in labels

    def test_load_from_file(self, fixtures_dir):
        path = fixtures_dir / "payment_a.py"
        witnesses = load_witnesses(path)
        assert len(witnesses) == 1
        assert witnesses[0].label == "A"

    def test_load_nonexistent_path(self):
        witnesses = load_witnesses(Path("/nonexistent/path"))
        assert witnesses == []

    def test_witness_lines_loaded(self, fixtures_dir):
        witnesses = load_witnesses(fixtures_dir)
        # Each witness should have lines
        for w in witnesses:
            assert len(w.lines) > 0


class TestLoadWitnessesFromStrings:
    def test_basic(self):
        sources = {
            "A": "x = 1\ny = 2",
            "B": "x = 1\ny = 3",
        }
        witnesses = load_witnesses_from_strings(sources)
        assert len(witnesses) == 2
        labels = {w.label for w in witnesses}
        assert labels == {"A", "B"}


class TestIdentifyVariationUnits:
    def test_unanimous_positions(self):
        aligned = {
            0: {"A": "x = 1", "B": "x = 1", "C": "x = 1"},
        }
        witnesses = [
            Witness(label="A", source="a.py"),
            Witness(label="B", source="b.py"),
            Witness(label="C", source="c.py"),
        ]
        units = identify_variation_units(aligned, witnesses)
        assert len(units) == 1
        assert not units[0].is_variant

    def test_variant_positions(self):
        aligned = {
            0: {"A": "x = 1", "B": "x = 1", "C": "x = 2"},
        }
        witnesses = [
            Witness(label="A", source="a.py"),
            Witness(label="B", source="b.py"),
            Witness(label="C", source="c.py"),
        ]
        units = identify_variation_units(aligned, witnesses)
        assert len(units) == 1
        assert units[0].is_variant
        assert len(units[0].readings) == 2

    def test_omission_detection(self):
        aligned = {
            0: {"A": "log.info(x)", "B": "log.info(x)", "C": ""},
        }
        witnesses = [
            Witness(label="A", source="a.py"),
            Witness(label="B", source="b.py"),
            Witness(label="C", source="c.py"),
        ]
        units = identify_variation_units(aligned, witnesses)
        assert units[0].is_variant
        # Should have an omission reading
        texts = [r.text for r in units[0].readings]
        assert "(absent)" in texts


class TestCollate:
    def test_collate_basic(self, all_witnesses):
        result = collate(all_witnesses)
        assert len(result.witnesses) == 5
        assert result.total_lines > 0
        assert result.variant_count > 0

    def test_collate_empty(self):
        result = collate([])
        assert result.witnesses == []
        assert result.total_lines == 0

    def test_collate_single_witness(self):
        w = Witness(label="A", source="a.py", lines=["x = 1", "y = 2"])
        result = collate([w])
        assert len(result.witnesses) == 1
        # Single witness should have no variants
        assert result.variant_count == 0

    def test_collate_identical_witnesses(self):
        a = Witness(label="A", source="a.py", lines=["x = 1", "y = 2"])
        b = Witness(label="B", source="b.py", lines=["x = 1", "y = 2"])
        result = collate([a, b])
        assert result.variant_count == 0

    def test_collate_path(self, fixtures_dir):
        result = collate_path(fixtures_dir)
        assert len(result.witnesses) == 5
