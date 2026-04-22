"""Epigenetic State Tracker — tracks documentation state across generations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ussy_operon.models import Codebase, EpigeneticMark, MarkType, Operon


class EpigeneticStateTracker:
    """Tracks epigenetic marks on documentation: methylation, acetylation, chromatin remodeling."""

    ACETYLATION_WINDOW_DAYS = 30
    DEACETYLASE_RISK_DAYS = 25
    METHYLATION_ARCHIVAL_DAYS = 180

    def __init__(self) -> None:
        self.marks: list[EpigeneticMark] = []

    def _is_archived(self, operon: Operon, doc_history: list[dict[str, Any]]) -> bool:
        """Check if an operon is permanently archived (methylated)."""
        for entry in doc_history:
            if entry.get("operon_id") == operon.operon_id:
                if entry.get("action") == "archive":
                    archive_time = datetime.fromisoformat(entry.get("timestamp", "2000-01-01T00:00:00+00:00"))
                    if datetime.now(timezone.utc) - archive_time > timedelta(days=self.METHYLATION_ARCHIVAL_DAYS):
                        return True
        # Also archive if all genes are deprecated
        if operon.genes and all(g.is_deprecated for g in operon.genes):
            return True
        return False

    def _get_last_reviewed(self, operon: Operon, doc_history: list[dict[str, Any]]) -> datetime | None:
        """Get the last review timestamp for an operon."""
        reviews = [
            datetime.fromisoformat(entry.get("timestamp", "2000-01-01T00:00:00+00:00"))
            for entry in doc_history
            if entry.get("operon_id") == operon.operon_id and entry.get("action") == "review"
        ]
        return max(reviews) if reviews else None

    def _days_since(self, dt: datetime) -> int:
        """Calculate days since a datetime."""
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = now - dt
        return max(0, delta.days)

    def _calculate_acetylation_level(self, operon: Operon, doc_history: list[dict[str, Any]]) -> float:
        """Calculate acetylation level based on recent reviews and changes."""
        last_reviewed = self._get_last_reviewed(operon, doc_history)
        if not last_reviewed:
            return 0.0

        days = self._days_since(last_reviewed)
        if days > self.ACETYLATION_WINDOW_DAYS:
            return 0.0

        # Linear decay from 1.0 to 0.0 over the window
        level = 1.0 - (days / self.ACETYLATION_WINDOW_DAYS)

        # Boost for well-documented genes
        doc_ratio = sum(1 for g in operon.genes if g.docstring) / max(1, len(operon.genes))
        level = min(1.0, level + 0.2 * doc_ratio)

        return round(level, 3)

    def _has_structure_changed(self, operon: Operon, doc_history: list[dict[str, Any]]) -> bool:
        """Check if the operon's structure has changed recently."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        for entry in doc_history:
            if entry.get("operon_id") == operon.operon_id:
                if entry.get("action") in ("restructure", "gene_added", "gene_removed"):
                    entry_time = datetime.fromisoformat(entry.get("timestamp", "2000-01-01T00:00:00+00:00"))
                    if entry_time > cutoff:
                        return True
        return False

    def _predict_epigenetic_inheritance(
        self, marks: list[EpigeneticMark], commit_graph: list[dict[str, Any]]
    ) -> dict[str, list[str]]:
        """Predict how epigenetic marks will be inherited."""
        inheritance_map: dict[str, list[str]] = {}
        for mark in marks:
            if mark.operon_id not in inheritance_map:
                inheritance_map[mark.operon_id] = []

            if mark.mark_type == MarkType.METHYLATION:
                inheritance_map[mark.operon_id].append("stable_silencing")
            elif mark.mark_type == MarkType.ACETYLATION:
                inheritance_map[mark.operon_id].append("active_transcription")
                if mark.deacetylase_risk:
                    inheritance_map[mark.operon_id].append("risk_of_silencing")
            elif mark.mark_type == MarkType.CHROMATIN_REMODELING:
                inheritance_map[mark.operon_id].append("altered_accessibility")

        return inheritance_map

    def _suggest_interventions(self, marks: list[EpigeneticMark]) -> list[dict[str, Any]]:
        """Suggest epigenetic interventions based on current marks."""
        suggestions = []
        for mark in marks:
            if mark.mark_type == MarkType.METHYLATION:
                suggestions.append({
                    "operon_id": mark.operon_id,
                    "intervention": "review_archived_docs",
                    "reason": "Documentation is methylated (archived). Consider migration guide.",
                })
            elif mark.mark_type == MarkType.ACETYLATION and mark.deacetylase_risk:
                suggestions.append({
                    "operon_id": mark.operon_id,
                    "intervention": "refresh_review",
                    "reason": "Acetylation is at risk. Schedule a review to maintain active state.",
                })
            elif mark.mark_type == MarkType.CHROMATIN_REMODELING:
                suggestions.append({
                    "operon_id": mark.operon_id,
                    "intervention": "restructure_docs",
                    "reason": "Structure changed. Update documentation organization.",
                })
        return suggestions

    def track_epigenetic_state(
        self, doc_history: list[dict[str, Any]], codebase: Codebase
    ) -> dict[str, Any]:
        """Track epigenetic marks on documentation."""
        marks: list[EpigeneticMark] = []

        for operon in codebase.operons:
            # Check methylation (permanent suppression)
            if self._is_archived(operon, doc_history):
                marks.append(
                    EpigeneticMark(
                        mark_id=f"mark_meth_{operon.operon_id}",
                        operon_id=operon.operon_id,
                        mark_type=MarkType.METHYLATION,
                        position="promoter_region",
                        inheritance="stable",
                        effect="transcriptional_silencing",
                    )
                )

            # Check acetylation (active state)
            last_reviewed = self._get_last_reviewed(operon, doc_history)
            if last_reviewed and self._days_since(last_reviewed) < self.ACETYLATION_WINDOW_DAYS:
                acetyl_level = self._calculate_acetylation_level(operon, doc_history)
                marks.append(
                    EpigeneticMark(
                        mark_id=f"mark_acet_{operon.operon_id}",
                        operon_id=operon.operon_id,
                        mark_type=MarkType.ACETYLATION,
                        position="enhancer_regions",
                        inheritance="semi_stable",
                        effect="euchromatin_open",
                        level=acetyl_level,
                        deacetylase_risk=self._days_since(last_reviewed) > self.DEACETYLASE_RISK_DAYS,
                    )
                )

            # Check chromatin remodeling (structural changes)
            if self._has_structure_changed(operon, doc_history):
                marks.append(
                    EpigeneticMark(
                        mark_id=f"mark_chrom_{operon.operon_id}",
                        operon_id=operon.operon_id,
                        mark_type=MarkType.CHROMATIN_REMODELING,
                        position="gene_body",
                        inheritance="transient",
                        effect="altered_accessibility",
                        change="nucleosome_repositioning",
                    )
                )

        self.marks = marks

        # Predict state inheritance
        inheritance_map = self._predict_epigenetic_inheritance(marks, [])

        # Suggest interventions
        recommendations = self._suggest_interventions(marks)

        return {
            "current_marks": [m.to_dict() for m in marks],
            "inheritance_predictions": inheritance_map,
            "recommended_remarks": recommendations,
            "total_operons": len(codebase.operons),
            "marked_operons": len({m.operon_id for m in marks}),
        }

    def add_manual_mark(
        self,
        operon_id: str,
        mark_type: MarkType,
        position: str = "",
        effect: str = "",
        level: float = 0.0,
    ) -> EpigeneticMark:
        """Manually add an epigenetic mark."""
        mark = EpigeneticMark(
            mark_id=f"mark_manual_{operon_id}_{mark_type.value}",
            operon_id=operon_id,
            mark_type=mark_type,
            position=position,
            effect=effect,
            level=level,
        )
        self.marks.append(mark)
        return mark

    def get_marks_for_operon(self, operon_id: str) -> list[EpigeneticMark]:
        """Get all marks for a specific operon."""
        return [m for m in self.marks if m.operon_id == operon_id]

    def clear_marks_for_operon(self, operon_id: str) -> int:
        """Clear all marks for a specific operon."""
        original_len = len(self.marks)
        self.marks = [m for m in self.marks if m.operon_id != operon_id]
        return original_len - len(self.marks)
