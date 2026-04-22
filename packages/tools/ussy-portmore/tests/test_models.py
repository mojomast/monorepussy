"""Tests for data models."""
import pytest

from ussy_portmore.models import (
    ClassifiedLicense,
    CompatibilityResult,
    CompatibilityStatus,
    ContagionAssessment,
    DependencyZone,
    GIRResult,
    HSCode,
    LicenseFamily,
    LicenseObligation,
    MultiLicenseResolution,
    OriginDetermination,
    OriginStatus,
    ProjectInfo,
    QuarantineEntry,
    QuarantineReport,
    ValuationHierarchy,
    ValuationMethod,
    ValuationResult,
    WithdrawalType,
)


class TestHSCodeModel:
    """Tests for HSCode data model."""

    def test_code_property(self):
        hs = HSCode("01", "0101", "010101", "MIT-style", LicenseFamily.PERMISSIVE)
        assert hs.code == "01.01.01"

    def test_str_representation(self):
        hs = HSCode("03", "0302", "030201", "GPL-3.0-style", LicenseFamily.STRONG_COPYLEFT)
        s = str(hs)
        assert "HS" in s
        assert "03.02.01" in s

    def test_family_enum(self):
        hs = HSCode("02", "0201", "020102", "LGPL-2.1", LicenseFamily.WEAK_COPYLEFT)
        assert hs.family == LicenseFamily.WEAK_COPYLEFT


class TestLicenseObligation:
    """Tests for LicenseObligation data model."""

    def test_creation(self):
        ob = LicenseObligation(name="source_disclosure", cost=5000.0)
        assert ob.name == "source_disclosure"
        assert ob.cost == 5000.0

    def test_test_flag(self):
        ob = LicenseObligation(name="test_ob")
        assert ob.__test__ is False


class TestClassifiedLicense:
    """Tests for ClassifiedLicense data model."""

    def test_auto_timestamp(self):
        cl = ClassifiedLicense(
            spdx_id="MIT",
            hs_code=HSCode("01", "0101", "010101", "MIT", LicenseFamily.PERMISSIVE),
            gir_applied="GIR 1",
            reasoning="Single license",
        )
        assert cl.timestamp != ""

    def test_explicit_timestamp(self):
        cl = ClassifiedLicense(
            spdx_id="MIT",
            hs_code=HSCode("01", "0101", "010101", "MIT", LicenseFamily.PERMISSIVE),
            gir_applied="GIR 1",
            reasoning="Single license",
            timestamp="2024-01-01T00:00:00+00:00",
        )
        assert cl.timestamp == "2024-01-01T00:00:00+00:00"


class TestMultiLicenseResolution:
    """Tests for MultiLicenseResolution data model."""

    def test_auto_timestamp(self):
        mr = MultiLicenseResolution(
            licenses_found=["MIT"],
            gir_results=[],
            governing_license="MIT",
        )
        assert mr.timestamp != ""

    def test_default_reasoning_chain(self):
        mr = MultiLicenseResolution(
            licenses_found=["MIT"],
            gir_results=[],
            governing_license="MIT",
        )
        assert mr.reasoning_chain == []


class TestOriginDetermination:
    """Tests for OriginDetermination data model."""

    def test_auto_timestamp(self):
        od = OriginDetermination(
            module="core",
            status=OriginStatus.WHOLLY_OBTAINED,
            wholly_obtained=True,
            ct_classification_changed=False,
            value_added_ratio=0.0,
            de_minimis_ratio=0.02,
            accumulation_applied=False,
            absorption_applied=False,
        )
        assert od.timestamp != ""

    def test_default_thresholds(self):
        od = OriginDetermination(
            module="core",
            status=OriginStatus.WHOLLY_OBTAINED,
            wholly_obtained=True,
            ct_classification_changed=False,
            value_added_ratio=0.0,
            de_minimis_ratio=0.02,
            accumulation_applied=False,
            absorption_applied=False,
        )
        assert od.threshold == 0.40
        assert od.deminimis_threshold == 0.05


class TestCompatibilityResult:
    """Tests for CompatibilityResult data model."""

    def test_auto_timestamp(self):
        cr = CompatibilityResult(
            from_license="MIT",
            to_license="Apache-2.0",
            status=CompatibilityStatus.COMPATIBLE,
            conditions=[],
        )
        assert cr.timestamp != ""

    def test_default_rules_applied(self):
        cr = CompatibilityResult(
            from_license="MIT",
            to_license="Apache-2.0",
            status=CompatibilityStatus.COMPATIBLE,
            conditions=[],
        )
        assert cr.rules_applied == []


