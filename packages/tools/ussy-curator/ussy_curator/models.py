"""Shared data models for Curator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Link:
    """Represents a link from one document to another."""
    source: Path
    target: Path
    text: str = ""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Link):
            return NotImplemented
        return self.source == other.source and self.target == other.target

    def __hash__(self) -> int:
        return hash((self.source, self.target))


@dataclass
class Document:
    """Central document model tying together all curation instruments."""
    path: Path
    content: str = field(default="", repr=False)
    title: str = field(default="")
    author: str = field(default="")
    tags: list[str] = field(default_factory=list)
    date: str = field(default="")
    reviewed: str = field(default="")
    audience: str = field(default="")
    doc_type: str = field(default="")
    word_count: int = field(default=0)
    keywords: list[str] = field(default_factory=list)
    backlinks: list[Path] = field(default_factory=list)
    content_summary: str = field(default="")
    referenced_code: list[str] = field(default_factory=list)
    last_accessed: str = field(default="")
    accession_number: str = field(default="")

    # Instrument results (populated by __post_init__ or later)
    marc_record: Any = field(default=None, repr=False)
    classification: Any = field(default=None, repr=False)
    conservation_report: Any = field(default=None, repr=False)
    provenance_chain: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.title:
            self.title = self._infer_title()
        if not self.author:
            self.author = self._infer_author()
        if not self.date:
            self.date = self._infer_date()
        if not self.word_count:
            self.word_count = len(self.content.split())
        if not self.keywords:
            self.keywords = self._extract_keywords()
        if not self.content_summary:
            self.content_summary = self._make_summary()
        if not self.doc_type:
            self.doc_type = self._infer_doc_type()

    def _infer_title(self) -> str:
        from ussy_curator.utils import infer_title
        return infer_title(self.path, self.content)

    def _infer_author(self) -> str:
        from ussy_curator.utils import infer_author
        return infer_author(self.path, self.content)

    def _infer_date(self) -> str:
        from ussy_curator.utils import git_creation_date
        return git_creation_date(self.path)

    def _extract_keywords(self) -> list[str]:
        from ussy_curator.utils import extract_keywords
        return extract_keywords(self.content)

    def _make_summary(self) -> str:
        from ussy_curator.utils import make_summary
        return make_summary(self.content)

    def _infer_doc_type(self) -> str:
        from ussy_curator.utils import classify_doc_type
        return classify_doc_type(self.path)
