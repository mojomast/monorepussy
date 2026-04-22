"""Classification System — Hierarchical faceted organization."""

from __future__ import annotations

from pathlib import Path
from typing import Any


# DDC-like top-level classes mapped to software documentation domains
DDC_TOP_LEVEL: dict[str, list[str]] = {
    "000": ["computer", "software", "programming", "code", "algorithm", "data"],
    "100": ["philosophy", "logic", "reasoning", "ethics", "principles"],
    "200": ["religion", "culture", "community", "values"],
    "300": ["social", "management", "organization", "team", "process"],
    "400": ["language", "syntax", "grammar", "semantics", "localization"],
    "500": ["science", "mathematics", "statistics", "analysis"],
    "600": ["technology", "engineering", "hardware", "infrastructure"],
    "700": ["arts", "design", "ui", "ux", "creative", "media"],
    "800": ["literature", "writing", "narrative", "story"],
    "900": ["history", "archive", "legacy", "migration"],
}


class FacetedClassification:
    """
    Implements faceted classification for docs.
    Facets are orthogonal dimensions combined with ':' separator.
    """

    FACETS = ["AUD", "DEP", "TOP", "FMT", "EXP"]

    def __init__(self, notation: str) -> None:
        self.notation = notation
        self.hierarchy, self.facets = self._parse(notation)

    def _parse(self, notation: str) -> tuple[str, dict[str, str]]:
        """Parses 'DEV.005.74:AUD:devops:TOP:docker' into hierarchy and facets."""
        parts = notation.split(":")
        hierarchy = parts[0]
        facet_pairs = parts[1:]
        facets: dict[str, str] = {}
        for i in range(0, len(facet_pairs), 2):
            if i + 1 < len(facet_pairs):
                facets[facet_pairs[i]] = facet_pairs[i + 1]
        return hierarchy, facets

    def notational_distance(self, other: FacetedClassification) -> float:
        """
        Calculates semantic distance between two classification notations.
        """
        # Hierarchy distance
        a_parts = self.hierarchy.split(".")
        b_parts = other.hierarchy.split(".")
        shared = sum(1 for a, b in zip(a_parts, b_parts) if a == b)
        h_dist = 1.0 / (1 + shared)

        # Facet distance (Jaccard on facet values)
        a_facet_values = set(self.facets.values())
        b_facet_values = set(other.facets.values())
        union = a_facet_values | b_facet_values
        intersection = a_facet_values & b_facet_values
        f_dist = 1.0 - (len(intersection) / len(union)) if union else 0.0

        alpha, beta = 0.6, 0.4
        return alpha * h_dist + beta * f_dist

    def broader_terms(self) -> list[str]:
        """Returns broader hierarchical terms (DDC truncation)."""
        parts = self.hierarchy.split(".")
        return [
            ".".join(parts[:i])
            for i in range(len(parts), 0, -1)
        ]

    def narrower_term_space(self) -> int:
        """Estimates available narrow terms (hierarchical capacity)."""
        parts = self.hierarchy.split(".")
        depth = len(parts)
        return 10 ** (4 - depth) if depth < 4 else 0

    def __repr__(self) -> str:
        return f"FacetedClassification({self.notation!r})"


def classify_document(doc_path: Path, content_analysis: dict[str, Any]) -> FacetedClassification:
    """
    Auto-classifies a document using content analysis.
    Returns DDC-like hierarchy + facets.
    """
    # Determine main class from content keywords
    tf = content_analysis.get("tf", {})
    class_scores: dict[str, float] = {}
    for class_code, keywords in DDC_TOP_LEVEL.items():
        score = sum(tf.get(kw, 0) for kw in keywords)
        class_scores[class_code] = score

    main_class = max(class_scores, key=class_scores.get) if class_scores else "000"

    # Determine facets from metadata and content
    from ussy_curator.utils import (
        infer_audience,
        infer_department,
        infer_topic,
        infer_format,
        infer_expertise_level,
    )

    readability = content_analysis.get("readability", 50.0)
    jargon_density = content_analysis.get("jargon_density", 0.1)
    named_entities = content_analysis.get("named_entities", [])
    concept_depth = content_analysis.get("concept_depth", 0.5)

    facets = {
        "AUD": infer_audience(readability, jargon_density),
        "DEP": infer_department(doc_path),
        "TOP": infer_topic(named_entities),
        "FMT": infer_format(doc_path),
        "EXP": infer_expertise_level(concept_depth),
    }

    facet_str = ":".join(f"{k}:{v}" for k, v in facets.items())
    return FacetedClassification(f"{main_class}:{facet_str}")
