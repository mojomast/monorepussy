"""Tests for Preferential Trade Agreements — License Compatibility."""
import pytest

from ussy_portmore.compatibility import (
    check_compatibility,
    get_zone,
    PERMISSIVE_ZONE,
    COPYLEFT_ZONE,
    WEAK_COPYLEFT_ZONE,
)
from ussy_portmore.models import CompatibilityStatus


class TestZoneClassification:
    """Tests for license zone classification."""

    def test_mit_in_permissive_zone(self):
        assert get_zone("MIT") == "permissive"

    def test_apache_in_permissive_zone(self):
        assert get_zone("Apache-2.0") == "permissive"

    def test_gpl3_in_copyleft_zone(self):
        assert get_zone("GPL-3.0") == "copyleft"

    def test_agpl3_in_copyleft_zone(self):
        assert get_zone("AGPL-3.0") == "copyleft"

    def test_lgpl21_in_weak_copyleft_zone(self):
        assert get_zone("LGPL-2.1") == "weak_copyleft"

    def test_mpl2_in_weak_copyleft_zone(self):
        assert get_zone("MPL-2.0") == "weak_copyleft"

    def test_cc0_in_public_domain_zone(self):
        assert get_zone("CC0-1.0") == "public_domain"

    def test_unknown_license(self):
        zone = get_zone("SomeRandomLicense-1.0")
        assert zone == "unknown"


class TestCompatiblePairs:
    """Tests for known compatible license pairs."""

    def test_mit_apache_compatible(self):
        result = check_compatibility("MIT", "Apache-2.0")
        assert result.status == CompatibilityStatus.COMPATIBLE

    def test_mit_bsd2_compatible(self):
        result = check_compatibility("MIT", "BSD-2-Clause")
        assert result.status == CompatibilityStatus.COMPATIBLE

    def test_gpl3_mit_compatible(self):
        result = check_compatibility("GPL-3.0", "MIT")
        assert result.status == CompatibilityStatus.COMPATIBLE

    def test_cc0_mit_compatible(self):
        result = check_compatibility("CC0-1.0", "MIT")
        assert result.status == CompatibilityStatus.COMPATIBLE

    def test_same_zone_permissive(self):
        result = check_compatibility("ISC", "MIT")
        assert result.status == CompatibilityStatus.COMPATIBLE


class TestIncompatiblePairs:
    """Tests for known incompatible license pairs."""

    def test_agpl3_proprietary_incompatible(self):
        result = check_compatibility("AGPL-3.0", "Proprietary")
        assert result.status == CompatibilityStatus.INCOMPATIBLE

    def test_gpl2only_apache_incompatible(self):
        result = check_compatibility("GPL-2.0-only", "Apache-2.0")
        assert result.status == CompatibilityStatus.INCOMPATIBLE

    def test_copyleft_proprietary_incompatible(self):
        result = check_compatibility("GPL-3.0", "Proprietary")
        # GPL → Proprietary is either incompatible or conditional with anti-circumvention
        assert result.status in (CompatibilityStatus.INCOMPATIBLE, CompatibilityStatus.CONDITIONAL)
        assert result.anti_circumvention_flag is True


class TestConditionalPairs:
    """Tests for conditionally compatible license pairs."""

    def test_lgpl21_apache_conditional(self):
        result = check_compatibility("LGPL-2.1", "Apache-2.0")
        assert result.status == CompatibilityStatus.CONDITIONAL
        assert len(result.conditions) > 0

    def test_permissive_copyleft_conditional(self):
        result = check_compatibility("MIT", "GPL-3.0")
        # MIT -> GPL is conditional because including GPL code may impose obligations
        assert result.status in (CompatibilityStatus.CONDITIONAL, CompatibilityStatus.COMPATIBLE)


class TestQuotaSystem:
    """Tests for tariff rate quota functionality."""

    def test_bsd4_clause_quota(self):
        result = check_compatibility("BSD-4-Clause", "MIT")
        # BSD-4-Clause has attribution quota of 3
        assert result.quota_remaining >= 0

    def test_quota_exhausted(self):
        result = check_compatibility("BSD-4-Clause", "MIT", current_quota_usage=3)
        # After 3 uses, quota should be exhausted
        assert result.status in (CompatibilityStatus.INCOMPATIBLE, CompatibilityStatus.CONDITIONAL)


class TestAntiCircumvention:
    """Tests for anti-circumvention detection."""

    def test_no_circumvention_for_normal(self):
        result = check_compatibility("MIT", "Apache-2.0")
        assert result.anti_circumvention_flag is False

    def test_circumvention_detection(self):
        # GPL → Proprietary triggers anti-circumvention
        result = check_compatibility("GPL-3.0", "Proprietary")
        assert result.anti_circumvention_flag is True


class TestCompatibilityResult:
    """Tests for CompatibilityResult data integrity."""

    def test_rules_applied_populated(self):
        result = check_compatibility("MIT", "Apache-2.0")
        assert len(result.rules_applied) > 0

    def test_timestamp_populated(self):
        result = check_compatibility("MIT", "Apache-2.0")
        assert result.timestamp != ""

    def test_from_to_preserved(self):
        result = check_compatibility("MIT", "GPL-3.0")
        assert result.from_license == "MIT"
        assert result.to_license == "GPL-3.0"
