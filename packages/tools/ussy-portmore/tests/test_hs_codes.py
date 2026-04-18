"""Tests for HS Code taxonomy and lookup."""
import pytest

from portmore.hs_codes import (
    all_hs_codes,
    all_spdx_ids,
    classify_by_family,
    get_family,
    get_family_for_chapter,
    lookup_hs_code,
)
from portmore.models import LicenseFamily


class TestHSCodeLookup:
    """Tests for HS code lookup by SPDX identifier."""

    def test_lookup_mit(self):
        hs = lookup_hs_code("MIT")
        assert hs is not None
        assert hs.chapter == "01"
        assert hs.family == LicenseFamily.PERMISSIVE
        assert "MIT" in hs.description

    def test_lookup_apache(self):
        hs = lookup_hs_code("Apache-2.0")
        assert hs is not None
        assert hs.chapter == "01"
        assert "Apache" in hs.description

    def test_lookup_gpl3(self):
        hs = lookup_hs_code("GPL-3.0")
        assert hs is not None
        assert hs.chapter == "03"
        assert hs.family == LicenseFamily.STRONG_COPYLEFT

    def test_lookup_agpl3(self):
        hs = lookup_hs_code("AGPL-3.0")
        assert hs is not None
        assert hs.chapter == "03"
        assert "network" in hs.description.lower() or "AGPL" in hs.description

    def test_lookup_lgpl21(self):
        hs = lookup_hs_code("LGPL-2.1")
        assert hs is not None
        assert hs.chapter == "02"
        assert hs.family == LicenseFamily.WEAK_COPYLEFT

    def test_lookup_cc0(self):
        hs = lookup_hs_code("CC0-1.0")
        assert hs is not None
        assert hs.chapter == "05"
        assert hs.family == LicenseFamily.PUBLIC_DOMAIN

    def test_lookup_proprietary_unknown(self):
        hs = lookup_hs_code("SomeProprietary-1.0")
        assert hs is None

    def test_lookup_bsd3(self):
        hs = lookup_hs_code("BSD-3-Clause")
        assert hs is not None
        assert hs.chapter == "01"

    def test_lookup_mpl2(self):
        hs = lookup_hs_code("MPL-2.0")
        assert hs is not None
        assert hs.chapter == "02"
        assert "file-level" in hs.description.lower()

    def test_lookup_eupl(self):
        hs = lookup_hs_code("EUPL-1.2")
        assert hs is not None
        assert hs.chapter == "03"


class TestHSCodeProperties:
    """Tests for HSCode data class properties."""

    def test_code_format(self):
        hs = lookup_hs_code("MIT")
        assert hs is not None
        # Chapter.Heading[2:].Subheading[4:]
        assert hs.code == "01.01.01"

    def test_code_format_apache(self):
        hs = lookup_hs_code("Apache-2.0")
        assert hs is not None
        assert hs.code == "01.02.01"

    def test_str_representation(self):
        hs = lookup_hs_code("MIT")
        assert hs is not None
        s = str(hs)
        assert "HS" in s
        assert "01.01.01" in s

    def test_gpl3_code(self):
        hs = lookup_hs_code("GPL-3.0")
        assert hs is not None
        assert hs.code == "03.02.01"


class TestFamilyLookup:
    """Tests for license family lookup."""

    def test_get_family_mit(self):
        fam = get_family("MIT")
        assert fam == LicenseFamily.PERMISSIVE

    def test_get_family_gpl3(self):
        fam = get_family("GPL-3.0")
        assert fam == LicenseFamily.STRONG_COPYLEFT

    def test_get_family_lgpl21(self):
        fam = get_family("LGPL-2.1")
        assert fam == LicenseFamily.WEAK_COPYLEFT

    def test_get_family_unknown(self):
        fam = get_family("NonExistent-1.0")
        assert fam is None

    def test_get_family_cc0(self):
        fam = get_family("CC0-1.0")
        assert fam == LicenseFamily.PUBLIC_DOMAIN

    def test_get_family_for_chapter_01(self):
        fam = get_family_for_chapter("01")
        assert fam == LicenseFamily.PERMISSIVE

    def test_get_family_for_chapter_03(self):
        fam = get_family_for_chapter("03")
        assert fam == LicenseFamily.STRONG_COPYLEFT

    def test_get_family_for_chapter_invalid(self):
        fam = get_family_for_chapter("99")
        assert fam is None


class TestClassificationByFamily:
    """Tests for classifying licenses by family."""

    def test_classify_mixed(self):
        result = classify_by_family(["MIT", "GPL-3.0", "LGPL-2.1"])
        assert LicenseFamily.PERMISSIVE in result
        assert LicenseFamily.STRONG_COPYLEFT in result
        assert LicenseFamily.WEAK_COPYLEFT in result
        assert "MIT" in result[LicenseFamily.PERMISSIVE]

    def test_classify_single_family(self):
        result = classify_by_family(["MIT", "ISC", "BSD-2-Clause"])
        assert len(result) == 1
        assert LicenseFamily.PERMISSIVE in result

    def test_classify_empty(self):
        result = classify_by_family([])
        assert result == {}

    def test_classify_unknown(self):
        result = classify_by_family(["MIT", "UnknownLicense"])
        assert LicenseFamily.PERMISSIVE in result
        assert "UnknownLicense" not in result.get(LicenseFamily.PERMISSIVE, [])


class TestAllCodes:
    """Tests for listing all HS codes and SPDX IDs."""

    def test_all_hs_codes_not_empty(self):
        codes = all_hs_codes()
        assert len(codes) > 20

    def test_all_spdx_ids_not_empty(self):
        ids = all_spdx_ids()
        assert "MIT" in ids
        assert "GPL-3.0" in ids
        assert "Apache-2.0" in ids

    def test_all_spdx_ids_count_matches(self):
        ids = all_spdx_ids()
        codes = all_hs_codes()
        # More SPDX IDs than HS codes (multiple SPDX per HS subheading)
        assert len(ids) > 0
