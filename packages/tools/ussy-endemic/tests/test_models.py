"""Tests for endemic.models module."""

import pytest
from datetime import datetime, timezone

from ussy_endemic.models import (
    Compartment,
    DeveloperStats,
    HerdImmunityResult,
    Module,
    Pattern,
    PatternStatus,
    PatternType,
    PromoteResult,
    SIRSimulation,
    SIRState,
    TransmissionEvent,
    TransmissionTree,
    TransmissionVector,
    VaccinationStrategy,
    ZoonoticJump,
)


class TestPattern:
    def test_pattern_creation(self):
        p = Pattern(name="bare-except")
        assert p.name == "bare-except"
        assert p.pattern_type == PatternType.BAD
        assert p.r0 == 0.0

    def test_pattern_auto_id(self):
        p = Pattern(name="bare-except")
        assert p.id  # Non-empty auto-generated id

    def test_pattern_custom_id(self):
        p = Pattern(name="bare-except", id="custom123")
        assert p.id == "custom123"

    def test_prevalence_ratio(self):
        p = Pattern(name="test", prevalence_count=10, total_modules=50)
        assert p.prevalence_ratio == 0.2

    def test_prevalence_ratio_zero_total(self):
        p = Pattern(name="test", prevalence_count=5, total_modules=0)
        assert p.prevalence_ratio == 0.0

    def test_is_spreading(self):
        p = Pattern(name="test", r0=1.5)
        assert p.is_spreading is True

    def test_is_not_spreading(self):
        p = Pattern(name="test", r0=0.8)
        assert p.is_spreading is False

    def test_is_spreading_at_boundary(self):
        p = Pattern(name="test", r0=1.0)
        assert p.is_spreading is False


class TestModule:
    def test_module_creation(self):
        m = Module(path="src/utils/helpers.py")
        assert m.path == "src/utils/helpers.py"
        assert m.language == "python"
        assert m.compartment == Compartment.SUSCEPTIBLE

    def test_filename(self):
        m = Module(path="src/utils/helpers.py")
        assert m.filename == "helpers.py"

    def test_filename_no_dir(self):
        m = Module(path="helpers.py")
        assert m.filename == "helpers.py"

    def test_directory(self):
        m = Module(path="src/utils/helpers.py")
        assert m.directory == "src/utils"

    def test_directory_no_dir(self):
        m = Module(path="helpers.py")
        assert m.directory == ""


class TestTransmissionEvent:
    def test_event_creation(self):
        e = TransmissionEvent(
            pattern_name="bare-except",
            source_module="a.py",
            target_module="b.py",
            vector=TransmissionVector.COPY_PASTE,
            developer="dev@example.com",
        )
        assert e.pattern_name == "bare-except"
        assert e.vector == TransmissionVector.COPY_PASTE
        assert e.timestamp is not None  # Auto-generated

    def test_event_auto_timestamp(self):
        e = TransmissionEvent(
            pattern_name="test",
            source_module="a.py",
            target_module="b.py",
        )
        assert e.timestamp is not None
        assert e.timestamp.tzinfo is not None  # Should be timezone-aware