class TestValuationResult:
    """Tests for ValuationResult data model."""

    def test_auto_timestamp(self):
        vr = ValuationResult(
            method=ValuationMethod.TRANSACTION,
            value=300.0,
        )
        assert vr.timestamp != ""

    def test_defaults(self):
        vr = ValuationResult(
            method=ValuationMethod.TRANSACTION,
            value=300.0,
        )
        assert vr.currency == "USD"
        assert vr.article8_adjustments == 0.0
        assert vr.related_party_adjustment == 0.0


class TestValuationHierarchy:
    """Tests for ValuationHierarchy data model."""

    def test_auto_timestamp(self):
        vh = ValuationHierarchy()
        assert vh.timestamp != ""

    def test_defaults(self):
        vh = ValuationHierarchy()
        assert vh.results == []
        assert vh.final_value == 0.0
        assert vh.final_method == ValuationMethod.TRANSACTION


class TestContagionAssessment:
    """Tests for ContagionAssessment data model."""

    def test_auto_timestamp(self):
        ca = ContagionAssessment(
            license_id="GPL-3.0",
            dumping_margin=-70.0,
            copyleft_ratio=0.70,
            within_duty_order=True,
            injury_indicators=[],
            causal_link_established=True,
            lesser_duty_remedy="Provide source",
        )
        assert ca.timestamp != ""


class TestQuarantineEntry:
    """Tests for QuarantineEntry data model."""

    def test_auto_timestamp(self):
        qe = QuarantineEntry(
            dependency="lib",
            zone=DependencyZone.BONDED,
            legal_status="duty-deferred",
            obligations=[],
        )
        assert qe.timestamp != ""

    def test_defaults(self):
        qe = QuarantineEntry(
            dependency="lib",
            zone=DependencyZone.BONDED,
            legal_status="duty-deferred",
            obligations=[],
        )
        assert qe.withdrawal_type is None
        assert qe.manipulation_warning is False
        assert qe.constructive_warehouse is False


class TestQuarantineReport:
    """Tests for QuarantineReport data model."""

    def test_auto_timestamp(self):
        qr = QuarantineReport()
        assert qr.timestamp != ""

    def test_defaults(self):
        qr = QuarantineReport()
        assert qr.entries == []
        assert qr.boundary_violations == []
        assert qr.manipulation_warnings == []


class TestProjectInfo:
    """Tests for ProjectInfo data model."""

    def test_creation(self):
        pi = ProjectInfo(name="test", path="/tmp/test")
        assert pi.name == "test"
        assert pi.licenses == []
        assert pi.dependencies == []
        assert pi.dev_dependencies == []
        assert pi.modules == []


class TestEnums:
    """Tests for enumeration values."""

    def test_license_families(self):
        assert LicenseFamily.PERMISSIVE.value == "01"
        assert LicenseFamily.WEAK_COPYLEFT.value == "02"
        assert LicenseFamily.STRONG_COPYLEFT.value == "03"
        assert LicenseFamily.PROPRIETARY.value == "04"
        assert LicenseFamily.PUBLIC_DOMAIN.value == "05"

    def test_dependency_zones(self):
        assert DependencyZone.BONDED.value == "bonded"
        assert DependencyZone.DOMESTIC.value == "domestic"

    def test_withdrawal_types(self):
        assert WithdrawalType.EXPORT.value == "export"
        assert WithdrawalType.DOMESTIC.value == "domestic"

    def test_origin_statuses(self):
        assert OriginStatus.WHOLLY_OBTAINED.value == "wholly_obtained"
        assert OriginStatus.SUBSTANTIALLY_TRANSFORMED.value == "substantially_transformed"
        assert OriginStatus.NON_ORIGINATING.value == "non_originating"

    def test_compatibility_statuses(self):
        assert CompatibilityStatus.COMPATIBLE.value == "compatible"
        assert CompatibilityStatus.CONDITIONAL.value == "conditional"
        assert CompatibilityStatus.INCOMPATIBLE.value == "incompatible"

    def test_valuation_methods(self):
        assert ValuationMethod.TRANSACTION.value == 1
        assert ValuationMethod.IDENTICAL.value == 2
        assert ValuationMethod.SIMILAR.value == 3
        assert ValuationMethod.DEDUCTIVE.value == 4
        assert ValuationMethod.COMPUTED.value == 5
        assert ValuationMethod.FALLBACK.value == 6
