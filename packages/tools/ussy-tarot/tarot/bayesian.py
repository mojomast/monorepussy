"""Bayesian Updater for probability priors.

Updates priors from observed outcomes, community data, and expert estimates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from tarot.cards import CardRegistry, DecisionCard, Outcome


@dataclass
class OutcomeObservation:
    """Record of an observed outcome for a decision."""
    adr_id: str
    outcome_name: str
    observed_at: str = ""
    source: str = "local"  # local, community, expert


@dataclass
class BetaDistribution:
    """Beta distribution for Bayesian probability estimation.

    Beta(alpha, beta) where alpha = successes + 1, beta = failures + 1.
    For our purposes, alpha = positive observations + 1, beta = negative observations + 1.
    """
    alpha: float = 1.0
    beta: float = 1.0

    @property
    def mean(self) -> float:
        """Expected value (posterior mean)."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        """Variance of the distribution."""
        total = self.alpha + self.beta
        if total <= 1:
            return 0.0
        return (self.alpha * self.beta) / (total * total * (total + 1))

    @property
    def confidence(self) -> float:
        """Confidence increases with more observations."""
        total = self.alpha + self.beta
        return min(1.0, total / 20.0)  # Full confidence at 20+ observations

    def update(self, success: bool, weight: float = 1.0):
        """Update the distribution with a new observation."""
        if success:
            self.alpha += weight
        else:
            self.beta += weight


class BayesianUpdater:
    """Bayesian updater for decision card probabilities.

    Maintains Beta distributions for each outcome of each card
    and updates them based on observed data.
    """

    def __init__(self, registry: CardRegistry):
        self.registry = registry
        # {adr_id: {outcome_name: BetaDistribution}}
        self.posteriors: Dict[str, Dict[str, BetaDistribution]] = {}
        self.observations: List[OutcomeObservation] = []
        self._initialize_priors()

    def _initialize_priors(self):
        """Initialize Beta distribution priors from current card probabilities."""
        for card in self.registry.all_cards():
            self.posteriors[card.adr_id] = {}
            for outcome in card.outcomes:
                # Use the card's stated probability as a prior
                # Convert probability to pseudo-counts
                pseudo_total = 10.0  # Equivalent sample size for prior
                alpha = max(0.5, outcome.probability * pseudo_total)
                beta_val = max(0.5, (1.0 - outcome.probability) * pseudo_total)
                self.posteriors[card.adr_id][outcome.name] = BetaDistribution(
                    alpha=alpha, beta=beta_val
                )

    def observe_outcome(self, observation: OutcomeObservation):
        """Record an observed outcome and update posteriors."""
        self.observations.append(observation)
        if observation.adr_id not in self.posteriors:
            self.posteriors[observation.adr_id] = {}

        posteriors = self.posteriors[observation.adr_id]

        # Weight based on source
        weight = {"local": 1.0, "community": 0.5, "expert": 0.3}.get(
            observation.source, 0.3
        )

        for outcome_name, beta_dist in posteriors.items():
            if outcome_name == observation.outcome_name:
                beta_dist.update(True, weight)
            else:
                beta_dist.update(False, weight)

    def observe_community_data(
        self, adr_id: str, outcome_counts: Dict[str, int], total_orgs: int
    ):
        """Update from community database outcomes.

        Args:
            adr_id: The decision card ID
            outcome_counts: {outcome_name: count_of_orgs_with_this_outcome}
            total_orgs: Total number of organizations observed
        """
        if adr_id not in self.posteriors:
            self.posteriors[adr_id] = {}

        for outcome_name, count in outcome_counts.items():
            if outcome_name not in self.posteriors[adr_id]:
                self.posteriors[adr_id][outcome_name] = BetaDistribution()

            beta_dist = self.posteriors[adr_id][outcome_name]
            # Community data weighted less than local observations
            weight = 0.5 / max(1, total_orgs)
            for _ in range(count):
                beta_dist.update(True, weight)
            # Remaining orgs didn't have this outcome
            remaining = total_orgs - count
            for _ in range(remaining):
                beta_dist.update(False, weight)

    def calibrate_expert(
        self, adr_id: str, outcome_name: str,
        estimated_prob: float, overconfidence_factor: float = 0.5
    ):
        """Calibrate an expert estimate by adjusting for overconfidence.

        Overconfidence factor shrinks estimates toward 0.5 (uniform).
        """
        if adr_id not in self.posteriors:
            self.posteriors[adr_id] = {}
        if outcome_name not in self.posteriors[adr_id]:
            self.posteriors[adr_id][outcome_name] = BetaDistribution()

        # Calibrate: shrink toward 0.5
        calibrated = 0.5 + overconfidence_factor * (estimated_prob - 0.5)

        # Convert to pseudo-counts
        pseudo_total = 5.0  # Weaker prior for expert estimates
        alpha = max(0.5, calibrated * pseudo_total)
        beta_val = max(0.5, (1.0 - calibrated) * pseudo_total)

        # Mix with existing posterior
        existing = self.posteriors[adr_id][outcome_name]
        mix_weight = 0.3  # Expert gets 30% weight
        new_alpha = existing.alpha * (1 - mix_weight) + alpha * mix_weight
        new_beta = existing.beta * (1 - mix_weight) + beta_val * mix_weight
        self.posteriors[adr_id][outcome_name] = BetaDistribution(
            alpha=new_alpha, beta=new_beta
        )

    def get_updated_probabilities(self, adr_id: str) -> Dict[str, float]:
        """Get updated probabilities for all outcomes of a card."""
        if adr_id not in self.posteriors:
            return {}

        posteriors = self.posteriors[adr_id]
        raw_probs = {name: dist.mean for name, dist in posteriors.items()}

        # Normalize so probabilities sum to 1
        total = sum(raw_probs.values())
        if total > 0:
            return {name: prob / total for name, prob in raw_probs.items()}
        return raw_probs

    def apply_updates_to_registry(self):
        """Apply updated probabilities back to the registry cards."""
        for card in self.registry.all_cards():
            updated = self.get_updated_probabilities(card.adr_id)
            if not updated:
                continue
            for outcome in card.outcomes:
                if outcome.name in updated:
                    outcome.probability = updated[outcome.name]
            card._normalize_outcomes()
            card.stability_tier = card._compute_stability_tier()

    def accuracy_score(self) -> float:
        """Compute an accuracy score based on how well priors predicted outcomes.

        Uses log-likelihood of observed outcomes under the posterior.
        """
        if not self.observations:
            return 0.0

        total_log_likelihood = 0.0
        count = 0

        for obs in self.observations:
            if obs.adr_id in self.posteriors:
                posteriors = self.posteriors[obs.adr_id]
                if obs.outcome_name in posteriors:
                    prob = posteriors[obs.outcome_name].mean
                    # Avoid log(0)
                    prob = max(1e-10, min(1 - 1e-10, prob))
                    total_log_likelihood += math.log(prob)
                    count += 1

        if count == 0:
            return 0.0

        # Normalize to [0, 1] range
        avg_ll = total_log_likelihood / count
        # Log-likelihood for a random guess (1/n outcomes)
        n_outcomes = max(2, count)
        random_ll = math.log(1.0 / n_outcomes)
        # Scale: 0 = random, 1 = perfect
        if random_ll == 0:
            return 0.0
        return max(0.0, min(1.0, avg_ll / random_ll))
