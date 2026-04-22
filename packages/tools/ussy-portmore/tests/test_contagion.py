"""Tests for Anti-Dumping/CVD — Copyleft Contagion Containment."""
import pytest

from ussy_portmore.contagion import (
    assess_contagion,
    causal_link_test,
    circumvention_threshold_test,
    compute_dumping_margin,
    lesser_duty_remedy,
    material_injury_test,
    scope_ruling,
)
from ussy_portmore.models import InjuryIndicator


class TestDumpingMargin:
    """Tests for dumping margin computation."""

    def test_mit_positive_margin(self):
        # MIT: rights=100, obligations=5 → DM=95 (fair value)
        dm = compute_dumping_margin("MIT")
        assert dm > 0

    def test_gpl3_negative_margin(self):
        # GPL-3.0: rights=20, obligations=90 → DM=-70 (dumping)
        dm = compute_dumping_margin("GPL-3.0")
        assert dm < 0

    def test_cc0_high_margin(self):
        dm = compute_dumping_margin("CC0-1.0")
        assert dm == 100.0  # rights=100, obligations=0

    def test_agpl3_very_negative(self):
        dm = compute_dumping_margin("AGPL-3.0")
        assert dm < -50  # Very high obligations surrendered

    def test_apache2_slight_positive(self):
        dm = compute_dumping_margin("Apache-2.0")
        # Apache-2.0 has patent grant but still permissive
        assert dm > 0

    def test_lgpl21_moderate(self):
        dm = compute_dumping_margin("LGPL-2.1")
        assert dm > -50  # Weak copyleft, less dumping


class TestMaterialInjury:
    """Tests for material injury test."""

    def test_gpl3_auto_detects(self):
        indicators = material_injury_test("GPL-3.0")
        assert InjuryIndicator.LOST_LICENSING_OPTIONS in indicators

    def test_mit_no_injury(self):
        indicators = material_injury_test("MIT")
        assert len(indicators) == 0

    def test_agpl3_forced_disclosure(self):
        indicators = material_injury_test("AGPL-3.0", forced_code_disclosure=True)
        assert InjuryIndicator.FORCED_CODE_DISCLOSURE in indicators

    def test_multiple_indicators(self):
        indicators = material_injury_test(
            "GPL-3.0",
            lost_licensing_options=True,
            forced_code_disclosure=True,
            competitive_disadvantage=True,
        )
        assert len(indicators) == 3


class TestCausalLink:
    """Tests for causal link test."""

    def test_strong_copyleft_with_code(self):
        assert causal_link_test("GPL-3.0", copyleft_code_ratio=0.30) is True

    def test_strong_copyleft_zero_code(self):
        assert causal_link_test("GPL-3.0", copyleft_code_ratio=0.0) is False

    def test_permissive_no_link(self):
        assert causal_link_test("MIT", copyleft_code_ratio=0.50) is False

    def test_weak_copyleft_above_threshold(self):
        assert causal_link_test("LGPL-2.1", copyleft_code_ratio=0.40) is True

    def test_weak_copyleft_below_threshold(self):
        assert causal_link_test("LGPL-2.1", copyleft_code_ratio=0.20) is False

    def test_counterfactual_blocks(self):
        assert causal_link_test("GPL-3.0", 0.50, would_obligation_exist_without=True) is False


class TestCircumventionThreshold:
    """Tests for the 60% circumvention threshold."""

    def test_above_threshold(self):
        assert circumvention_threshold_test(0.70) is True

    def test_at_threshold(self):
        assert circumvention_threshold_test(0.60) is False  # Strict > 0.60

    def test_below_threshold(self):
        assert circumvention_threshold_test(0.50) is False

    def test_custom_threshold(self):
        assert circumvention_threshold_test(0.50, threshold=0.40) is True


class TestLesserDutyRemedy:
    """Tests for the lesser duty remedy."""

    def test_gpl3_high_ratio(self):
        remedy = lesser_duty_remedy("GPL-3.0", 0.95)
        assert "complete corresponding source" in remedy.lower()

    def test_gpl3_moderate_ratio(self):
        remedy = lesser_duty_remedy("GPL-3.0", 0.70)
        assert "gpl-linked module" in remedy.lower() or "copyleft-linked module" in remedy.lower()

    def test_gpl3_low_ratio(self):
        remedy = lesser_duty_remedy("GPL-3.0", 0.20)
        assert "attribution" in remedy.lower()

    def test_mit_minimal_remedy(self):
        remedy = lesser_duty_remedy("MIT", 0.50)
        assert "attribution" in remedy.lower()

    def test_lgpl_moderate_ratio(self):
        remedy = lesser_duty_remedy("LGPL-2.1", 0.70)
        assert "modified" in remedy.lower() or "weak-copyleft" in remedy.lower()


class TestScopeRuling:
    """Tests for scope ruling."""

    def test_static_link_in_scope(self):
        ruling = scope_ruling("static")
        assert "YES" in ruling

    def test_dynamic_link_out_of_scope(self):
        ruling = scope_ruling("dynamic")
        assert "NO" in ruling

    def test_socket_api_context_dependent(self):
        ruling = scope_ruling("socket")
        assert "CONTEXT-DEPENDENT" in ruling

    def test_microservice_usually_no(self):
        ruling = scope_ruling("microservice")
        assert "NO" in ruling or "Usually" in ruling

    def test_unknown_type(self):
        ruling = scope_ruling("quantum_entanglement")
        assert "UNKNOWN" in ruling or "manual" in ruling.lower()


class TestAssessContagion:
    """Tests for the full contagion assessment."""

    def test_gpl3_assessment(self):
        assessment = assess_contagion("GPL-3.0", copyleft_ratio=0.70)
        assert assessment.dumping_margin < 0
        assert assessment.within_duty_order is True
        assert len(assessment.injury_indicators) > 0
        assert assessment.causal_link_established is True
        assert assessment.scope_ruling != ""

    def test_mit_no_contagion(self):
        assessment = assess_contagion("MIT", copyleft_ratio=0.0)
        assert assessment.dumping_margin > 0
        assert assessment.within_duty_order is False
        assert len(assessment.injury_indicators) == 0

    def test_agpl3_high_contagion(self):
        assessment = assess_contagion("AGPL-3.0", copyleft_ratio=0.80)
        assert assessment.dumping_margin < -50
        assert assessment.within_duty_order is True

    def test_timestamp_populated(self):
        assessment = assess_contagion("GPL-3.0", copyleft_ratio=0.50)
        assert assessment.timestamp != ""

    def test_custom_threshold(self):
        assessment = assess_contagion("GPL-3.0", copyleft_ratio=0.50, threshold=0.40)
        assert assessment.within_duty_order is True  # 0.50 > 0.40
