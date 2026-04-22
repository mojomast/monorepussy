"""Tests for endemic.herd_immunity module."""

import pytest

from ussy_endemic.models import (
    HerdImmunityResult,
    Module,
    Pattern,
    PatternType,
    Compartment,
    VaccinationStrategy,
)
from ussy_endemic.herd_immunity import (
    calculate_combined_effort,
    calculate_herd_immunity,
    generate_vaccination_strategies,
    herd_immunity_threshold,
)


class TestHerdImmunityThreshold:
    def test_basic(self):
        # R0 = 3 -> HIT = 1 - 1/3 = 0.667
        hit = herd_immunity_threshold(3.0)
        assert hit == pytest.approx(0.667, rel=0.01)

    def test_r0_equals_2(self):
        # R0 = 2 -> HIT = 50%
        hit = herd_immunity_threshold(2.0)
        assert hit == 0.5

    def test_r0_below_1(self):
        # R0 < 1 -> No vaccination needed
        hit = herd_immunity_threshold(0.8)
        assert hit == 0.0

    def test_r0_equals_1(self):
        hit = herd_immunity_threshold(1.0)
        assert hit == 0.0

    def test_high_r0(self):
        # R0 = 10 -> HIT = 90%
        hit = herd_immunity_threshold(10.0)
        assert hit == pytest.approx(0.9)


class TestCalculateHerdImmunity:
    def test_basic(self):
        pattern = Pattern(name="bare-except", r0=3.2)
        result = calculate_herd_immunity(pattern, immune_modules=22, total_modules=47)
        assert result.threshold == pytest.approx(1 - 1/3.2, rel=0.01)
        assert result.modules_to_vaccinate > 0

    def test_already_immune(self):
        pattern = Pattern(name="test", r0=2.0)
        result = calculate_herd_immunity(pattern, immune_modules=40, total_modules=50)
        # 50% needed, 80% immune -> 0 to vaccinate
        assert result.modules_to_vaccinate == 0

    def test_zero_total(self):
        pattern = Pattern(name="test", r0=2.0)
        result = calculate_herd_immunity(pattern, immune_modules=0, total_modules=0)
        # Should not crash; uses total=1 as fallback
        assert isinstance(result, HerdImmunityResult)

    def test_low_r0(self):
        pattern = Pattern(name="test", r0=0.5)
        result = calculate_herd_immunity(pattern, immune_modules=0, total_modules=50)
        # R0 < 1 -> no vaccination needed
        assert result.modules_to_vaccinate == 0


class TestGenerateVaccinationStrategies:
    def test_with_superspreaders(self):
        pattern = Pattern(name="test", r0=3.0)
        result = calculate_herd_immunity(pattern, immune_modules=5, total_modules=50)
        ss_modules = [("src/utils/helpers.py", 9), ("src/api/routes.py", 5)]
        strategies = generate_vaccination_strategies(result, modules=[], superspreader_modules=ss_modules)
        assert len(strategies) >= 1
        assert strategies[0].target != ""

    def test_with_developers(self):
        pattern = Pattern(name="test", r0=3.0)
        result = calculate_herd_immunity(pattern, immune_modules=5, total_modules=50)
        dev_infections = {"alice@test.com": 5, "bob@test.com": 3}
        strategies = generate_vaccination_strategies(
            result, modules=[], developer_infections=dev_infections,
        )
        # Should include developer-related strategies
        dev_strategies = [s for s in strategies if "alice" in s.target.lower() or "bob" in s.target.lower()]
        assert len(dev_strategies) >= 1

    def test_empty_inputs(self):
        pattern = Pattern(name="test", r0=2.0)
        result = calculate_herd_immunity(pattern, immune_modules=0, total_modules=50)
        strategies = generate_vaccination_strategies(result, modules=[])
        assert isinstance(strategies, list)


class TestCalculateCombinedEffort:
    def test_basic(self):
        strategies = [
            VaccinationStrategy(target="a.py", action="Refactor", prevented_infections=5, effort_hours=2.0, rank=1),
            VaccinationStrategy(target="b.py", action="Refactor", prevented_infections=3, effort_hours=4.0, rank=2),
        ]
        result = calculate_combined_effort(strategies, total_infected=18)
        assert result["combined_hours"] == 6.0
        assert result["full_refactor_hours"] == 36.0
        assert result["savings"] == 30.0

    def test_empty_strategies(self):
        result = calculate_combined_effort([], total_infected=10)
        assert result["combined_hours"] == 0.0
        assert result["full_refactor_hours"] == 20.0
