"""Exhibition Curator — Selective doc surfacing."""

from __future__ import annotations

from typing import Any

from curator.utils import vectorize, cosine_similarity, adapt_summary


class Exhibition:
    """
    A curated selection of documents for a specific audience and context.
    """

    def __init__(
        self,
        name: str,
        theme: str,
        audience_profile: dict[str, str],
        max_items: int = 20,
    ) -> None:
        self.name = name
        self.theme = theme
        self.audience = audience_profile
        self.max_items = max_items
        self.selection: list[Any] = []

    def curate(self, collection: list[Any]) -> Exhibition:
        """
        Selects documents for exhibition using curatorial scoring.
        """
        scored = []
        for doc in collection:
            relevance = self._theme_relevance(doc)
            condition = doc.conservation_report.condition_index()
            diversity = self._diversity_bonus(doc)
            crowd = self._crowd_penalty(doc)

            score = (relevance * condition * diversity) / (crowd + 1e-6)
            scored.append((score, doc))

        scored.sort(reverse=True, key=lambda x: x[0])
        self.selection = self._diverse_select(scored, self.max_items)
        return self

    def _theme_relevance(self, doc: Any) -> float:
        """Calculates semantic relevance to exhibition theme."""
        theme_vec = vectorize(self.theme)
        doc_vec = vectorize(doc.content_summary)
        return cosine_similarity(theme_vec, doc_vec)

    def _diversity_bonus(self, doc: Any) -> float:
        """Rewards documents that expand facet coverage."""
        doc_facets = set(doc.classification.facets.values())
        selected_facets: set[str] = set()
        for selected in self.selection:
            selected_facets.update(selected.classification.facets.values())

        new_facets = doc_facets - selected_facets
        return 1.0 + (0.2 * len(new_facets))

    def _crowd_penalty(self, doc: Any) -> float:
        """Penalizes overrepresented hierarchy branches."""
        branch = doc.classification.hierarchy.split(".")[0]
        branch_count = sum(
            1 for s in self.selection
            if s.classification.hierarchy.split(".")[0] == branch
        )
        return 1.0 + (0.3 * branch_count)

    def _diverse_select(self, scored: list[tuple[float, Any]], max_items: int) -> list[Any]:
        """Greedy selection with diversity constraint."""
        selected = []
        for score, doc in scored:
            if len(selected) >= max_items:
                break
            branch = doc.classification.hierarchy.split(".")[0]
            branch_count = sum(
                1 for s in selected
                if s.classification.hierarchy.split(".")[0] == branch
            )
            if branch_count < 3:
                selected.append(doc)
        return selected

    def didactic_label(self, doc: Any) -> str:
        """
        Generates audience-adapted summary (didactic label).
        """
        base_summary = doc.content_summary
        level = self.audience.get("level", "general")
        if level == "beginner":
            max_len = 80
        elif level == "expert":
            max_len = 200
        else:
            max_len = 120

        return adapt_summary(base_summary, max_len)

    def generate_rotation_schedule(self, collection: list[Any], period_days: int = 30) -> list[dict[str, Any]]:
        """
        Plans exhibit rotations to keep content fresh while
        maintaining narrative coherence.
        """
        schedule = []
        for period in range(4):
            retain_count = int(self.max_items * 0.7)
            rotate_count = self.max_items - retain_count

            retained = self.selection[:retain_count]
            retained_paths = {id(d) for d in retained}
            candidates = [d for d in collection if id(d) not in retained_paths]
            new_items = sorted(
                candidates,
                key=lambda d: d.conservation_report.condition_index(),
            )[:rotate_count]

            schedule.append({
                "period": period,
                "retained": retained,
                "rotated_in": new_items,
                "theme_shift": self._detect_theme_shift(retained + new_items),
            })

        return schedule

    def _detect_theme_shift(self, docs: list[Any]) -> float:
        """Detects how much the theme shifts with the given docs."""
        if not docs:
            return 0.0
        theme_vec = vectorize(self.theme)
        scores = [cosine_similarity(theme_vec, vectorize(d.content_summary)) for d in docs]
        return sum(scores) / len(scores) if scores else 0.0
