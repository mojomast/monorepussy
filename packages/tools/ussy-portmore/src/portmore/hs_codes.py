"""HS Code taxonomy and lookup for license classification."""
from __future__ import annotations

import json
from pathlib import Path

from portmore.models import HSCode, LicenseFamily


# ── HS Code Database (in-memory) ─────────────────────────────────────────────

_HS_CODES: list[HSCode] = [
    # Chapter 01: Permissive
    HSCode("01", "0101", "010101", "MIT-style (no patent grant)", LicenseFamily.PERMISSIVE),
    HSCode("01", "0101", "010102", "MIT X11 (with sell clause)", LicenseFamily.PERMISSIVE),
    HSCode("01", "0102", "010201", "Apache-style (patent grant + retaliation)", LicenseFamily.PERMISSIVE),
    HSCode("01", "0103", "010301", "BSD-style (no-endorsement clause)", LicenseFamily.PERMISSIVE),
    HSCode("01", "0103", "010302", "BSD-2-Clause", LicenseFamily.PERMISSIVE),
    HSCode("01", "0103", "010303", "BSD-3-Clause", LicenseFamily.PERMISSIVE),
    HSCode("01", "0104", "010401", "ISC-style", LicenseFamily.PERMISSIVE),
    HSCode("01", "0105", "010501", "Unlicense-style", LicenseFamily.PERMISSIVE),
    HSCode("01", "0106", "010601", "Zlib-style", LicenseFamily.PERMISSIVE),
    # Chapter 02: Weak Copyleft
    HSCode("02", "0201", "020101", "LGPL-2.0-style", LicenseFamily.WEAK_COPYLEFT),
    HSCode("02", "0201", "020102", "LGPL-2.1-style", LicenseFamily.WEAK_COPYLEFT),
    HSCode("02", "0202", "020201", "LGPL-3.0-style", LicenseFamily.WEAK_COPYLEFT),
    HSCode("02", "0203", "020301", "MPL-2.0-style (file-level copyleft)", LicenseFamily.WEAK_COPYLEFT),
    HSCode("02", "0204", "020401", "CDDL-style (file-level copyleft)", LicenseFamily.WEAK_COPYLEFT),
    HSCode("02", "0205", "020501", "EPL-style (weak copyleft + patent)", LicenseFamily.WEAK_COPYLEFT),
    # Chapter 03: Strong Copyleft
    HSCode("03", "0301", "030101", "GPL-2.0-style", LicenseFamily.STRONG_COPYLEFT),
    HSCode("03", "0301", "030102", "GPL-2.0-only", LicenseFamily.STRONG_COPYLEFT),
    HSCode("03", "0302", "030201", "GPL-3.0-style", LicenseFamily.STRONG_COPYLEFT),
    HSCode("03", "0302", "030202", "GPL-3.0-only", LicenseFamily.STRONG_COPYLEFT),
    HSCode("03", "0303", "030301", "AGPL-3.0-style (network copyleft)", LicenseFamily.STRONG_COPYLEFT),
    HSCode("03", "0304", "030401", "EUPL-style (strong copyleft, EU)", LicenseFamily.STRONG_COPYLEFT),
    # Chapter 04: Proprietary
    HSCode("04", "0401", "040101", "Proprietary closed-source", LicenseFamily.PROPRIETARY),
    HSCode("04", "0402", "040201", "Proprietary with source-available", LicenseFamily.PROPRIETARY),
    HSCode("04", "0403", "040301", "Commercial with open-source components", LicenseFamily.PROPRIETARY),
    HSCode("04", "0404", "040401", "BSL (Business Source License)", LicenseFamily.PROPRIETARY),
    # Chapter 05: Public Domain / CC0
    HSCode("05", "0501", "050101", "CC0-style (public domain dedication)", LicenseFamily.PUBLIC_DOMAIN),
    HSCode("05", "0502", "050201", "CC-BY-style (attribution only)", LicenseFamily.PUBLIC_DOMAIN),
    HSCode("05", "0503", "050301", "WTFPL-style", LicenseFamily.PUBLIC_DOMAIN),
]

# ── SPDX to HS Code mapping ──────────────────────────────────────────────────

_SPDX_TO_HS: dict[str, str] = {
    "MIT": "010101",
    "MIT-0": "010101",
    "Expat": "010101",
    "X11": "010102",
    "Apache-2.0": "010201",
    "Apache-1.1": "010201",
    "BSD-3-Clause": "010303",
    "BSD-2-Clause": "010302",
    "BSD-4-Clause": "010301",
    "ISC": "010401",
    "Unlicense": "010501",
    "Zlib": "010601",
    "LGPL-2.0": "020101",
    "LGPL-2.0-only": "020101",
    "LGPL-2.0-or-later": "020101",
    "LGPL-2.1": "020102",
    "LGPL-2.1-only": "020102",
    "LGPL-2.1-or-later": "020102",
    "LGPL-3.0": "020201",
    "LGPL-3.0-only": "020201",
    "LGPL-3.0-or-later": "020201",
    "MPL-2.0": "020301",
    "MPL-2.0-no-copyleft-exception": "020301",
    "CDDL-1.0": "020401",
    "CDDL-1.1": "020401",
    "EPL-1.0": "020501",
    "EPL-2.0": "020501",
    "GPL-2.0": "030101",
    "GPL-2.0-only": "030102",
    "GPL-2.0-or-later": "030101",
    "GPL-3.0": "030201",
    "GPL-3.0-only": "030202",
    "GPL-3.0-or-later": "030201",
    "AGPL-3.0": "030301",
    "AGPL-3.0-only": "030301",
    "AGPL-3.0-or-later": "030301",
    "EUPL-1.2": "030401",
    "CC0-1.0": "050101",
    "CC-BY-4.0": "050201",
    "CC-BY-3.0": "050201",
    "WTFPL": "050301",
}


def lookup_hs_code(spdx_id: str) -> HSCode | None:
    """Look up the HS code for an SPDX license identifier."""
    subheading = _SPDX_TO_HS.get(spdx_id)
    if subheading is None:
        return None
    for code in _HS_CODES:
        if code.subheading == subheading:
            return code
    return None


def get_family(spdx_id: str) -> LicenseFamily | None:
    """Get the license family for an SPDX identifier."""
    hs = lookup_hs_code(spdx_id)
    if hs is not None:
        return hs.family
    return None


def get_family_for_chapter(chapter: str) -> LicenseFamily | None:
    """Get the LicenseFamily enum for a chapter code."""
    for fam in LicenseFamily:
        if fam.value == chapter:
            return fam
    return None


def all_hs_codes() -> list[HSCode]:
    """Return all registered HS codes."""
    return list(_HS_CODES)


def all_spdx_ids() -> list[str]:
    """Return all registered SPDX identifiers."""
    return list(_SPDX_TO_HS.keys())


def classify_by_family(spdx_ids: list[str]) -> dict[LicenseFamily, list[str]]:
    """Group SPDX IDs by license family."""
    result: dict[LicenseFamily, list[str]] = {}
    for spdx_id in spdx_ids:
        fam = get_family(spdx_id)
        if fam is not None:
            result.setdefault(fam, []).append(spdx_id)
    return result
