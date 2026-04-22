"""Tests for curator.models."""

from __future__ import annotations

from pathlib import Path

import pytest

from curator.models import Document, Link


class TestLink:
    def test_equality(self) -> None:
        a = Link(Path("a.md"), Path("b.md"), "x")
        b = Link(Path("a.md"), Path("b.md"), "y")
        assert a == b

    def test_hash(self) -> None:
        a = Link(Path("a.md"), Path("b.md"))
        b = Link(Path("a.md"), Path("b.md"))
        assert hash(a) == hash(b)

    def test_inequality(self) -> None:
        a = Link(Path("a.md"), Path("b.md"))
        b = Link(Path("a.md"), Path("c.md"))
        assert a != b


class TestDocument:
    def test_title_inference(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("# My Title\n")
        doc = Document(path=f, content=f.read_text())
        assert doc.title == "My Title"

    def test_author_inference(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("---\nauthor: Ada\n---\n")
        doc = Document(path=f, content=f.read_text())
        assert doc.author == "Ada"

    def test_word_count(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("One two three.")
        doc = Document(path=f, content=f.read_text())
        assert doc.word_count == 3

    def test_keywords_extracted(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("python python code testing")
        doc = Document(path=f, content=f.read_text())
        assert "python" in doc.keywords

    def test_default_backlinks(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("Hello.")
        doc = Document(path=f, content="Hello.")
        assert doc.backlinks == []

    def test_content_summary(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("This is a simple document.")
        doc = Document(path=f, content=f.read_text())
        assert "simple" in doc.content_summary

    def test_date_set(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("hello")
        doc = Document(path=f, content="hello")
        assert doc.date != ""

    def test_doc_type_inferred(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("hello")
        doc = Document(path=f, content="hello")
        assert doc.doc_type == "markdown"
