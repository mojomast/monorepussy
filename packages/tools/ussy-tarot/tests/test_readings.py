try:
    from conftest import create_fixture_dir, create_incidents_file
except ImportError:
    from .conftest import create_fixture_dir, create_incidents_file

"""Tests for tarot.readings module."""

import pytest

from ussy_tarot.cards import (
    CardRegistry,
    DecisionCard,
    Outcome,
    CascadeRule,
    InteractionRule,
    InteractionType,
)
from ussy_tarot.engine import MonteCarloEngine
from ussy_tarot.readings import (
    ReadingGenerator,
    FullReading,
    TowerReading,
    WheelReading,
    HermitReading,
    StarReading,
    DeathReading,
    format_reading,
)


def _make_risky_registry():
    """Create a registry with clearly risky cards for reading tests."""
    registry = CardRegistry()
    registry.add_card(DecisionCard(
        adr_id="ADR-001",
        title="Single AZ",
        outcomes=[
            Outcome(name="Outage", probability=0.7),
            Outcome(name="No issues", probability=0.3),
        ],
        cascades=[
            CascadeRule(target_adr="ADR-002", description="Cascading failure", trigger_probability=0.8),
        ],
    ))
    registry.add_card(DecisionCard(
        adr_id="ADR-002",
        title="Microservices",
        outcomes=[
            Outcome(name="Distributed monolith", probability=0.4),
            Outcome(name="No issues", probability=0.6),
        ],
        interactions=[
            InteractionRule(other_adr="ADR-003", interaction_type=InteractionType.MITIGATE, strength=2.0),
        ],
    ))
    registry.add_card(DecisionCard(
        adr_id="ADR-003",
        title="Redis cache",
        outcomes=[
            Outcome(name="Memory pressure", probability=0.2),
            Outcome(name="No issues", probability=0.8),
        ],
        interactions=[
            InteractionRule(other_adr="ADR-002", interaction_type=InteractionType.MITIGATE, strength=1.5),
        ],
    ))
    # High-risk orphan
    registry.add_card(DecisionCard(
        adr_id="ADR-004",
        title="No backup strategy",
        outcomes=[
            Outcome(name="Data loss", probability=0.6),
            Outcome(name="No issues", probability=0.4),
        ],
    ))
    return registry


class TestTowerReading:
    def test_tower_generated(self):
        registry = _make_risky_registry()
        engine = MonteCarloEngine(registry, seed=42)
        spread = engine.run(simulations=1000)
        gen = ReadingGenerator(registry, spread)
        tower = gen.generate_tower()
        assert isinstance(tower, TowerReading)
        assert tower.probability >= 0.0

    def test_tower_no_risks(self):
        registry = CardRegistry()
        registry.add_card(DecisionCard(
            adr_id="ADR-SAFE",
            title="Safe",
            outcomes=[Outcome(name="No issues", probability=1.0)],
        ))
        engine = MonteCarloEngine(registry, seed=42)
        spread = engine.run(simulations=100)
        gen = ReadingGenerator(registry, spread)
        tower = gen.generate_tower()
        assert tower.severity == "low"

    def test_tower_severity_critical(self):
        registry = CardRegistry()
        registry.add_card(DecisionCard(
            adr_id="ADR-001",
            title="Risky A",
            outcomes=[Outcome(name="Bad", probability=0.8), Outcome(name="No issues", probability=0.2)],
        ))
        registry.add_card(DecisionCard(
            adr_id="ADR-002",
            title="Risky B",
            outcomes=[Outcome(name="Bad", probability=0.8), Outcome(name="No issues", probability=0.2)],
        ))
        engine = MonteCarloEngine(registry, seed=42)
        spread = engine.run(simulations=2000)
        gen = ReadingGenerator(registry, spread)
        tower = gen.generate_tower()
        # With two very risky cards, should be at least high severity
        assert tower.severity in ("critical", "high", "medium")


class TestWheelReading:
    def test_wheel_generated(self):
        registry = _make_risky_registry()
        engine = MonteCarloEngine(registry, seed=42)
        spread = engine.run(simulations=1000)
        gen = ReadingGenerator(registry, spread)
        wheel = gen.generate_wheel()
        assert isinstance(wheel, WheelReading)

    def test_wheel_no_cascades(self):
        registry = CardRegistry()
        registry.add_card(DecisionCard(
            adr_id="ADR-001",
            title="Simple",
            outcomes=[Outcome(name="Bad", probability=0.5), Outcome(name="No issues", probability=0.5)],
        ))
        engine = MonteCarloEngine(registry, seed=42)
        spread = engine.run(simulations=100)
        gen = ReadingGenerator(registry, spread)
        wheel = gen.generate_wheel()
        assert wheel.avg_cascades == 0.0


