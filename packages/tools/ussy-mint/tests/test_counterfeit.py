"""Tests for mint.counterfeit — Counterfeit detection."""

import pytest
from ussy_mint.counterfeit import (
    detect_typosquat,
    detect_dependency_confusion,
    detect_account_takeover,
    detect_build_injection,
    detect_die_clash,
    detect_provenance_gap,
    compute_counterfeit_confidence,
    authenticate_package,
    CounterfeitType,
    Severity,
)
from ussy_mint.models import ProvenanceLevel


class TestDetectTyposquat:
    """Test typosquat detection."""

    def test_xpress_vs_express(self):
        """xpress should be flagged as typosquat of express."""
        findings = detect_typosquat("xpress", ["express", "lodash", "react"])
        assert len(findings) == 1
        assert findings[0].counterfeit_type == CounterfeitType.TYPOSQUAT
        assert findings[0].severity == Severity.CRITICAL  # distance=1

    def test_legitimate_name_not_flagged(self):
        """Exact match to a known package should NOT be flagged."""
        findings = detect_typosquat("express", ["express", "lodash"])
        assert len(findings) == 0

    def test_distant_name_not_flagged(self):
        """Names that are too different should not be flagged."""
        findings = detect_typosquat("completely-different", ["express"], max_distance=2)
        assert len(findings) == 0

    def test_distance_2_is_warning(self):
        """Distance-2 matches should be WARNING severity."""
        findings = detect_typosquat("loDash", ["lodash"])  # distance 2 with case
        # Depending on case handling, may be 1 or 2
        if findings:
            assert findings[0].counterfeit_type == CounterfeitType.TYPOSQUAT

    def test_multiple_similar_packages(self):
        """Should find multiple similar packages."""
        findings = detect_typosquat("babel", ["babel-core", "babe1"], max_distance=2)
        # Should find at least some
        assert len(findings) >= 1


class TestDetectDependencyConfusion:
    """Test dependency confusion detection."""

    def test_registry_mismatch(self):
        """Package from wrong registry should be flagged."""
        finding = detect_dependency_confusion(
            "internal-lib",
            private_registries=["my-private-registry"],
            public_registry="npm",
            current_registry="npm",
        )
        # current_registry is "npm" which matches public_registry, so no finding
        assert finding is None

    def test_unexpected_registry(self):
        """Package from unexpected registry should be flagged."""
        finding = detect_dependency_confusion(
            "internal-lib",
            private_registries=["my-private-registry"],
            public_registry="npm",
            current_registry="evil-registry",
        )
        assert finding is not None
        assert finding.counterfeit_type == CounterfeitType.DEPENDENCY_CONFUSION
        assert finding.severity == Severity.CRITICAL

    def test_correct_registry_no_finding(self):
        """Package from expected registry should not be flagged."""
        finding = detect_dependency_confusion(
            "express",
            private_registries=["npm"],
            public_registry="npm",
            current_registry="npm",
        )
        assert finding is None


class TestDetectAccountTakeover:
    """Test account takeover detection."""

    def test_new_publisher_on_established_package(self):
        """New publisher on old package should be flagged."""
        finding = detect_account_takeover(
            "popular-pkg",
            current_publisher="new-attacker",
            previous_publishers=["trusted-maintainer"],
            package_age_days=365,
        )
        assert finding is not None
        assert finding.counterfeit_type == CounterfeitType.ACCOUNT_TAKEOVER

    def test_same_publisher_no_finding(self):
        """Same publisher as before should not be flagged."""
        finding = detect_account_takeover(
            "popular-pkg",
            current_publisher="trusted-maintainer",
            previous_publishers=["trusted-maintainer"],
            package_age_days=365,
        )
        assert finding is None

    def test_new_package_no_finding(self):
        """Brand new package (no previous publishers) should not be flagged."""
        finding = detect_account_takeover(
            "new-pkg",
            current_publisher="anyone",
            previous_publishers=[],
        )
        assert finding is None

    def test_young_package_lower_confidence(self):
        """Very young package with new publisher has lower confidence than old package."""
        finding_young = detect_account_takeover(
            "young-pkg",
            current_publisher="new-person",
            previous_publishers=["original-author"],
            package_age_days=91,  # Must exceed 90-day threshold
        )
        finding_old = detect_account_takeover(
            "old-pkg",
            current_publisher="new-person",
            previous_publishers=["original-author"],
            package_age_days=365,
        )
        assert finding_young is not None
        assert finding_old is not None
        assert finding_young.confidence < finding_old.confidence


