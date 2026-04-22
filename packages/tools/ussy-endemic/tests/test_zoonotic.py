"""Tests for endemic.zoonotic module."""

import pytest

from endemic.models import Module, Pattern, PatternType, Compartment, ZoonoticJump
from endemic.zoonotic import (
    detect_zoonotic_jumps,
    format_zoonotic_alert,
    infer_domain,
    is_pattern_appropriate_in_domain,
)


class TestInferDomain:
    def test_web(self):
        assert infer_domain("src/web/api_handler.py") == "web"

    def test_data(self):
        assert infer_domain("src/data/pipeline/transform.py") == "data"

    def test_core(self):
        assert infer_domain("src/core/model.py") == "core"

    def test_infrastructure(self):
        assert infer_domain("src/infra/database.py") == "infrastructure"

    def test_testing(self):
        assert infer_domain("tests/test_handler.py") == "testing"

    def test_utils(self):
        assert infer_domain("src/util/helper.py") == "utils"

    def test_unknown(self):
        assert infer_domain("src/xyz/abc.py") == "unknown"


class TestIsPatternAppropriateInDomain:
    def test_bare_except_web(self):
        p = Pattern(name="bare-except", pattern_type=PatternType.BAD)
        assert is_pattern_appropriate_in_domain(p, "web") is True

    def test_bare_except_data(self):
        p = Pattern(name="bare-except", pattern_type=PatternType.BAD)
        assert is_pattern_appropriate_in_domain(p, "data") is False

    def test_print_debugging_testing(self):
        p = Pattern(name="print-debugging", pattern_type=PatternType.BAD)
        assert is_pattern_appropriate_in_domain(p, "testing") is True

    def test_unknown_pattern(self):
        p = Pattern(name="custom-pattern", pattern_type=PatternType.BAD)
        # Default is appropriate
        assert is_pattern_appropriate_in_domain(p, "web") is True


class TestDetectZoonoticJumps:
    def test_cross_domain_jump(self):
        modules = [
            Module(path="src/web/api.py", patterns=["bare-except"], domain="web"),
            Module(path="src/data/pipeline.py", patterns=["bare-except"], domain="data"),
        ]
        patterns = [
            Pattern(name="bare-except", pattern_type=PatternType.BAD),
        ]
        jumps = detect_zoonotic_jumps(modules, patterns)
        assert len(jumps) > 0
        # bare-except jumped from web to data
        jump = jumps[0]
        assert jump.pattern_name == "bare-except"

    def test_no_jump_same_domain(self):
        modules = [
            Module(path="src/web/api.py", patterns=["bare-except"], domain="web"),
            Module(path="src/web/routes.py", patterns=["bare-except"], domain="web"),
        ]
        patterns = [
            Pattern(name="bare-except", pattern_type=PatternType.BAD),
        ]
        jumps = detect_zoonotic_jumps(modules, patterns)
        assert len(jumps) == 0

    def test_no_jump_single_domain(self):
        modules = [
            Module(path="src/web/api.py", patterns=["bare-except"], domain="web"),
        ]
        patterns = [
            Pattern(name="bare-except", pattern_type=PatternType.BAD),
        ]
        jumps = detect_zoonotic_jumps(modules, patterns)
        assert len(jumps) == 0

    def test_auto_domain_inference(self):
        modules = [
            Module(path="src/web/api.py", patterns=["bare-except"]),
            Module(path="src/data/pipeline.py", patterns=["bare-except"]),
        ]
        patterns = [
            Pattern(name="bare-except", pattern_type=PatternType.BAD),
        ]
        jumps = detect_zoonotic_jumps(modules, patterns)
        assert len(jumps) > 0


class TestFormatZoonoticAlert:
    def test_basic_alert(self):
        jump = ZoonoticJump(
            pattern_name="bare-except",
            origin_domain="web",
            target_domain="data",
            origin_module="src/web/api.py",
            target_module="src/data/pipeline.py",
            risk="HIGH",
            is_appropriate_in_origin=True,
            recommendation="Replace with domain-specific error handling",
        )
        alert = format_zoonotic_alert(jump)
        assert "ZOONOTIC JUMP DETECTED" in alert
        assert "bare-except" in alert
        assert "HIGH" in alert

    def test_medium_risk_alert(self):
        jump = ZoonoticJump(
            pattern_name="no-type-hints",
            origin_domain="utils",
            target_domain="core",
            origin_module="src/util/helper.py",
            target_module="src/core/model.py",
            risk="MEDIUM",
        )
        alert = format_zoonotic_alert(jump)
        assert "ZOONOTIC JUMP" in alert
