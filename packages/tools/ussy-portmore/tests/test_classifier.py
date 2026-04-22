"""Tests for General Interpretative Rules (GIRs) classification."""
import pytest

from ussy_portmore.classifier import (
    apply_gir1,
    apply_gir2a,
    apply_gir2b,
    apply_gir3a,
    apply_gir3b,
    apply_gir3c,
    classify_licenses,
)
from ussy_portmore.models import MultiLicenseResolution


class TestGIR1:
    """Tests for GIR 1: Classify by headings and section notes first."""

    def test_applied_with_project_license(self):
        result = apply_gir1(["MIT", "Apache-2.0"], "MIT")
        assert result.applied is True
        assert "MIT" in result.outcome

    def test_not_applied_without_project_license(self):
        result = apply_gir1(["MIT", "Apache-2.0"], None)
        assert result.applied is False

    def test_not_applied_project_license_not_in_list(self):
        result = apply_gir1(["MIT", "Apache-2.0"], "GPL-3.0")
        assert result.applied is False

    def test_rule_name(self):
        result = apply_gir1(["MIT"], "MIT")
        assert result.rule == "GIR 1"


class TestGIR2a:
    """Tests for GIR 2a: Essential character of incomplete/unfinished works."""

    def test_applied_with_high_fork_ratio(self):
        result = apply_gir2a(["MIT", "Apache-2.0"], fork_ratio=0.95)
        assert result.applied is True
        assert "original" in result.outcome.lower()

    def test_not_applied_with_low_fork_ratio(self):
        result = apply_gir2a(["MIT", "Apache-2.0"], fork_ratio=0.50)
        assert result.applied is False

    def test_not_applied_single_license(self):
        result = apply_gir2a(["MIT"], fork_ratio=0.95)
        assert result.applied is False

    def test_exactly_90_percent(self):
        result = apply_gir2a(["MIT", "Apache-2.0"], fork_ratio=0.90)
        assert result.applied is True


class TestGIR2b:
    """Tests for GIR 2b: Essential character of mixtures."""

    def test_applied_with_core_license(self):
        result = apply_gir2b(["MIT", "Apache-2.0", "GPL-3.0"], core_license="Apache-2.0")
        assert result.applied is True
        assert "Apache-2.0" in result.outcome

    def test_not_applied_without_core(self):
        result = apply_gir2b(["MIT", "Apache-2.0"])
        assert result.applied is False

    def test_not_applied_core_not_in_list(self):
        result = apply_gir2b(["MIT", "Apache-2.0"], core_license="GPL-3.0")
        assert result.applied is False


class TestGIR3a:
    """Tests for GIR 3a: Specific description prevails."""

    def test_applied_with_different_specificity(self):
        result = apply_gir3a(["MIT", "Apache-2.0"])
        assert result.applied is True
        # Apache-2.0 has higher specificity (patent grant + retaliation)

    def test_not_applied_single_license(self):
        result = apply_gir3a(["MIT"])
        assert result.applied is False

    def test_with_clause_adds_specificity(self):
        result = apply_gir3a(["GPL-2.0", "GPL-2.0 WITH Classpath-exception-2.0"])
        assert result.applied is True


class TestGIR3b:
    """Tests for GIR 3b: Essential character of mixtures."""

    def test_applied_with_different_families(self):
        result = apply_gir3b(["MIT", "GPL-3.0"])
        assert result.applied is True

    def test_not_applied_single_family(self):
        result = apply_gir3b(["MIT", "Apache-2.0"])
        assert result.applied is False

    def test_not_applied_single_license(self):
        result = apply_gir3b(["MIT"])
        assert result.applied is False


class TestGIR3c:
    """Tests for GIR 3c: Most restrictive tiebreaker."""

    def test_applied_with_multiple_licenses(self):
        result = apply_gir3c(["MIT", "GPL-3.0"])
        assert result.applied is True
        assert "GPL-3.0" in result.outcome

    def test_not_applied_single_license(self):
        result = apply_gir3c(["MIT"])
        assert result.applied is False

    def test_gpl_more_restrictive_than_mit(self):
        result = apply_gir3c(["MIT", "GPL-3.0"])
        assert "GPL-3.0" in result.outcome


class TestClassifyLicenses:
    """Tests for the full sequential GIR classification."""

    def test_empty_licenses(self):
        result = classify_licenses([])
        assert result.governing_license == "UNKNOWN"

    def test_single_license(self):
        result = classify_licenses(["MIT"])
        assert result.governing_license == "MIT"
        assert len(result.gir_results) == 1

    def test_gir1_resolves(self):
        result = classify_licenses(
            ["MIT", "Apache-2.0"],
            project_license="MIT",
        )
        assert result.governing_license == "MIT"
        assert any(r.applied and r.rule == "GIR 1" for r in result.gir_results)

    def test_gir2a_resolves(self):
        result = classify_licenses(
            ["MIT", "Apache-2.0"],
            fork_ratio=0.95,
        )
        assert result.governing_license == "MIT"
        assert any(r.applied for r in result.gir_results)

    def test_gir2b_resolves(self):
        result = classify_licenses(
            ["MIT", "Apache-2.0", "GPL-3.0"],
            core_license="Apache-2.0",
        )
        assert result.governing_license == "Apache-2.0"

    def test_gir3c_fallback(self):
        # No project license, no core, no fork ratio
        result = classify_licenses(["MIT", "GPL-3.0"])
        assert result.governing_license == "GPL-3.0"  # More restrictive

    def test_reasoning_chain_populated(self):
        result = classify_licenses(["MIT", "Apache-2.0"], project_license="MIT")
        assert len(result.reasoning_chain) > 0

    def test_hs_code_in_result(self):
        result = classify_licenses(["MIT"])
        assert result.governing_hs_code == "01.01.01"

    def test_timestamp_populated(self):
        result = classify_licenses(["MIT"])
        assert result.timestamp != ""

    def test_multi_license_all_found(self):
        result = classify_licenses(["MIT", "Apache-2.0", "GPL-3.0"])
        assert len(result.licenses_found) == 3