class TestTransmissionTree:
    def test_empty_tree(self):
        tree = TransmissionTree(pattern_name="test")
        assert len(tree.events) == 0
        assert len(tree.infected_modules) == 0

    def test_add_event(self):
        tree = TransmissionTree(pattern_name="test")
        event = TransmissionEvent(
            pattern_name="test",
            source_module="a.py",
            target_module="b.py",
        )
        tree.add_event(event)
        assert len(tree.events) == 1

    def test_infected_modules(self):
        tree = TransmissionTree(pattern_name="test")
        tree.add_event(TransmissionEvent(
            pattern_name="test", source_module="a.py", target_module="b.py"
        ))
        tree.add_event(TransmissionEvent(
            pattern_name="test", source_module="a.py", target_module="c.py"
        ))
        assert tree.infected_modules == {"a.py", "b.py", "c.py"}

    def test_vector_counts(self):
        tree = TransmissionTree(pattern_name="test")
        tree.add_event(TransmissionEvent(
            pattern_name="test", source_module="a.py", target_module="b.py",
            vector=TransmissionVector.COPY_PASTE,
        ))
        tree.add_event(TransmissionEvent(
            pattern_name="test", source_module="a.py", target_module="c.py",
            vector=TransmissionVector.DEVELOPER_HABIT,
        ))
        tree.add_event(TransmissionEvent(
            pattern_name="test", source_module="b.py", target_module="d.py",
            vector=TransmissionVector.COPY_PASTE,
        ))
        counts = tree.vector_counts
        assert counts[TransmissionVector.COPY_PASTE] == 2
        assert counts[TransmissionVector.DEVELOPER_HABIT] == 1


class TestSIRState:
    def test_total(self):
        state = SIRState(time=0, s=30, i=10, r=7)
        assert state.n == 47

    def test_zero_state(self):
        state = SIRState(time=0, s=0, i=0, r=0)
        assert state.n == 0


class TestSIRSimulation:
    def test_simulation_defaults(self):
        sim = SIRSimulation(
            pattern_name="test", r0=2.0, beta=0.2, gamma=0.1, n=50,
            states=[SIRState(time=0, s=45, i=5, r=0)],
        )
        assert sim.n == 50
        assert sim.peak_infected > 0

    def test_simulation_post_init(self):
        states = [
            SIRState(time=0, s=45, i=5, r=0),
            SIRState(time=1, s=40, i=8, r=2),
            SIRState(time=2, s=35, i=10, r=5),
        ]
        sim = SIRSimulation(
            pattern_name="test", r0=2.0, beta=0.2, gamma=0.1, n=50,
            states=states,
        )
        assert sim.peak_infected == 10
        assert sim.peak_time == 2


class TestHerdImmunityResult:
    def test_threshold_pct(self):
        r = HerdImmunityResult(
            pattern_name="test", r0=3.0,
            threshold=0.667,
            current_immune_count=10,
            total_modules=50,
        )
        assert r.threshold_pct == pytest.approx(66.7, rel=0.01)

    def test_current_immune_pct(self):
        r = HerdImmunityResult(
            pattern_name="test", r0=3.0,
            threshold=0.667,
            current_immune_count=10,
            total_modules=50,
        )
        assert r.current_immune_pct == 20.0

    def test_gap_pct(self):
        r = HerdImmunityResult(
            pattern_name="test", r0=3.0,
            threshold=0.667,
            current_immune_count=10,
            total_modules=50,
        )
        assert r.gap_pct == pytest.approx(46.7, rel=0.05)

    def test_zero_total(self):
        r = HerdImmunityResult(
            pattern_name="test", r0=3.0,
            threshold=0.667,
            current_immune_count=0,
            total_modules=0,
        )
        assert r.current_immune_pct == 0.0


class TestDeveloperStats:
    def test_infection_count(self):
        d = DeveloperStats(
            email="dev@test.com",
            modules_infected=["a.py", "b.py", "c.py"],
        )
        assert d.infection_count == 3

    def test_empty_infections(self):
        d = DeveloperStats(email="dev@test.com")
        assert d.infection_count == 0


class TestZoonoticJump:
    def test_jump_creation(self):
        j = ZoonoticJump(
            pattern_name="bare-except",
            origin_domain="web",
            target_domain="data",
            origin_module="web/api.py",
            target_module="data/pipeline.py",
            risk="HIGH",
        )
        assert j.risk == "HIGH"
        assert j.is_appropriate_in_origin is True


class TestVaccinationStrategy:
    def test_strategy_creation(self):
        s = VaccinationStrategy(
            target="helpers.py",
            action="Refactor",
            prevented_infections=5,
            effort_hours=2.0,
            rank=1,
        )
        assert s.prevented_infections == 5
