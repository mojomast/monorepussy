"""Tests for endemic.promote module."""

import pytest

from endemic.models import Module, Pattern, PatternType, Compartment
from endemic.promote import (
    compute_cross_protection,
    find_optimal_seed,
    predict_r0_increase,
    promote_pattern,
)


class TestFindOptimalSeed:
    def test_basic(self):
        pattern = Pattern(name="structured-logging", pattern_type=PatternType.GOOD)
        modules = [
            Module(path="a.py", patterns=["bare-except"]),
            Module(path="b.py", patterns=["structured-logging"]),
            Module(path="c.py", patterns=[], developer_traffic=10, dependents=5),
        ]
        seed = find_optimal_seed(pattern, modules)
        assert seed == "c.py"  # Highest traffic, susceptible

    def test_all_infected(self):
        pattern = Pattern(name="structured-logging", pattern_type=PatternType.GOOD)
        modules = [
            Module(path="a.py", patterns=["structured-logging"], developer_traffic=5),
            Module(path="b.py", patterns=["structured-logging"], developer_traffic=10),
        ]
        seed = find_optimal_seed(pattern, modules)
        assert seed == "b.py"  # Highest traffic

    def test_empty_modules(self):
        pattern = Pattern(name="structured-logging", pattern_type=PatternType.GOOD)
        seed = find_optimal_seed(pattern, [])
        assert seed == ""


class TestPredictR0Increase:
    def test_basic(self):
        pattern = Pattern(name="structured-logging", pattern_type=PatternType.GOOD, r0=2.0)
        modules = [
            Module(path="a.py", patterns=["structured-logging"]),
            Module(path="b.py", patterns=[], developer_traffic=5, dependents=3),
        ]
        increase = predict_r0_increase(pattern, "b.py", modules)
        assert increase > 0

    def test_zero_modules(self):
        pattern = Pattern(name="test", r0=1.0)
        increase = predict_r0_increase(pattern, "x.py", [])
        assert increase == 0.0


class TestComputeCrossProtection:
    def test_basic(self):
        good = Pattern(name="structured-logging", pattern_type=PatternType.GOOD)
        bad = Pattern(name="bare-except", pattern_type=PatternType.BAD)
        modules = [
            Module(path="a.py", patterns=["structured-logging"]),
            Module(path="b.py", patterns=["structured-logging"]),
            Module(path="c.py", patterns=["bare-except"]),
            Module(path="d.py", patterns=["bare-except", "structured-logging"]),  # Overlap
        ]
        protection = compute_cross_protection(good, [bad], modules)
        assert "bare-except" in protection
        # 3/4 of modules with structured-logging also have bare-except (a doesn't, b doesn't, d does)
        # So protection should be positive since structured-logging modules have lower bare-except rate

    def test_no_overlap(self):
        good = Pattern(name="structured-logging", pattern_type=PatternType.GOOD)
        bad = Pattern(name="bare-except", pattern_type=PatternType.BAD)
        modules = [
            Module(path="a.py", patterns=["structured-logging"]),
            Module(path="b.py", patterns=["bare-except"]),
        ]
        protection = compute_cross_protection(good, [bad], modules)
        # No overlap -> full protection
        assert protection.get("bare-except", 0) > 0


class TestPromotePattern:
    def test_basic(self):
        pattern = Pattern(name="structured-logging", pattern_type=PatternType.GOOD, r0=2.0)
        modules = [
            Module(path="a.py", patterns=["structured-logging"], developer_traffic=2),
            Module(path="b.py", patterns=[], developer_traffic=5, dependents=3),
            Module(path="c.py", patterns=[], developer_traffic=1),
        ]
        result = promote_pattern(pattern, modules)
        assert result.pattern_name == "structured-logging"
        assert result.current_prevalence >= 1
        assert result.optimal_seed_module != ""

    def test_empty_modules(self):
        pattern = Pattern(name="test", pattern_type=PatternType.GOOD, r0=1.0)
        result = promote_pattern(pattern, [])
        assert result.pattern_name == "test"

    def test_with_bad_patterns(self):
        pattern = Pattern(name="structured-logging", pattern_type=PatternType.GOOD, r0=2.0)
        bad = Pattern(name="bare-except", pattern_type=PatternType.BAD)
        modules = [
            Module(path="a.py", patterns=["structured-logging"]),
            Module(path="b.py", patterns=["bare-except"]),
        ]
        result = promote_pattern(pattern, modules, bad_patterns=[bad])
        assert result.pattern_name == "structured-logging"
