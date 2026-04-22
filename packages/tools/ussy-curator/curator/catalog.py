"""MARC Cataloger — Structured metadata with controlled vocabulary."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from curator.utils import (
    parse_yaml_frontmatter,
    infer_title,
    infer_author,
    git_creation_date,
    classify_doc_type,
    extract_markdown_links,
)


class ControlledVocabulary:
    """Maps free-form tags to controlled canonical terms."""

    SYNONYMS: dict[str, str] = {
        "api": "application_programming_interface",
        "apis": "application_programming_interface",
        "database": "databases",
        "databases": "databases",
        "db": "databases",
        "sql": "databases",
        "deploy": "deployment",
        "deployment": "deployment",
        "docker": "containerization",
        "containers": "containerization",
        "kubernetes": "orchestration",
        "k8s": "orchestration",
        "testing": "quality_assurance",
        "tests": "quality_assurance",
        "qa": "quality_assurance",
        "frontend": "user_interface",
        "ui": "user_interface",
        "backend": "server_side",
        "auth": "authentication",
        "authentication": "authentication",
        "security": "cybersecurity",
        "devops": "operations",
        "setup": "installation",
        "install": "installation",
        "guide": "documentation",
        "tutorial": "education",
        "howto": "education",
        "overview": "introduction",
        "intro": "introduction",
    }

    @classmethod
    def resolve(cls, tag: str) -> str | None:
        return cls.SYNONYMS.get(tag.lower().strip())


class MARCRecord:
    """
    Represents a bibliographic record for a documentation file.
    Fields map MARC21 conventions to documentation metadata.
    """

    FIELD_MAP = {
        "245": "title",
        "100": "creator",
        "650": "subject_heading",
        "260": "publication",
        "500": "general_note",
        "856": "url",
        "901": "doc_type",
        "902": "audience",
        "903": "review_date",
        "904": "staleness_score",
    }

    def __init__(self, doc_path: Path) -> None:
        self.path = doc_path
        self.fields = self._extract_fields()

    def _extract_fields(self) -> dict[str, Any]:
        """Extracts MARC-like fields from YAML frontmatter or infers from content."""
        frontmatter = parse_yaml_frontmatter(self.path)
        return {
            "245": frontmatter.get("title", infer_title(self.path)),
            "100": frontmatter.get("author", infer_author(self.path)),
            "650": self._normalize_subject(frontmatter.get("tags", [])),
            "260": {"c": frontmatter.get("date", git_creation_date(self.path))},
            "903": frontmatter.get("reviewed", None),
            "901": classify_doc_type(self.path),
        }

    def _normalize_subject(self, raw_tags: list[str] | str) -> list[str]:
        """Maps free-form tags to controlled vocabulary using synonym ring."""
        controlled: list[str] = []
        if isinstance(raw_tags, str):
            raw_tags = [raw_tags]
        for tag in raw_tags:
            canonical = ControlledVocabulary.resolve(tag)
            if canonical:
                controlled.append(canonical)
        return controlled

    def completeness_score(self) -> float:
        """
        Measures cataloging completeness as a ratio of populated core fields.
        """
        weights = {
            "245": 1.0,
            "100": 0.9,
            "650": 0.8,
            "260": 0.6,
            "903": 0.7,
            "901": 0.5,
        }
        total = sum(weights.values())
        populated = sum(
            w for field, w in weights.items()
            if self.fields.get(field)
        )
        return populated / total

    def cross_reference_consistency(self, collection: dict[Path, Any]) -> dict[str, float]:
        """
        Verifies that linked documents exist and have reciprocal links.
        Returns link integrity score.
        """
        links = extract_markdown_links(self.path)
        if not links:
            return {"integrity": 1.0, "reciprocity": 1.0}

        valid = 0
        reciprocal = 0
        for link in links:
            target = link.target
            if target in collection:
                valid += 1
                target_doc = collection[target]
                backlinks = getattr(target_doc, "backlinks", [])
                if self.path in backlinks:
                    reciprocal += 1

        return {
            "integrity": valid / len(links),
            "reciprocity": reciprocal / len(links),
        }
