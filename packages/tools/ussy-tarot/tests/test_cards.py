try:
    from conftest import create_fixture_dir, create_incidents_file
except ImportError:
    from .conftest import create_fixture_dir, create_incidents_file

"""Tests for tarot.cards module."""

import os
import tempfile
import pytest

from ussy_tarot.cards import (
    Outcome,
    CascadeRule,
    InteractionRule,
    InteractionType,
    Confidence,
    DecisionCard,
    CardRegistry,
    parse_frontmatter,
    _parse_simple_yaml,
    _parse_outcomes,
    _parse_cascades,
    _parse_interactions,
    load_card_from_markdown,
)


class TestOutcome:
    def test_creation(self):
        o = Outcome(name="Test", probability=0.5)
        assert o.name == "Test"
        assert o.probability == 0.5

    def test_probability_clamped_high(self):
        o = Outcome(name="Test", probability=1.5)
        assert o.probability == 1.0

    def test_probability_clamped_low(self):
        o = Outcome(name="Test", probability=-0.5)
        assert o.probability == 0.0

    def test_probability_boundary_values(self):
        o0 = Outcome(name="Zero", probability=0.0)
        assert o0.probability == 0.0
        o1 = Outcome(name="One", probability=1.0)
        assert o1.probability == 1.0


class TestCascadeRule:
    def test_creation(self):
        c = CascadeRule(target_adr="ADR-002", description="Redis needed", trigger_probability=0.6)
        assert c.target_adr == "ADR-002"
        assert c.trigger_probability == 0.6

    def test_probability_clamped(self):
        c = CascadeRule(target_adr="X", description="", trigger_probability=2.0)
        assert c.trigger_probability == 1.0

    def test_probability_clamped_negative(self):
        c = CascadeRule(target_adr="X", description="", trigger_probability=-1.0)
        assert c.trigger_probability == 0.0


class TestInteractionRule:
    def test_amplify(self):
        i = InteractionRule(other_adr="ADR-002", interaction_type=InteractionType.AMPLIFY, strength=1.5)
        assert i.interaction_type == InteractionType.AMPLIFY
        assert i.strength == 1.5

    def test_mitigate(self):
        i = InteractionRule(other_adr="ADR-003", interaction_type=InteractionType.MITIGATE, strength=2.0)
        assert i.interaction_type == InteractionType.MITIGATE
        assert i.strength == 2.0

    def test_default_strength(self):
        i = InteractionRule(other_adr="X", interaction_type=InteractionType.AMPLIFY)
        assert i.strength == 1.0

    def test_strength_clamped_high(self):
        i = InteractionRule(other_adr="X", interaction_type=InteractionType.AMPLIFY, strength=5.0)
        assert i.strength == 3.0

    def test_strength_clamped_low(self):
        i = InteractionRule(other_adr="X", interaction_type=InteractionType.AMPLIFY, strength=-1.0)
        assert i.strength == 0.0


