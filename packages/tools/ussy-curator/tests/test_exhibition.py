"""Tests for curator.exhibition."""

from __future__ import annotations

from pathlib import Path

import pytest

from curator.exhibition import Exhibition
from curator.models import Document
from curator.classification import FacetedClassification
from curator.conservation import ConservationReport


def _make_doc(tmp_path: Path, name: str, content: str, notation: str) -> Document:
    p = tmp_path / name
    p.write_text(content)
    doc = Document(path=p, content=content)
    doc.classification = FacetedClassification(notation)
    doc.conservation_report = ConservationReport(p)
    return doc


class TestExhibition:
    def test_curate_selects_documents(self, tmp_path: Path) -> None:
        docs = [
            _make_doc(tmp_path, "a.md", "Python programming guide", "000:AUD:beginner"),
            _make_doc(tmp_path, "b.md", "Docker deployment tips", "000:AUD:expert"),
        ]
        ex = Exhibition("DevExpo", "programming", {"level": "general"}, max_items=5)
        ex.curate(docs)
        assert len(ex.selection) <= 5
        assert len(ex.selection) > 0

    def test_curate_respects_max_items(self, tmp_path: Path) -> None:
        docs = [
            _make_doc(tmp_path, f"{i}.md", f"Doc {i}", f"000:AUD:general")
            for i in range(10)
        ]
        ex = Exhibition("BigExpo", "docs", {"level": "general"}, max_items=3)
        ex.curate(docs)
        assert len(ex.selection) <= 3

    def test_diverse_select_limits_branch(self, tmp_path: Path) -> None:
        docs = [
            _make_doc(tmp_path, f"{i}.md", f"Doc {i}", f"000:AUD:general")
            for i in range(10)
        ]
        ex = Exhibition("Test", "docs", {"level": "general"}, max_items=10)
        ex.curate(docs)
        branch_counts = {}
        for d in ex.selection:
            b = d.classification.hierarchy.split(".")[0]
            branch_counts[b] = branch_counts.get(b, 0) + 1
        assert all(c <= 3 for c in branch_counts.values())

    def test_didactic_label_beginner(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path, "a.md", "A very simple guide for beginners to learn.", "000:AUD:beginner")
        ex = Exhibition("E", "docs", {"level": "beginner"})
        label = ex.didactic_label(doc)
        assert len(label) <= 90

    def test_didactic_label_expert(self, tmp_path: Path) -> None:
        text = "Advanced computational methodologies for distributed systems."
        doc = _make_doc(tmp_path, "a.md", text, "000:AUD:expert")
        ex = Exhibition("E", "docs", {"level": "expert"})
        label = ex.didactic_label(doc)
        assert len(label) <= 210

    def test_rotation_schedule(self, tmp_path: Path) -> None:
        docs = [
            _make_doc(tmp_path, f"{i}.md", f"Doc {i}", f"000:AUD:general")
            for i in range(10)
        ]
        ex = Exhibition("Rot", "docs", {"level": "general"}, max_items=5)
        ex.curate(docs)
        schedule = ex.generate_rotation_schedule(docs)
        assert len(schedule) == 4
        for entry in schedule:
            assert "retained" in entry
            assert "rotated_in" in entry

    def test_theme_relevance(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path, "a.md", "Python programming", "000:AUD:general")
        ex = Exhibition("PyExpo", "python", {"level": "general"})
        rel = ex._theme_relevance(doc)
        assert rel > 0.0

    def test_diversity_bonus(self, tmp_path: Path) -> None:
        doc1 = _make_doc(tmp_path, "a.md", "Doc A", "000:AUD:general:TOP:python")
        doc2 = _make_doc(tmp_path, "b.md", "Doc B", "000:AUD:expert:TOP:docker")
        ex = Exhibition("E", "docs", {"level": "general"})
        ex.selection = [doc1]
        bonus = ex._diversity_bonus(doc2)
        assert bonus > 1.0

    def test_crowd_penalty(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path, "a.md", "Doc", "000:AUD:general")
        ex = Exhibition("E", "docs", {"level": "general"})
        ex.selection = [doc]
        penalty = ex._crowd_penalty(doc)
        assert penalty > 1.0
