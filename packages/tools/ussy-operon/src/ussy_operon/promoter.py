"""Promoter Detector — analyzes documentation generation triggers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ussy_operon.models import Codebase, Operon, Promoter


class PromoterDetector:
    """Analyzes triggers that should initiate documentation generation."""

    TRIGGER_DEFINITIONS: dict[str, dict[str, Any]] = {
        "public_api_change": {
            "strength": 1.0,
            "rnap_binding": ["signature_change", "new_export"],
        },
        "behavior_change": {
            "strength": 0.8,
            "rnap_binding": ["logic_change", "side_effect_added"],
        },
        "dependency_update": {
            "strength": 0.5,
            "rnap_binding": ["semver_minor", "new_capability"],
        },
        "comment_update": {
            "strength": 0.1,
            "rnap_binding": ["docstring_edit"],
        },
        "refactor": {
            "strength": 0.3,
            "rnap_binding": ["internal_restructure"],
        },
        "test_addition": {
            "strength": 0.4,
            "rnap_binding": ["new_test_file", "test_coverage_increase"],
        },
    }

    def __init__(self) -> None:
        self.triggers: dict[str, Promoter] = {}

    def _calculate_doc_urgency(self, change_type: str, history: list[dict[str, Any]]) -> float:
        """Calculate documentation urgency based on change history."""
        if not history:
            return 0.5

        # Count recent changes of this type
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent_changes = [h for h in history if datetime.fromisoformat(h.get("timestamp", "2000-01-01")) > cutoff and h.get("type") == change_type]

        urgency = min(1.0, 0.3 + 0.1 * len(recent_changes))
        return round(urgency, 3)

    def _find_specialized_triggers(self, operon: Operon) -> list[str]:
        """Find sigma factors (specialized triggers) for an operon."""
        triggers = []
        if operon.polycistronic:
            triggers.append("large_operon_change")
        if any(g.is_deprecated for g in operon.genes):
            triggers.append("deprecated_feature")
        if any(g.is_internal for g in operon.genes):
            triggers.append("internal_api")
        if any(g.exports for g in operon.genes):
            triggers.append("public_api_present")
        return triggers

    def _find_prerequisites(self, operon: Operon) -> list[str]:
        """Find upstream activators (prerequisites) for an operon."""
        prereqs = []
        if operon.regulatory_proteins:
            prereqs.append("dependencies_documented")
        if any(g.docstring for g in operon.genes):
            prereqs.append("has_documentation")
        if operon.coupling_score > 0.8:
            prereqs.append("high_coupling")
        return prereqs

    def analyze_promoters(self, codebase: Codebase, history: list[dict[str, Any]] | None = None) -> dict[str, Promoter]:
        """Analyze triggers for documentation generation."""
        if history is None:
            history = []

        triggers: dict[str, Promoter] = {}

        for trigger_type, definition in self.TRIGGER_DEFINITIONS.items():
            transcription_rate = self._calculate_doc_urgency(trigger_type, history)
            promoter = Promoter(
                promoter_id=f"prom_{trigger_type}",
                trigger_type=trigger_type,
                strength=definition["strength"],
                rnap_binding=definition["rnap_binding"],
                transcription_rate=transcription_rate,
                target_operon="global",
            )
            triggers[trigger_type] = promoter

        # Add operon-specific promoters
        for operon in codebase.operons:
            sigma_factors = self._find_specialized_triggers(operon)
            upstream_activators = self._find_prerequisites(operon)

            operon_promoter = Promoter(
                promoter_id=f"prom_{operon.operon_id}",
                trigger_type="operon_specific",
                strength=operon.coupling_score,
                rnap_binding=sigma_factors,
                transcription_rate=self._calculate_doc_urgency("operon", history),
                target_operon=operon.operon_id,
                sigma_factor=sigma_factors,
                upstream_activators=upstream_activators,
            )
            triggers[operon.operon_id] = operon_promoter

        self.triggers = triggers
        return triggers

    def get_promoter_strength(self, trigger_type: str) -> float:
        """Get the strength of a specific trigger type."""
        if trigger_type in self.triggers:
            return self.triggers[trigger_type].strength
        return 0.0

    def should_generate(self, change_type: str, min_strength: float = 0.5) -> bool:
        """Determine if documentation should be generated for a change type."""
        return self.get_promoter_strength(change_type) >= min_strength

    def get_priority_order(self) -> list[tuple[str, float]]:
        """Get promoters sorted by priority (strength)."""
        sorted_promoters = sorted(
            self.triggers.items(),
            key=lambda x: x[1].strength,
            reverse=True
        )
        return [(pid, p.strength) for pid, p in sorted_promoters]