class TestDecisionCard:
    def test_basic_creation(self):
        card = DecisionCard(adr_id="ADR-001", title="Test decision")
        assert card.adr_id == "ADR-001"
        assert card.title == "Test decision"
        assert card.outcomes == []
        assert card.cascades == []
        assert card.confidence == Confidence.MEDIUM

    def test_auto_stability_tier(self):
        card = DecisionCard(
            adr_id="ADR-001",
            title="Risky",
            outcomes=[
                Outcome(name="Bad outcome", probability=0.8),
                Outcome(name="No issues", probability=0.2),
            ],
        )
        assert card.stability_tier == "critical"

    def test_stability_tier_unstable(self):
        card = DecisionCard(
            adr_id="ADR-002",
            title="Unstable",
            outcomes=[
                Outcome(name="Bad", probability=0.5),
                Outcome(name="No issues", probability=0.5),
            ],
        )
        assert card.stability_tier == "unstable"

    def test_stability_tier_moderate(self):
        card = DecisionCard(
            adr_id="ADR-003",
            title="Moderate",
            outcomes=[
                Outcome(name="Bad", probability=0.3),
                Outcome(name="No issues", probability=0.7),
            ],
        )
        assert card.stability_tier == "moderate"

    def test_stability_tier_stable(self):
        card = DecisionCard(
            adr_id="ADR-004",
            title="Stable",
            outcomes=[
                Outcome(name="Bad", probability=0.1),
                Outcome(name="No issues", probability=0.9),
            ],
        )
        assert card.stability_tier == "stable"

    def test_stability_tier_no_outcomes(self):
        card = DecisionCard(adr_id="ADR-005", title="Empty")
        assert card.stability_tier == "unknown"

    def test_risk_probability(self):
        card = DecisionCard(
            adr_id="ADR-001",
            title="Test",
            outcomes=[
                Outcome(name="Bad", probability=0.4),
                Outcome(name="No issues", probability=0.6),
            ],
        )
        assert card.risk_probability == pytest.approx(0.4, abs=0.05)

    def test_risk_probability_no_outcomes(self):
        card = DecisionCard(adr_id="ADR-001", title="Empty")
        assert card.risk_probability == 0.0

    def test_normalize_outcomes(self):
        card = DecisionCard(
            adr_id="ADR-001",
            title="Test",
            outcomes=[
                Outcome(name="A", probability=30.0),
                Outcome(name="B", probability=70.0),
            ],
        )
        total = sum(o.probability for o in card.outcomes)
        assert total == pytest.approx(1.0, abs=0.01)

    def test_sample_outcome(self):
        card = DecisionCard(
            adr_id="ADR-001",
            title="Test",
            outcomes=[
                Outcome(name="A", probability=0.5),
                Outcome(name="B", probability=0.5),
            ],
        )
        import random
        rng = random.Random(42)
        outcome = card.sample_outcome(rng)
        assert outcome is not None
        assert outcome.name in ("A", "B")

    def test_sample_outcome_empty(self):
        card = DecisionCard(adr_id="ADR-001", title="Empty")
        import random
        rng = random.Random(42)
        assert card.sample_outcome(rng) is None

    def test_auto_created_at(self):
        card = DecisionCard(adr_id="ADR-001", title="Test")
        assert card.created_at != ""

    def test_explicit_created_at(self):
        card = DecisionCard(adr_id="ADR-001", title="Test", created_at="2025-01-01T00:00:00+00:00")
        assert card.created_at == "2025-01-01T00:00:00+00:00"


class TestYAMLParsing:
    def test_parse_simple_yaml(self):
        text = "key: value\nlist:\n  - item1\n  - item2"
        result = _parse_simple_yaml(text)
        assert result["key"] == "value"
        assert result["list"] == ["item1", "item2"]

    def test_parse_frontmatter(self):
        text = "---\nadr_id: ADR-001\ntitle: Test\n---\nBody text"
        meta, body = parse_frontmatter(text)
        assert meta["adr_id"] == "ADR-001"
        assert meta["title"] == "Test"
        assert body == "Body text"

    def test_parse_frontmatter_no_frontmatter(self):
        text = "Just plain text"
        meta, body = parse_frontmatter(text)
        assert meta == {}
        assert body == "Just plain text"

    def test_parse_outcomes(self):
        raw = ["Schema rigidity:35%", "No issues:65%"]
        outcomes = _parse_outcomes(raw)
        assert len(outcomes) == 2
        assert outcomes[0].name == "Schema rigidity"
        assert outcomes[0].probability == pytest.approx(0.35, abs=0.01)

    def test_parse_cascades(self):
        raw = ["ADR-003:Redis cluster needed:60%"]
        cascades = _parse_cascades(raw)
        assert len(cascades) == 1
        assert cascades[0].target_adr == "ADR-003"
        assert cascades[0].trigger_probability == pytest.approx(0.6, abs=0.01)

    def test_parse_interactions(self):
        raw = ["ADR-002:AMPLIFY:1.5"]
        interactions = _parse_interactions(raw)
        assert len(interactions) == 1
        assert interactions[0].other_adr == "ADR-002"
        assert interactions[0].interaction_type == InteractionType.AMPLIFY
        assert interactions[0].strength == 1.5


class TestLoadCardFromMarkdown:
    def test_load_fixture_card(self):
        fixture_dir = create_fixture_dir()
        try:
            card = load_card_from_markdown(os.path.join(fixture_dir, "adr-001.md"))
            assert card.adr_id == "ADR-001"
            assert card.title == "PostgreSQL for session storage"
            assert card.confidence == Confidence.HIGH
            assert len(card.outcomes) == 2
            assert len(card.cascades) == 1
            assert len(card.interactions) == 1
        finally:
            import shutil
            shutil.rmtree(fixture_dir)

    def test_load_card_with_interactions(self):
        fixture_dir = create_fixture_dir()
        try:
            card = load_card_from_markdown(os.path.join(fixture_dir, "adr-002.md"))
            assert card.adr_id == "ADR-002"
            assert len(card.interactions) == 2
        finally:
            import shutil
            shutil.rmtree(fixture_dir)


