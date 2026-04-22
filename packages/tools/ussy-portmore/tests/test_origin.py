"""Tests for Rules of Origin — Provenance Determination."""
import pytest

from ussy_portmore.origin import (
    accumulation_test,
    absorption_rule,
    de_minimis_test,
    determine_origin,
    substantial_transformation_ctc,
    value_added_test,
    wholly_obtained_test,
)
from ussy_portmore.models import OriginStatus


class TestWhollyObtained:
    """Tests for the wholly obtained test."""

    def test_zero_third_party(self):
        assert wholly_obtained_test(0.0) is True

    def test_below_deminimis(self):
        assert wholly_obtained_test(0.03) is True

    def test_at_deminimis(self):
        assert wholly_obtained_test(0.05) is True

    def test_above_deminimis(self):
        assert wholly_obtained_test(0.10) is False

    def test_custom_threshold(self):
        assert wholly_obtained_test(0.03, deminimis_threshold=0.02) is False


class TestSubstantialTransformationCTC:
    """Tests for change in tariff classification."""

    def test_classification_changed(self):
        assert substantial_transformation_ctc("01.01.01", "03.02.01") is True

    def test_classification_unchanged(self):
        assert substantial_transformation_ctc("01.01.01", "01.01.01") is False

    def test_different_chapter(self):
        assert substantial_transformation_ctc("01.01.01", "02.01.01") is True


class TestValueAddedTest:
    """Tests for the value-added test."""

    def test_above_threshold(self):
        assert value_added_test(0.50) is True

    def test_below_threshold(self):
        assert value_added_test(0.30) is False

    def test_at_threshold(self):
        assert value_added_test(0.40) is True

    def test_custom_threshold(self):
        assert value_added_test(0.30, threshold=0.25) is True


class TestDeMinimisTest:
    """Tests for the de minimis test."""

    def test_below_threshold(self):
        assert de_minimis_test(0.03) is True

    def test_at_threshold(self):
        assert de_minimis_test(0.05) is False  # Strict <

    def test_above_threshold(self):
        assert de_minimis_test(0.10) is False


class TestAccumulationTest:
    """Tests for the accumulation test."""

    def test_accumulation_sufficient(self):
        ratios = [0.15, 0.15, 0.15]
        assert accumulation_test(ratios) is True

    def test_accumulation_insufficient(self):
        ratios = [0.05, 0.05]
        assert accumulation_test(ratios) is False

    def test_accumulation_empty(self):
        assert accumulation_test([]) is False

    def test_accumulation_custom_threshold(self):
        ratios = [0.20, 0.15]
        assert accumulation_test(ratios, threshold=0.50) is False


class TestAbsorptionRule:
    """Tests for the absorption rule."""

    def test_originating_component_retains_status(self):
        assert absorption_rule(OriginStatus.WHOLLY_OBTAINED, OriginStatus.NON_ORIGINATING) is True

    def test_non_originating_component(self):
        assert absorption_rule(OriginStatus.NON_ORIGINATING, OriginStatus.NON_ORIGINATING) is False

    def test_substantially_transformed_component(self):
        assert absorption_rule(OriginStatus.SUBSTANTIALLY_TRANSFORMED, OriginStatus.NON_ORIGINATING) is False


class TestDetermineOrigin:
    """Tests for the full origin determination."""

    def test_wholly_obtained_module(self):
        det = determine_origin(
            module="core",
            third_party_ratio=0.02,
            modification_ratio=0.0,
            original_hs_code="01.01.01",
            modified_hs_code="01.01.01",
        )
        assert det.status == OriginStatus.WHOLLY_OBTAINED
        assert det.wholly_obtained is True

    def test_substantially_transformed_by_ctc(self):
        det = determine_origin(
            module="forked",
            third_party_ratio=0.50,
            modification_ratio=0.30,
            original_hs_code="01.01.01",
            modified_hs_code="03.02.01",
        )
        assert det.status == OriginStatus.SUBSTANTIALLY_TRANSFORMED
        assert det.ct_classification_changed is True

    def test_substantially_transformed_by_value(self):
        det = determine_origin(
            module="modified",
            third_party_ratio=0.50,
            modification_ratio=0.60,
            original_hs_code="01.01.01",
            modified_hs_code="01.01.01",
        )
        assert det.status == OriginStatus.SUBSTANTIALLY_TRANSFORMED
        assert det.ct_classification_changed is False

    def test_non_originating(self):
        det = determine_origin(
            module="vendor",
            third_party_ratio=0.80,
            modification_ratio=0.10,
            original_hs_code="01.01.01",
            modified_hs_code="01.01.01",
        )
        assert det.status == OriginStatus.NON_ORIGINATING

    def test_accumulation_applied(self):
        det = determine_origin(
            module="shared",
            third_party_ratio=0.50,
            modification_ratio=0.20,
            original_hs_code="01.01.01",
            modified_hs_code="01.01.01",
            contributor_ratios=[0.15, 0.15, 0.15],
            threshold=0.40,
        )
        assert det.accumulation_applied is True
        assert det.status == OriginStatus.SUBSTANTIALLY_TRANSFORMED

    def test_timestamp_populated(self):
        det = determine_origin(
            module="core",
            third_party_ratio=0.0,
            modification_ratio=0.0,
            original_hs_code="01.01.01",
            modified_hs_code="01.01.01",
        )
        assert det.timestamp != ""

    def test_custom_thresholds(self):
        det = determine_origin(
            module="core",
            third_party_ratio=0.02,
            modification_ratio=0.0,
            original_hs_code="01.01.01",
            modified_hs_code="01.01.01",
            threshold=0.50,
            deminimis_threshold=0.01,
        )
        assert det.threshold == 0.50
        assert det.deminimis_threshold == 0.01