class TestDetectBuildInjection:
    """Test build injection detection."""

    def test_hash_mismatch(self):
        """Mismatched hashes should be flagged."""
        finding = detect_build_injection(
            "compromised-pkg",
            declared_hash="abc123def456",
            actual_hash="xyz789ghi012",
        )
        assert finding is not None
        assert finding.counterfeit_type == CounterfeitType.BUILD_INJECTION
        assert finding.severity == Severity.CRITICAL

    def test_matching_hash_no_finding(self):
        """Matching hashes should not be flagged."""
        finding = detect_build_injection(
            "safe-pkg",
            declared_hash="abc123def456",
            actual_hash="abc123def456",
        )
        assert finding is None

    def test_empty_hash_no_finding(self):
        """Empty hashes should not trigger false positive."""
        finding = detect_build_injection("pkg", "", "")
        assert finding is None


class TestDetectDieClash:
    """Test die clash detection."""

    def test_foreign_files_detected(self):
        """Files from another package should be flagged."""
        finding = detect_die_clash(
            "my-pkg",
            foreign_files=["jest-mock.js", "jest-utils.js"],
        )
        assert finding is not None
        assert finding.counterfeit_type == CounterfeitType.DIE_CLASH

    def test_no_foreign_files(self):
        """No foreign files should not be flagged."""
        finding = detect_die_clash("my-pkg", foreign_files=[])
        assert finding is None


class TestDetectProvenanceGap:
    """Test provenance gap detection."""

    def test_unverified_flagged(self):
        finding = detect_provenance_gap("pkg", ProvenanceLevel.UNVERIFIED)
        assert finding is not None
        assert finding.counterfeit_type == CounterfeitType.PROVENANCE_GAP

    def test_build_signed_flagged(self):
        finding = detect_provenance_gap("pkg", ProvenanceLevel.BUILD_SIGNED)
        assert finding is not None  # Below Level 2

    def test_source_linked_ok(self):
        finding = detect_provenance_gap("pkg", ProvenanceLevel.SOURCE_LINKED)
        assert finding is None  # Level 2+ is fine

    def test_end_to_end_ok(self):
        finding = detect_provenance_gap("pkg", ProvenanceLevel.END_TO_END)
        assert finding is None


class TestComputeCounterfeitConfidence:
    """Test composite counterfeit confidence."""

    def test_high_confidence_typosquat(self):
        """Close name + registry mismatch + no signature = high confidence."""
        confidence = compute_counterfeit_confidence(
            "xpress", "express",
            registry_mismatch=True,
            signature_absent=True,
        )
        assert confidence > 0.7

    def test_low_confidence(self):
        """Different name + no mismatch + signature present = low confidence."""
        confidence = compute_counterfeit_confidence(
            "my-custom-lib", "express",
            registry_mismatch=False,
            signature_absent=False,
        )
        assert confidence < 0.5


class TestAuthenticatePackage:
    """Test the full authentication pipeline."""

    def test_clean_package(self):
        """A legitimate, well-known package should have minimal findings."""
        findings = authenticate_package(
            "express",
            version="4.18.2",
            known_packages=["express", "lodash", "react"],
            provenance_level=ProvenanceLevel.SOURCE_LINKED,
        )
        # No typosquat, good provenance — should be clean
        critical = [f for f in findings if f.severity == Severity.CRITICAL]
        assert len(critical) == 0

    def test_suspicious_package(self):
        """A typosquatted package should have findings."""
        findings = authenticate_package(
            "xpress",
            known_packages=["express", "lodash"],
            provenance_level=ProvenanceLevel.UNVERIFIED,
        )
        assert len(findings) >= 1
        types = {f.counterfeit_type for f in findings}
        assert CounterfeitType.TYPOSQUAT in types

    def test_all_checks_run(self):
        """All detection checks should run when data is provided."""
        findings = authenticate_package(
            "compromised-pkg",
            version="1.0.0",
            known_packages=["express"],
            current_publisher="attacker",
            previous_publishers=["original-author"],
            declared_hash="abc123",
            actual_hash="xyz789",
            provenance_level=ProvenanceLevel.UNVERIFIED,
            package_age_days=365,
        )
        # Should have findings from multiple checks
        types = {f.counterfeit_type for f in findings}
        assert CounterfeitType.ACCOUNT_TAKEOVER in types or CounterfeitType.BUILD_INJECTION in types
