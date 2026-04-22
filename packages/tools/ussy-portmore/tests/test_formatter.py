"""Tests for the output formatter module."""
import json
import pytest

from portmore.formatter import (
    format_compatibility,
    format_contagion,
    format_origin,
    format_quarantine,
    format_resolution,
    format_valuation,
)
from portmore.models import (
    CompatibilityResult,
    CompatibilityStatus,
    ContagionAssessment,
    DependencyZone,
    GIRResult,
    InjuryIndicator,
    MultiLicenseResolution,
    OriginDetermination,
    OriginStatus,
    QuarantineEntry,
    QuarantineReport,
    ValuationHierarchy,
    ValuationMethod,
    ValuationResult,
)


class TestFormatResolution:
    """Tests for multi-license resolution formatting."""

    def test_text_format(self):
        resolution = MultiLicenseResolution(
            licenses_found=["MIT", "Apache-2.0"],
            gir_results=[GIRResult("GIR 1", "Test", True, "MIT governs")],
            governing_license="MIT",
            governing_hs_code="01.01.01",
            reasoning_chain=["GIR 1 applied"],
        )
        output = format_resolution(resolution, fmt="text")
        assert "MIT" in output
        assert "PORTMORE" in output

    def test_json_format(self):
        resolution = MultiLicenseResolution(
            licenses_found=["MIT"],
            gir_results=[],
            governing_license="MIT",
            governing_hs_code="01.01.01",
        )
        output = format_resolution(resolution, fmt="json")
        data = json.loads(output)
        assert data["governing_license"] == "MIT"
        assert data["governing_hs_code"] == "01.01.01"

    def test_json_round_trip(self):
        resolution = MultiLicenseResolution(
            licenses_found=["MIT", "GPL-3.0"],
            gir_results=[GIRResult("GIR 3c", "Tiebreaker", True, "GPL-3.0")],
            governing_license="GPL-3.0",
            reasoning_chain=["GIR 3c applied"],
        )
        output = format_resolution(resolution, fmt="json")
        data = json.loads(output)
        assert len(data["licenses_found"]) == 2
        assert data["gir_results"][0]["applied"] is True


class TestFormatOrigin:
    """Tests for origin determination formatting."""

    def test_text_format(self):
        det = OriginDetermination(
            module="core", status=OriginStatus.WHOLLY_OBTAINED,
            wholly_obtained=True, ct_classification_changed=False,
            value_added_ratio=0.0, de_minimis_ratio=0.02,
            accumulation_applied=False, absorption_applied=False,
        )
        output = format_origin(det, fmt="text")
        assert "WHOLLY OBTAINED" in output
        assert "core" in output

    def test_json_format(self):
        det = OriginDetermination(
            module="utils", status=OriginStatus.SUBSTANTIALLY_TRANSFORMED,
            wholly_obtained=False, ct_classification_changed=True,
            value_added_ratio=0.60, de_minimis_ratio=0.50,
            accumulation_applied=False, absorption_applied=False,
        )
        output = format_origin(det, fmt="json")
        data = json.loads(output)
        assert data["status"] == "substantially_transformed"


class TestFormatCompatibility:
    """Tests for compatibility result formatting."""

    def test_text_compatible(self):
        result = CompatibilityResult(
            from_license="MIT", to_license="Apache-2.0",
            status=CompatibilityStatus.COMPATIBLE, conditions=[],
        )
        output = format_compatibility(result, fmt="text")
        assert "COMPATIBLE" in output

    def test_text_incompatible(self):
        result = CompatibilityResult(
            from_license="AGPL-3.0", to_license="Proprietary",
            status=CompatibilityStatus.INCOMPATIBLE, conditions=[],
        )
        output = format_compatibility(result, fmt="text")
        assert "INCOMPATIBLE" in output

    def test_json_format(self):
        result = CompatibilityResult(
            from_license="LGPL-2.1", to_license="Apache-2.0",
            status=CompatibilityStatus.CONDITIONAL,
            conditions=["dynamic_link"],
        )
        output = format_compatibility(result, fmt="json")
        data = json.loads(output)
        assert data["status"] == "conditional"
        assert "dynamic_link" in data["conditions"]


class TestFormatValuation:
    """Tests for valuation hierarchy formatting."""

    def test_text_format(self):
        hierarchy = ValuationHierarchy(
            results=[
                ValuationResult(method=ValuationMethod.TRANSACTION, value=300.0,
                                reasoning="MIT obligations"),
            ],
            final_value=300.0,
            final_method=ValuationMethod.TRANSACTION,
        )
        output = format_valuation(hierarchy, fmt="text")
        assert "$" in output
        assert "300" in output

    def test_json_format(self):
        hierarchy = ValuationHierarchy(
            results=[
                ValuationResult(method=ValuationMethod.TRANSACTION, value=300.0),
                ValuationResult(method=ValuationMethod.IDENTICAL, value=315.0),
            ],
            final_value=300.0,
            final_method=ValuationMethod.TRANSACTION,
        )
        output = format_valuation(hierarchy, fmt="json")
        data = json.loads(output)
        assert data["final_value"] == 300.0
        assert len(data["methods"]) == 2


class TestFormatContagion:
    """Tests for contagion assessment formatting."""

    def test_text_format(self):
        assessment = ContagionAssessment(
            license_id="GPL-3.0",
            dumping_margin=-70.0,
            copyleft_ratio=0.70,
            within_duty_order=True,
            injury_indicators=[InjuryIndicator.LOST_LICENSING_OPTIONS],
            causal_link_established=True,
            lesser_duty_remedy="Must provide source for linked module",
            scope_ruling="YES — static linking",
        )
        output = format_contagion(assessment, fmt="text")
        assert "DUMPING" in output
        assert "GPL-3.0" in output

    def test_json_format(self):
        assessment = ContagionAssessment(
            license_id="GPL-3.0",
            dumping_margin=-70.0,
            copyleft_ratio=0.70,
            within_duty_order=True,
            injury_indicators=[],
            causal_link_established=True,
            lesser_duty_remedy="Provide source",
        )
        output = format_contagion(assessment, fmt="json")
        data = json.loads(output)
        assert data["dumping_margin"] == -70.0


class TestFormatQuarantine:
    """Tests for quarantine report formatting."""

    def test_text_format(self):
        report = QuarantineReport(
            entries=[
                QuarantineEntry(
                    dependency="requests", zone=DependencyZone.DOMESTIC,
                    legal_status="duty-paid", obligations=["attribution"],
                ),
            ],
        )
        output = format_quarantine(report, fmt="text")
        assert "requests" in output
        assert "duty-paid" in output

    def test_json_format(self):
        report = QuarantineReport(
            entries=[
                QuarantineEntry(
                    dependency="pytest", zone=DependencyZone.BONDED,
                    legal_status="duty-deferred", obligations=[],
                ),
            ],
            boundary_violations=["pytest: boundary crossed"],
        )
        output = format_quarantine(report, fmt="json")
        data = json.loads(output)
        assert data["entries"][0]["zone"] == "bonded"
        assert len(data["boundary_violations"]) == 1
