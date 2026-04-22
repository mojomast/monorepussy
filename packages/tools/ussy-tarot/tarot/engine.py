"""Monte Carlo Simulation Engine.

Runs probabilistic simulations across all active decisions,
propagating cascades and interactions.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from tarot.cards import (
    CardRegistry,
    CascadeRule,
    DecisionCard,
    InteractionType,
    Outcome,
)


@dataclass
class SimulationResult:
    """Result of a single Monte Carlo simulation run."""
    triggered_outcomes: Dict[str, Outcome] = field(default_factory=dict)
    triggered_cascades: List[CascadeRule] = field(default_factory=list)
    total_risk_events: int = 0


@dataclass
class SpreadResult:
    """Aggregated result of all Monte Carlo simulations."""
    simulations: int = 0
    horizon_months: int = 24
    # Per-card outcome frequencies: {adr_id: {outcome_name: count}}
    outcome_frequencies: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # Per-card risk probability: {adr_id: risk_probability}
    card_risk_probabilities: Dict[str, float] = field(default_factory=dict)
    # Cascade trigger frequencies: {cascade_description: count}
    cascade_frequencies: Dict[str, int] = field(default_factory=dict)
    # Co-occurrence: {(adr1, adr2): count} where both had negative outcomes
    co_occurrences: Dict[Tuple[str, str], int] = field(default_factory=dict)
    # Per-card cascades triggered count
    card_cascade_counts: Dict[str, int] = field(default_factory=dict)
    # Risk events per sim
    risk_events_distribution: List[int] = field(default_factory=list)
    # All individual simulation results
    simulation_results: List[SimulationResult] = field(default_factory=list)

    @property
    def avg_risk_events(self) -> float:
        if not self.risk_events_distribution:
            return 0.0
        return sum(self.risk_events_distribution) / len(self.risk_events_distribution)

    def card_negative_probability(self, adr_id: str) -> float:
        """Probability that a card triggers a negative outcome."""
        freqs = self.outcome_frequencies.get(adr_id, {})
        if not freqs or self.simulations == 0:
            return 0.0
        negative_count = sum(
            count for name, count in freqs.items()
            if name.lower() != "no issues"
        )
        return negative_count / self.simulations

    def cascade_probability(self, cascade_desc: str) -> float:
        """Probability that a specific cascade fires."""
        if self.simulations == 0:
            return 0.0
        return self.cascade_frequencies.get(cascade_desc, 0) / self.simulations

    def co_occurrence_probability(self, adr1: str, adr2: str) -> float:
        """Probability that two cards both have negative outcomes."""
        if self.simulations == 0:
            return 0.0
        key = tuple(sorted([adr1, adr2]))
        return self.co_occurrences.get(key, 0) / self.simulations


class MonteCarloEngine:
    """Monte Carlo simulation engine for architecture risk analysis."""

    def __init__(self, registry: CardRegistry, seed: Optional[int] = None):
        self.registry = registry
        self.rng = random.Random(seed)

    def _apply_interactions(
        self, card: DecisionCard, base_prob: float
    ) -> float:
        """Modify a card's risk probability based on interactions with other cards."""
        modified = base_prob
        for interaction in card.interactions:
            other = self.registry.get_card(interaction.other_adr)
            if not other:
                continue
            other_risk = other.risk_probability
            if interaction.interaction_type == InteractionType.AMPLIFY:
                # Amplify: increase risk proportionally to other card's risk
                modified *= 1.0 + (interaction.strength - 1.0) * other_risk
            elif interaction.interaction_type == InteractionType.MITIGATE:
                # Mitigate: decrease risk proportionally to other card's presence
                modified *= 1.0 / interaction.strength
        return min(modified, 1.0)

    def _simulate_cascade_propagation(
        self,
        triggered: Dict[str, Outcome],
        cascades_fired: List[CascadeRule],
        visited: Optional[Set[str]] = None,
        depth: int = 0,
    ) -> None:
        """Recursively propagate cascades from triggered outcomes."""
        if depth > 5:  # Max cascade depth
            return
        if visited is None:
            visited = set()

        current_triggered = dict(triggered)  # snapshot
        for adr_id, outcome in current_triggered.items():
            if outcome.name.lower() == "no issues":
                continue
            if adr_id in visited:
                continue
            visited.add(adr_id)

            card = self.registry.get_card(adr_id)
            if not card:
                continue

            for cascade in card.cascades:
                if self.rng.random() < cascade.trigger_probability:
                    target = self.registry.get_card(cascade.target_adr)
                    if target:
                        target_outcome = target.sample_outcome(self.rng)
                        if target_outcome and target.adr_id not in triggered:
                            triggered[target.adr_id] = target_outcome
                            cascades_fired.append(cascade)
                            self._simulate_cascade_propagation(
                                triggered, cascades_fired, visited, depth + 1
                            )

    def run_single_simulation(self) -> SimulationResult:
        """Run a single Monte Carlo simulation."""
        triggered: Dict[str, Outcome] = {}
        cascades_fired: List[CascadeRule] = []

        # For each card, decide if a negative outcome triggers
        for card in self.registry.all_cards():
            base_risk = card.risk_probability
            modified_risk = self._apply_interactions(card, base_risk)

            if self.rng.random() < modified_risk:
                # Trigger a negative outcome
                negative_outcomes = [
                    o for o in card.outcomes if o.name.lower() != "no issues"
                ]
                if negative_outcomes:
                    # Weighted sample from negative outcomes
                    total = sum(o.probability for o in negative_outcomes)
                    if total > 0:
                        r = self.rng.random() * total
                        cumulative = 0.0
                        chosen = negative_outcomes[-1]
                        for o in negative_outcomes:
                            cumulative += o.probability
                            if r <= cumulative:
                                chosen = o
                                break
                        triggered[card.adr_id] = chosen
                    else:
                        triggered[card.adr_id] = negative_outcomes[0]
                else:
                    # Card has risk but no explicit negative outcomes
                    triggered[card.adr_id] = Outcome(name="Risk triggered", probability=1.0)

        # Propagate cascades
        self._simulate_cascade_propagation(triggered, cascades_fired)

        risk_events = sum(
            1 for o in triggered.values()
            if o.name.lower() != "no issues"
        )

        return SimulationResult(
            triggered_outcomes=triggered,
            triggered_cascades=cascades_fired,
            total_risk_events=risk_events,
        )

    def run(self, simulations: int = 10000, horizon_months: int = 24) -> SpreadResult:
        """Run the full Monte Carlo simulation."""
        result = SpreadResult(
            simulations=simulations,
            horizon_months=horizon_months,
        )

        for _ in range(simulations):
            sim = self.run_single_simulation()
            result.simulation_results.append(sim)
            result.risk_events_distribution.append(sim.total_risk_events)

            # Track outcome frequencies
            for adr_id, outcome in sim.triggered_outcomes.items():
                if adr_id not in result.outcome_frequencies:
                    result.outcome_frequencies[adr_id] = {}
                freqs = result.outcome_frequencies[adr_id]
                freqs[outcome.name] = freqs.get(outcome.name, 0) + 1

            # Track cascade frequencies
            for cascade in sim.triggered_cascades:
                key = f"{cascade.target_adr}:{cascade.description}"
                result.cascade_frequencies[key] = (
                    result.cascade_frequencies.get(key, 0) + 1
                )

                # Track per-card cascade counts
                source_cards = [
                    c for c in self.registry.all_cards()
                    if cascade in c.cascades
                ]
                for sc in source_cards:
                    result.card_cascade_counts[sc.adr_id] = (
                        result.card_cascade_counts.get(sc.adr_id, 0) + 1
                    )

            # Track co-occurrences of negative outcomes
            negative_adrs = [
                adr_id for adr_id, outcome in sim.triggered_outcomes.items()
                if outcome.name.lower() != "no issues"
            ]
            for i in range(len(negative_adrs)):
                for j in range(i + 1, len(negative_adrs)):
                    key = tuple(sorted([negative_adrs[i], negative_adrs[j]]))
                    result.co_occurrences[key] = (
                        result.co_occurrences.get(key, 0) + 1
                    )

        # Compute per-card risk probabilities
        for card in self.registry.all_cards():
            result.card_risk_probabilities[card.adr_id] = (
                result.card_negative_probability(card.adr_id)
            )

        return result
