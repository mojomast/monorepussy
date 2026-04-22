"""Tests for curator.catalog."""

from __future__ import annotations

from pathlib import Path

import pytest

from ussy_curator.catalog import ControlledVocabulary, MARCRecord


class TestControlledVocabulary:
    def test_resolve_synonym(self) -> None:
        assert ControlledVocabulary.resolve("api") == "application_programming_interface"

    def test_resolve_databases(self) -> None:
        assert ControlledVocabulary.resolve("db") == "databases"

    def test_resolve_unknown(self) -> None:
        assert ControlledVocabulary.resolve("xyz_unknown") is None

    def test_case_insensitive(self) -> None:
        assert ControlledVocabulary.resolve("API") == "application_programming_interface"


class TestMARCRecord:
    def test_extracts_title_from_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("---\ntitle: My Doc\n---\n\n# Body\n")
        record = MARCRecord(f)
        assert record.fields["245"] == "My Doc"

    def test_infers_title_when_missing(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("No frontmatter here.")
        record = MARCRecord(f)
        assert record.fields["245"] == "Doc"

    def test_normalizes_tags(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("---\ntags: [api, docker]\n---\n")
        record = MARCRecord(f)
        assert "application_programming_interface" in record.fields["650"]
        assert "containerization" in record.fields["650"]

    def test_completeness_score_full(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("---\ntitle: T\nauthor: A\ntags: [api]\ndate: 2024-01-01\nreviewed: 2024-06-01\n---\n")
        record = MARCRecord(f)
        score = record.completeness_score()
        assert score > 0.9

    def test_completeness_score_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("Body only.")
        record = MARCRecord(f)
        score = record.completeness_score()
        assert 0.0 < score < 1.0

    def test_cross_reference_integrity(self, tmp_path: Path) -> None:
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        a.write_text("See [b](b.md)")
        b.write_text("See [a](a.md)")
        record = MARCRecord(a)

        from ussy_curator.models import Document
        docs = {
            a: Document(path=a, content=a.read_text(), backlinks=[b]),
            b: Document(path=b, content=b.read_text(), backlinks=[a]),
        }
        result = record.cross_reference_consistency(docs)
        assert result["integrity"] == 1.0
        assert result["reciprocity"] == 1.0

    def test_cross_reference_broken_link(self, tmp_path: Path) -> None:
        a = tmp_path / "a.md"
        a.write_text("See [missing](missing.md)")
        record = MARCRecord(a)
        result = record.cross_reference_consistency({})
        assert result["integrity"] == 0.0

    def test_field_map_coverage(self) -> None:
        assert "245" in MARCRecord.FIELD_MAP
        assert MARCRecord.FIELD_MAP["245"] == "title"
