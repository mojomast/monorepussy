"""Tests for prescribe module."""

from __future__ import annotations

import pytest

from seral.models import GovernancePrescription, GovernanceRule, ModuleMetrics, Stage
from seral.prescribe import (
    get_builtin_rules,
    governance_diff,
    prescribe,
)


class TestGetBuiltinRules:
    """Tests for get_builtin_rules."""

    def test_pioneer_rules(self):
        rules = get_builtin_rules(Stage.PIONEER)
        assert "mandatory" in rules
        assert "recommended" in rules
        assert "forbidden" in rules
        assert len(rules["mandatory"]) >= 1

    def test_climax_rules(self):
        rules = get_builtin_rules(Stage.CLIMAX)
        assert len(rules["mandatory"]) >= 3
        assert len(rules["forbidden"]) >= 2

    def test_disturbed_rules(self):
        rules = get_builtin_rules(Stage.DISTURBED)
        assert len(rules["mandatory"]) >= 1
        assert len(rules["recommended"]) >= 1

    def test_all_stages_have_rules(self):
        for stage in Stage:
            rules = get_builtin_rules(stage)
            assert isinstance(rules, dict)
            assert "mandatory" in rules

    def test_seral_early_rules(self):
        rules = get_builtin_rules(Stage.SERAL_EARLY)
        assert len(rules["mandatory"]) >= 2

    def test_seral_late_rules(self):
        rules = get_builtin_rules(Stage.SERAL_LATE)
        assert len(rules["mandatory"]) >= 3


class TestPrescribe:
    """Tests for prescribe function."""

    def test_prescribe_pioneer(self):
        p = prescribe(Stage.PIONEER, "src/test")
        assert isinstance(p, GovernancePrescription)
        assert p.stage == Stage.PIONEER
        assert p.path == "src/test"
        assert len(p.mandatory) >= 1

    def test_prescribe_climax(self):
        p = prescribe(Stage.CLIMAX, "src/auth")
        assert p.stage == Stage.CLIMAX
        assert len(p.mandatory) >= 3
        assert len(p.forbidden) >= 2

    def test_prescribe_with_metrics(self):
        metrics = ModuleMetrics(
            path="src/test",
            age_days=100,
            commit_count=50,
            contributor_count=3,
            test_coverage=0.6,
        )
        p = prescribe(Stage.SERAL_MID, "src/test", metrics)
        assert p.stage == Stage.SERAL_MID

    def test_prescribe_default_path(self):
        p = prescribe(Stage.PIONEER)
        assert p.path == ""

    def test_prescribe_mandatory_rules_have_category(self):
        p = prescribe(Stage.CLIMAX)
        for rule in p.mandatory:
            assert rule.category == "mandatory"

    def test_prescribe_recommended_rules_have_category(self):
        p = prescribe(Stage.SERAL_MID)
        for rule in p.recommended:
            assert rule.category == "recommended"

    def test_prescribe_forbidden_rules_have_category(self):
        p = prescribe(Stage.CLIMAX)
        for rule in p.forbidden:
            assert rule.category == "forbidden"


class TestGovernanceDiff:
    """Tests for governance_diff."""

    def test_diff_pioneer_to_climax(self):
        diff = governance_diff(Stage.PIONEER, Stage.CLIMAX)
        assert "added" in diff
        assert "removed" in diff
        assert "changed" in diff
        assert len(diff["added"]) > 0

    def test_diff_same_stage(self):
        diff = governance_diff(Stage.PIONEER, Stage.PIONEER)
        assert len(diff["added"]) == 0
        assert len(diff["removed"]) == 0

    def test_diff_pioneer_to_seral(self):
        diff = governance_diff(Stage.PIONEER, Stage.SERAL_MID)
        assert len(diff["added"]) > 0

    def test_diff_climax_to_pioneer(self):
        diff = governance_diff(Stage.CLIMAX, Stage.PIONEER)
        assert len(diff["removed"]) > 0

    def test_diff_includes_categories(self):
        diff = governance_diff(Stage.PIONEER, Stage.CLIMAX)
        # Added items should mention their category
        for item in diff["added"]:
            assert "ADDED" in item

    def test_diff_removed_items(self):
        diff = governance_diff(Stage.CLIMAX, Stage.PIONEER)
        for item in diff["removed"]:
            assert "REMOVED" in item


class TestGovernanceDiffFunction:
    """Test the governance_diff function."""

    def test_governance_diff_works(self):
        diff = governance_diff(Stage.PIONEER, Stage.CLIMAX)
        assert "added" in diff