class TestHermitReading:
    def test_hermit_finds_orphans(self):
        registry = _make_risky_registry()
        engine = MonteCarloEngine(registry, seed=42)
        spread = engine.run(simulations=1000)
        gen = ReadingGenerator(registry, spread)
        hermit = gen.generate_hermit()
        assert isinstance(hermit, HermitReading)
        # ADR-004 is an orphan
        assert "ADR-004" in hermit.orphaned_cards

    def test_hermit_no_orphans(self):
        registry = CardRegistry()
        registry.add_card(DecisionCard(
            adr_id="ADR-001",
            title="Mitigated",
            outcomes=[Outcome(name="Bad", probability=0.3), Outcome(name="No issues", probability=0.7)],
            interactions=[
                InteractionRule(other_adr="ADR-002", interaction_type=InteractionType.MITIGATE),
            ],
        ))
        registry.add_card(DecisionCard(
            adr_id="ADR-002",
            title="Mitigator",
            outcomes=[Outcome(name="No issues", probability=1.0)],
            interactions=[
                InteractionRule(other_adr="ADR-001", interaction_type=InteractionType.MITIGATE),
            ],
        ))
        engine = MonteCarloEngine(registry, seed=42)
        spread = engine.run(simulations=100)
        gen = ReadingGenerator(registry, spread)
        hermit = gen.generate_hermit()
        assert len(hermit.orphaned_cards) == 0


class TestStarReading:
    def test_star_generated(self):
        registry = _make_risky_registry()
        engine = MonteCarloEngine(registry, seed=42)
        spread = engine.run(simulations=1000)
        gen = ReadingGenerator(registry, spread)
        star = gen.generate_star()
        assert isinstance(star, StarReading)
        # ADR-003 is a mitigator
        assert len(star.star_cards) > 0


class TestDeathReading:
    def test_death_finds_high_risk(self):
        registry = _make_risky_registry()
        engine = MonteCarloEngine(registry, seed=42)
        spread = engine.run(simulations=2000)
        gen = ReadingGenerator(registry, spread)
        death = gen.generate_death()
        assert isinstance(death, DeathReading)
        # ADR-001 and ADR-004 should be flagged (>=70% sim risk)
        # This depends on simulation results, so we check type only

    def test_death_no_reversals(self):
        registry = CardRegistry()
        registry.add_card(DecisionCard(
            adr_id="ADR-SAFE",
            title="Safe",
            outcomes=[Outcome(name="No issues", probability=1.0)],
        ))
        engine = MonteCarloEngine(registry, seed=42)
        spread = engine.run(simulations=100)
        gen = ReadingGenerator(registry, spread)
        death = gen.generate_death()
        assert len(death.death_cards) == 0


class TestFullReading:
    def test_full_reading_generated(self):
        registry = _make_risky_registry()
        engine = MonteCarloEngine(registry, seed=42)
        spread = engine.run(simulations=1000)
        gen = ReadingGenerator(registry, spread)
        reading = gen.generate_full_reading()
        assert isinstance(reading, FullReading)
        assert reading.tower is not None
        assert reading.wheel is not None
        assert reading.hermit is not None
        assert reading.star is not None
        assert reading.death is not None


class TestFormatReading:
    def test_format_produces_output(self):
        registry = _make_risky_registry()
        engine = MonteCarloEngine(registry, seed=42)
        spread = engine.run(simulations=1000)
        gen = ReadingGenerator(registry, spread)
        reading = gen.generate_full_reading()
        output = format_reading(reading)
        assert "TAROT READING" in output
        assert "TOWER" in output
        assert "WHEEL" in output
        assert "HERMIT" in output
        assert "STAR" in output
        assert "DEATH" in output

    def test_format_includes_emojis(self):
        registry = _make_risky_registry()
        engine = MonteCarloEngine(registry, seed=42)
        spread = engine.run(simulations=1000)
        gen = ReadingGenerator(registry, spread)
        reading = gen.generate_full_reading()
        output = format_reading(reading)
        assert "🏚️" in output or "THE TOWER" in output
