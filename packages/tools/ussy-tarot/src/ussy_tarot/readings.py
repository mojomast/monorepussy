"""Readings — Tarot-inspired risk analysis outputs.

Generates the five key readings:
- The Tower: Highest-severity risk cluster
- The Wheel: Decisions most likely to cascade
- The Hermit: Orphaned decisions with no mitigations
- The Star: Decisions that reduce overall risk
- Death: Decisions that should be reversed
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ussy_tarot.cards import CardRegistry, DecisionCard
from ussy_tarot.engine import MonteCarloEngine, SpreadResult


@dataclass
class TowerReading:
    """The Tower: Highest-severity risk cluster."""
    description: str
    involved_cards: List[str]
    probability: float
    severity: str  # critical, high, medium, low


@dataclass
class WheelReading:
    """The Wheel: Decisions most likely to cascade."""
    description: str
    source_card: str
    avg_cascades: float
    likely_targets: List[str]


@dataclass
class HermitReading:
    """The Hermit: Orphaned decisions with no mitigations."""
    description: str
    orphaned_cards: List[str]
    highest_risk: str
    risk_probability: float


@dataclass
class StarReading:
    """The Star: Decisions that reduce overall risk."""
    description: str
    star_cards: List[str]
    mitigated_count: int
    risk_reduction_pct: float


@dataclass
class DeathReading:
    """Death: Decisions that should be reversed."""
    description: str
    death_cards: List[str]
    blocking_probability: float


@dataclass
class FullReading:
    """Complete tarot reading with all five card positions."""
    tower: Optional[TowerReading] = None
    wheel: Optional[WheelReading] = None
    hermit: Optional[HermitReading] = None
    star: Optional[StarReading] = None
    death: Optional[DeathReading] = None


class ReadingGenerator:
    """Generates tarot-inspired risk readings from simulation results."""

    def __init__(self, registry: CardRegistry, spread: SpreadResult):
        self.registry = registry
        self.spread = spread

    def generate_tower(self) -> Optional[TowerReading]:
        """Generate The Tower reading: highest-severity risk cluster.

        Finds the pair of decisions with the highest co-occurrence
        of negative outcomes.
        """
        if not self.spread.co_occurrences:
            return TowerReading(
                description="No significant risk clusters detected.",
                involved_cards=[],
                probability=0.0,
                severity="low",
            )

        # Find the most dangerous co-occurrence
        max_co = max(self.spread.co_occurrences.values())
        if max_co == 0:
            return TowerReading(
                description="No significant risk clusters detected.",
                involved_cards=[],
                probability=0.0,
                severity="low",
            )

        # Find the pair(s) with max co-occurrence
        worst_pairs = [
            pair for pair, count in self.spread.co_occurrences.items()
            if count == max_co
        ]
        worst_pair = worst_pairs[0]
        prob = self.spread.co_occurrence_probability(worst_pair[0], worst_pair[1])

        # Determine severity
        if prob >= 0.6:
            severity = "critical"
        elif prob >= 0.4:
            severity = "high"
        elif prob >= 0.2:
            severity = "medium"
        else:
            severity = "low"

        # Build description
        card_names = []
        for adr_id in worst_pair:
            card = self.registry.get_card(adr_id)
            if card:
                card_names.append(f"{adr_id} ({card.title})")
            else:
                card_names.append(adr_id)

        description = (
            f"Risk cluster: {' and '.join(card_names)} — "
            f"{prob:.0%} chance of concurrent negative outcomes"
        )

        return TowerReading(
            description=description,
            involved_cards=list(worst_pair),
            probability=prob,
            severity=severity,
        )

    def generate_wheel(self) -> Optional[WheelReading]:
        """Generate The Wheel reading: decisions most likely to cascade.

        Finds the card that triggers the most cascading decisions.
        """
        if not self.spread.card_cascade_counts:
            return WheelReading(
                description="No significant cascade patterns detected.",
                source_card="",
                avg_cascades=0.0,
                likely_targets=[],
            )

        # Find the card with the most cascades
        max_cascades_adr = max(
            self.spread.card_cascade_counts,
            key=self.spread.card_cascade_counts.get,
        )
        cascade_count = self.spread.card_cascade_counts[max_cascades_adr]
        avg_cascades = cascade_count / max(1, self.spread.simulations)

        # Find cascade targets
        card = self.registry.get_card(max_cascades_adr)
        targets = []
        if card:
            for cascade in card.cascades:
                targets.append(
                    f"{cascade.target_adr} ({cascade.description})"
                )

        card_name = f"{max_cascades_adr}"
        if card:
            card_name = f"{max_cascades_adr} ({card.title})"

        description = (
            f"{card_name} will cascade to {avg_cascades:.1f} new decisions "
            f"on average per simulation run"
        )

        return WheelReading(
            description=description,
            source_card=max_cascades_adr,
            avg_cascades=avg_cascades,
            likely_targets=targets,
        )

    def generate_hermit(self) -> Optional[HermitReading]:
        """Generate The Hermit reading: orphaned decisions with no mitigations.

        Finds cards with high risk but no mitigation interactions.
        """
        orphans = self.registry.get_orphaned_cards()

        if not orphans:
            return HermitReading(
                description="All decisions have some mitigation coverage.",
                orphaned_cards=[],
                highest_risk="",
                risk_probability=0.0,
            )

        # Find the highest-risk orphan
        highest_risk_orphan = max(orphans, key=lambda c: c.risk_probability)
        sim_prob = self.spread.card_negative_probability(highest_risk_orphan.adr_id)

        orphan_names = [
            f"{c.adr_id} ({c.title})" for c in orphans
        ]

        description = (
            f"{len(orphans)} orphaned decision(s) with no mitigations. "
            f"Highest risk: {highest_risk_orphan.adr_id} "
            f"({highest_risk_orphan.title}) at {sim_prob:.0%} probability"
        )

        return HermitReading(
            description=description,
            orphaned_cards=[c.adr_id for c in orphans],
            highest_risk=highest_risk_orphan.adr_id,
            risk_probability=sim_prob,
        )

    def generate_star(self) -> Optional[StarReading]:
        """Generate The Star reading: decisions that reduce overall risk.

        Finds cards that mitigate the most other risks.
        """
        mitigators = self.registry.get_mitigators()

        if not mitigators:
            return StarReading(
                description="No decisions currently mitigate other risks.",
                star_cards=[],
                mitigated_count=0,
                risk_reduction_pct=0.0,
            )

        top_mitigator, count = mitigators[0]

        # Estimate risk reduction by computing how much overall risk
        # would increase if this card's mitigations were removed
        total_risk = sum(
            self.spread.card_negative_probability(c.adr_id)
            for c in self.registry.all_cards()
        )
        # Rough estimate: each mitigation reduces risk by ~10-20%
        risk_reduction = min(100.0, count * 15.0)

        description = (
            f"{top_mitigator.adr_id} ({top_mitigator.title}) mitigates "
            f"{count} other risk(s). Strengthening it could reduce "
            f"overall risk by ~{risk_reduction:.0f}%"
        )

        return StarReading(
            description=description,
            star_cards=[f"{c.adr_id} ({c.title})" for c, _ in mitigators],
            mitigated_count=count,
            risk_reduction_pct=risk_reduction,
        )

    def generate_death(self) -> Optional[DeathReading]:
        """Generate Death reading: decisions that should be reversed.

        Finds cards with very high risk probability that are likely
        blocking future work.
        """
        death_cards = []
        for card in self.registry.all_cards():
            sim_prob = self.spread.card_negative_probability(card.adr_id)
            if sim_prob >= 0.7:
                death_cards.append((card, sim_prob))

        if not death_cards:
            return DeathReading(
                description="No decisions currently warrant reversal.",
                death_cards=[],
                blocking_probability=0.0,
            )

        # Sort by probability
        death_cards.sort(key=lambda x: x[1], reverse=True)
        worst_card, worst_prob = death_cards[0]

        card_names = [
            f"{c.adr_id} ({c.title}) at {p:.0%}"
            for c, p in death_cards
        ]

        description = (
            f"{len(death_cards)} decision(s) should be considered for reversal. "
            f"Highest: {worst_card.adr_id} ({worst_card.title}) at "
            f"{worst_prob:.0%} probability of negative outcomes"
        )

        return DeathReading(
            description=description,
            death_cards=[f"{c.adr_id}" for c, _ in death_cards],
            blocking_probability=worst_prob,
        )

    def generate_full_reading(self) -> FullReading:
        """Generate the complete five-card reading."""
        return FullReading(
            tower=self.generate_tower(),
            wheel=self.generate_wheel(),
            hermit=self.generate_hermit(),
            star=self.generate_star(),
            death=self.generate_death(),
        )


def format_reading(reading: FullReading) -> str:
    """Format a full reading as a human-readable string."""
    lines = []
    lines.append("=" * 60)
    lines.append("  TAROT READING — Architecture Risk Divination")
    lines.append("=" * 60)

    if reading.tower:
        lines.append("")
        lines.append("🏚️  THE TOWER — Highest-Severity Risk Cluster")
        lines.append(f"   {reading.tower.description}")
        if reading.tower.involved_cards:
            lines.append(f"   Severity: {reading.tower.severity.upper()}")
            lines.append(f"   Probability: {reading.tower.probability:.0%}")

    if reading.wheel:
        lines.append("")
        lines.append("🎡  THE WHEEL — Cascade Patterns")
        lines.append(f"   {reading.wheel.description}")
        if reading.wheel.likely_targets:
            for target in reading.wheel.likely_targets:
                lines.append(f"   → {target}")

    if reading.hermit:
        lines.append("")
        lines.append("🧙  THE HERMIT — Orphaned Decisions")
        lines.append(f"   {reading.hermit.description}")
        if reading.hermit.orphaned_cards:
            for card_id in reading.hermit.orphaned_cards:
                lines.append(f"   ⚠ {card_id}")

    if reading.star:
        lines.append("")
        lines.append("⭐  THE STAR — Risk Reducers")
        lines.append(f"   {reading.star.description}")
        if reading.star.star_cards:
            for card in reading.star.star_cards:
                lines.append(f"   ✦ {card}")

    if reading.death:
        lines.append("")
        lines.append("💀  DEATH — Decisions to Reverse")
        lines.append(f"   {reading.death.description}")
        if reading.death.death_cards:
            for card_id in reading.death.death_cards:
                lines.append(f"   ✗ {card_id}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