class TestCardRegistry:
    def test_add_and_get_card(self):
        registry = CardRegistry()
        card = DecisionCard(adr_id="ADR-001", title="Test")
        registry.add_card(card)
        assert registry.get_card("ADR-001") is card
        assert registry.get_card("ADR-999") is None

    def test_remove_card(self):
        registry = CardRegistry()
        card = DecisionCard(adr_id="ADR-001", title="Test")
        registry.add_card(card)
        registry.remove_card("ADR-001")
        assert registry.get_card("ADR-001") is None

    def test_all_cards(self):
        registry = CardRegistry()
        registry.add_card(DecisionCard(adr_id="ADR-001", title="A"))
        registry.add_card(DecisionCard(adr_id="ADR-002", title="B"))
        assert len(registry.all_cards()) == 2

    def test_load_from_directory(self):
        fixture_dir = create_fixture_dir()
        try:
            registry = CardRegistry()
            registry.load_from_directory(fixture_dir)
            assert len(registry.all_cards()) == 5
            assert registry.get_card("ADR-001") is not None
            assert registry.get_card("ADR-005") is not None
        finally:
            import shutil
            shutil.rmtree(fixture_dir)

    def test_load_from_nonexistent_directory(self):
        registry = CardRegistry()
        registry.load_from_directory("/nonexistent/path")
        assert len(registry.all_cards()) == 0

    def test_get_interacting_cards(self):
        fixture_dir = create_fixture_dir()
        try:
            registry = CardRegistry()
            registry.load_from_directory(fixture_dir)
            interacting = registry.get_interacting_cards("ADR-001")
            assert len(interacting) >= 1
            # ADR-001 has an AMPLIFY interaction with ADR-002
            assert any(r[0].adr_id == "ADR-002" for r in interacting)
        finally:
            import shutil
            shutil.rmtree(fixture_dir)

    def test_get_cascade_targets(self):
        fixture_dir = create_fixture_dir()
        try:
            registry = CardRegistry()
            registry.load_from_directory(fixture_dir)
            targets = registry.get_cascade_targets("ADR-001")
            assert len(targets) >= 1
            # ADR-001 cascades to ADR-003
            assert any(t[0].adr_id == "ADR-003" for t in targets)
        finally:
            import shutil
            shutil.rmtree(fixture_dir)

    def test_get_orphaned_cards(self):
        registry = CardRegistry()
        # Card with no interactions and risk > 0
        registry.add_card(DecisionCard(
            adr_id="ADR-ORPHAN",
            title="Orphaned",
            outcomes=[Outcome(name="Bad", probability=0.5), Outcome(name="No issues", probability=0.5)],
        ))
        orphans = registry.get_orphaned_cards()
        assert len(orphans) == 1
        assert orphans[0].adr_id == "ADR-ORPHAN"

    def test_get_mitigators(self):
        registry = CardRegistry()
        registry.add_card(DecisionCard(
            adr_id="ADR-001",
            title="Risk",
            outcomes=[Outcome(name="Bad", probability=0.5), Outcome(name="No issues", probability=0.5)],
            interactions=[InteractionRule(other_adr="ADR-002", interaction_type=InteractionType.MITIGATE)],
        ))
        mitigators = registry.get_mitigators()
        assert len(mitigators) == 1
        assert mitigators[0][0].adr_id == "ADR-001"

    def test_save_card_to_markdown(self):
        registry = CardRegistry()
        card = DecisionCard(
            adr_id="ADR-099",
            title="Test save",
            outcomes=[Outcome(name="Risk", probability=0.3), Outcome(name="No issues", probability=0.7)],
            tags=["test"],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = registry.save_card_to_markdown(card, tmpdir)
            assert os.path.exists(filepath)
            # Verify round-trip
            loaded = load_card_from_markdown(filepath)
            assert loaded.adr_id == "ADR-099"
            assert loaded.title == "Test save"
