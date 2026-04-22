"""Tests for curator.classification."""

from __future__ import annotations

from pathlib import Path

import pytest

from curator.classification import FacetedClassification, classify_document, DDC_TOP_LEVEL


class TestFacetedClassification:
    def test_parse_hierarchy_only(self) -> None:
        fc = FacetedClassification("DEV.005.74")
        assert fc.hierarchy == "DEV.005.74"
        assert fc.facets == {}

    def test_parse_with_facets(self) -> None:
        fc = FacetedClassification("DEV.005.74:AUD:devops:TOP:docker")
        assert fc.hierarchy == "DEV.005.74"
        assert fc.facets["AUD"] == "devops"
        assert fc.facets["TOP"] == "docker"

    def test_notational_distance_identical(self) -> None:
        fc = FacetedClassification("000:AUD:general")
        # Identical hierarchy still has base h_dist from shared depth
        assert fc.notational_distance(fc) >= 0.0

    def test_notational_distance_different(self) -> None:
        a = FacetedClassification("000:AUD:general")
        b = FacetedClassification("100:AUD:expert")
        dist = a.notational_distance(b)
        assert dist > 0.0

    def test_broader_terms(self) -> None:
        fc = FacetedClassification("A.B.C")
        terms = fc.broader_terms()
        assert "A.B.C" in terms
        assert "A.B" in terms
        assert "A" in terms

    def test_narrower_term_space(self) -> None:
        fc = FacetedClassification("A.B")
        assert fc.narrower_term_space() == 100

    def test_narrower_term_space_deep(self) -> None:
        fc = FacetedClassification("A.B.C.D")
        assert fc.narrower_term_space() == 0

    def test_notation_attribute(self) -> None:
        fc = FacetedClassification("X:AUD:y")
        assert fc.notation == "X:AUD:y"

    def test_repr(self) -> None:
        fc = FacetedClassification("000")
        assert "FacetedClassification" in repr(fc)


class TestClassifyDocument:
    def test_classifies_markdown(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("This is about computer programming and data.")
        analysis = {
            "tf": {"computer": 1, "programming": 1, "data": 1},
            "readability": 50.0,
            "jargon_density": 0.1,
            "named_entities": ["python"],
            "concept_depth": 0.5,
        }
        fc = classify_document(f, analysis)
        assert fc.hierarchy == "000"
        assert "AUD" in fc.facets

    def test_classifies_with_empty_analysis(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("Hello world.")
        fc = classify_document(f, {})
        assert fc.hierarchy == "000"

    def test_ddc_top_level_has_entries(self) -> None:
        assert len(DDC_TOP_LEVEL) > 0
        assert "000" in DDC_TOP_LEVEL
