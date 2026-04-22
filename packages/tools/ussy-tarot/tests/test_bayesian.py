try:
    from conftest import create_fixture_dir, create_incidents_file
except ImportError:
    from .conftest import create_fixture_dir, create_incidents_file

"""Tests for tarot.bayesian module."""

import pytest

from ussy_tarot.cards import (
    CardRegistry,
    DecisionCard,
    Outcome,
)
from ussy_tarot.bayesian import (
    BetaDistribution,
    BayesianUpdater,
    OutcomeObservation,
)


class TestBetaDistribution:
    def test_default_prior(self):
        bd = BetaDistribution()
        assert bd.alpha == 1.0
        assert bd.beta == 1.0
        assert bd.mean == pytest.approx(0.5, abs=0.01)

    def test_custom_params(self):
        bd = BetaDistribution(alpha=3.0, beta=1.0)
        assert bd.mean == pytest.approx(0.75, abs=0.01)

    def test_variance(self):
        bd = BetaDistribution(alpha=2.0, beta=2.0)
        assert bd.variance > 0

    def test_confidence_increases(self):
        bd = BetaDistribution(alpha=1.0, beta=1.0)
        c1 = bd.confidence
        bd.update(True)
        c2 = bd.confidence
        assert c2 > c1

    def test_update_success(self):
        bd = BetaDistribution(alpha=1.0, beta=1.0)
        bd.update(True)
        assert bd.alpha == 2.0
        assert bd.beta == 1.0

    def test_update_failure(self):
        bd = BetaDistribution(alpha=1.0, beta=1.0)
        bd.update(False)
        assert bd.alpha == 1.0
        assert bd.beta == 2.0

    def test_update_with_weight(self):
        bd = BetaDistribution(alpha=1.0, beta=1.0)
        bd.update(True, weight=2.0)
        assert bd.alpha == 3.0

    def test_confidence_maxes_out(self):
        bd = BetaDistribution(alpha=10.0, beta=10.0)
        assert bd.confidence == 1.0


class TestOutcomeObservation:
    def test_creation(self):
        obs = OutcomeObservation(adr_id="ADR-001", outcome_name="Bad")
        assert obs.adr_id == "ADR-001"
        assert obs.outcome_name == "Bad"
        assert obs.source == "local"

    def test_with_source(self):
        obs = OutcomeObservation(adr_id="ADR-001", outcome_name="Bad", source="community")
        assert obs.source == "community"


class TestBayesianUpdater:
    def _make_registry(self):
        registry = CardRegistry()
        registry.add_card(DecisionCard(
            adr_id="ADR-001",
            title="Test",
            outcomes=[
                Outcome(name="Bad", probability=0.3),
                Outcome(name="No issues", probability=0.7),
            ],
        ))
        return registry

    def test_initialize_priors(self):
        registry = self._make_registry()
        updater = BayesianUpdater(registry)
        assert "ADR-001" in updater.posteriors
        assert "Bad" in updater.posteriors["ADR-001"]
        assert "No issues" in updater.posteriors["ADR-001"]

    def test_observe_outcome(self):
        registry = self._make_registry()
        updater = BayesianUpdater(registry)
        obs = OutcomeObservation(adr_id="ADR-001", outcome_name="Bad", source="local")
        updater.observe_outcome(obs)
        assert len(updater.observations) == 1
        # "Bad" probability should increase
        probs = updater.get_updated_probabilities("ADR-001")
        assert probs["Bad"] > 0.3  # Should have shifted upward

    def test_observe_community_data(self):
        registry = self._make_registry()
        updater = BayesianUpdater(registry)
        updater.observe_community_data("ADR-001", {"Bad": 80, "No issues": 20}, total_orgs=100)
        probs = updater.get_updated_probabilities("ADR-001")
        # With community showing 80% bad outcomes, probability should increase
        assert probs["Bad"] > 0.3

    def test_calibrate_expert(self):
        registry = self._make_registry()
        updater = BayesianUpdater(registry)
        updater.calibrate_expert("ADR-001", "Bad", estimated_prob=0.9)
        probs = updater.get_updated_probabilities("ADR-001")
        # Expert says 90% bad, should shift upward (with overconfidence correction)
        assert probs["Bad"] > 0.3

    def test_get_updated_probabilities_normalize(self):
        registry = self._make_registry()
        updater = BayesianUpdater(registry)
        probs = updater.get_updated_probabilities("ADR-001")
        total = sum(probs.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_get_updated_probabilities_nonexistent(self):
        registry = self._make_registry()
        updater = BayesianUpdater(registry)
        probs = updater.get_updated_probabilities("ADR-999")
        assert probs == {}

    def test_apply_updates_to_registry(self):
        registry = self._make_registry()
        updater = BayesianUpdater(registry)
        # Observe lots of "Bad" outcomes
        for _ in range(10):
            updater.observe_outcome(
                OutcomeObservation(adr_id="ADR-001", outcome_name="Bad", source="local")
            )
        updater.apply_updates_to_registry()
        card = registry.get_card("ADR-001")
        # The risk should have increased
        assert card.risk_probability > 0.3

    def test_accuracy_score_no_observations(self):
        registry = self._make_registry()
        updater = BayesianUpdater(registry)
        assert updater.accuracy_score() == 0.0

    def test_accuracy_score_with_observations(self):
        registry = self._make_registry()
        updater = BayesianUpdater(registry)
        updater.observe_outcome(
            OutcomeObservation(adr_id="ADR-001", outcome_name="Bad", source="local")
        )
        score = updater.accuracy_score()
        assert 0.0 <= score <= 1.0
