"""Preferential Trade Agreements — License Compatibility Exceptions."""
from __future__ import annotations

from portmore.models import (
    CompatibilityResult,
    CompatibilityRule,
    CompatibilityStatus,
)
from portmore.hs_codes import get_family, LicenseFamily


# ── License Zones ─────────────────────────────────────────────────────────────

PERMISSIVE_ZONE = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC",
                   "X11", "Expat", "Unlicense", "Zlib", "BSD-4-Clause"}
COPYLEFT_ZONE = {"GPL-2.0", "GPL-2.0-only", "GPL-2.0-or-later",
                 "GPL-3.0", "GPL-3.0-only", "GPL-3.0-or-later",
                 "AGPL-3.0", "AGPL-3.0-only", "AGPL-3.0-or-later"}
WEAK_COPYLEFT_ZONE = {"LGPL-2.0", "LGPL-2.0-only", "LGPL-2.1", "LGPL-2.1-only",
                      "LGPL-3.0", "LGPL-3.0-only", "MPL-2.0", "CDDL-1.0",
                      "EPL-1.0", "EPL-2.0"}
PUBLIC_DOMAIN_ZONE = {"CC0-1.0", "WTFPL", "Unlicense"}


def _get_zone(license_id: str) -> str:
    """Determine the license zone for a given license."""
    if license_id in PERMISSIVE_ZONE:
        return "permissive"
    if license_id in COPYLEFT_ZONE:
        return "copyleft"
    if license_id in WEAK_COPYLEFT_ZONE:
        return "weak_copyleft"
    if license_id in PUBLIC_DOMAIN_ZONE:
        return "public_domain"
    fam = get_family(license_id)
    if fam == LicenseFamily.PROPRIETARY:
        return "proprietary"
    return "unknown"


# ── Compatibility Rules Database ─────────────────────────────────────────────

_COMPATIBILITY_RULES: list[CompatibilityRule] = [
    # Negative list — always incompatible
    CompatibilityRule("AGPL-3.0", "Proprietary", CompatibilityStatus.INCOMPATIBLE,
                      zone_from="copyleft", zone_to="proprietary"),
    CompatibilityRule("AGPL-3.0-only", "Proprietary", CompatibilityStatus.INCOMPATIBLE,
                      zone_from="copyleft", zone_to="proprietary"),
    CompatibilityRule("GPL-2.0-only", "Apache-2.0", CompatibilityStatus.INCOMPATIBLE,
                      "patent clause conflict", zone_from="copyleft", zone_to="permissive"),
    # Conditional compatibility
    CompatibilityRule("LGPL-2.1", "Apache-2.0", CompatibilityStatus.CONDITIONAL,
                      "dynamic_link", zone_from="weak_copyleft", zone_to="permissive"),
    CompatibilityRule("LGPL-3.0", "Apache-2.0", CompatibilityStatus.CONDITIONAL,
                      "dynamic_link", zone_from="weak_copyleft", zone_to="permissive"),
    CompatibilityRule("MPL-2.0", "GPL-2.0", CompatibilityStatus.CONDITIONAL,
                      "file_level_scope", zone_from="weak_copyleft", zone_to="copyleft"),
    # Tariff Rate Quotas
    CompatibilityRule("BSD-4-Clause", "MIT", CompatibilityStatus.CONDITIONAL,
                      "attribution_quota:3", quota_limit=3,
                      zone_from="permissive", zone_to="permissive"),
    # Intra-zone — compatible
    CompatibilityRule("MIT", "Apache-2.0", CompatibilityStatus.COMPATIBLE,
                      zone_from="permissive", zone_to="permissive"),
    CompatibilityRule("MIT", "BSD-2-Clause", CompatibilityStatus.COMPATIBLE,
                      zone_from="permissive", zone_to="permissive"),
    CompatibilityRule("MIT", "BSD-3-Clause", CompatibilityStatus.COMPATIBLE,
                      zone_from="permissive", zone_to="permissive"),
    CompatibilityRule("MIT", "ISC", CompatibilityStatus.COMPATIBLE,
                      zone_from="permissive", zone_to="permissive"),
    CompatibilityRule("Apache-2.0", "BSD-3-Clause", CompatibilityStatus.COMPATIBLE,
                      zone_from="permissive", zone_to="permissive"),
    CompatibilityRule("GPL-3.0", "MIT", CompatibilityStatus.COMPATIBLE,
                      "copyleft_governs", zone_from="copyleft", zone_to="permissive"),
    CompatibilityRule("GPL-2.0", "MIT", CompatibilityStatus.COMPATIBLE,
                      "copyleft_governs", zone_from="copyleft", zone_to="permissive"),
    CompatibilityRule("GPL-3.0", "Apache-2.0", CompatibilityStatus.COMPATIBLE,
                      "copyleft_governs", zone_from="copyleft", zone_to="permissive"),
    CompatibilityRule("CC0-1.0", "MIT", CompatibilityStatus.COMPATIBLE,
                      zone_from="public_domain", zone_to="permissive"),
]

# ── Anti-circumvention detection ──────────────────────────────────────────────

_CIRCUMVENTION_PATTERNS: list[dict[str, str]] = [
    {"from": "GPL", "intermediate": "socket_api", "to": "Proprietary"},
    {"from": "GPL", "intermediate": "rpc_shim", "to": "Proprietary"},
    {"from": "AGPL", "intermediate": "microservice_wrapper", "to": "Proprietary"},
]


def check_compatibility(
    from_license: str,
    to_license: str,
    usage_type: str = "static",
    current_quota_usage: int = 0,
) -> CompatibilityResult:
    """Check license compatibility with PTA-style exceptions.

    Applies:
    1. Direct rule lookup
    2. Zone-based cumulation
    3. Tariff rate quotas
    4. Anti-circumvention detection
    """
    conditions: list[str] = []
    rules_applied: list[str] = []
    quota_remaining = 0
    anti_circumvention = False

    # Step 1: Check negative list (exact match)
    for rule in _COMPATIBILITY_RULES:
        if rule.from_license == from_license and rule.to_license == to_license:
            rules_applied.append(f"rule:{rule.from_license}->{rule.to_license}")
            if rule.status == CompatibilityStatus.INCOMPATIBLE:
                return CompatibilityResult(
                    from_license=from_license,
                    to_license=to_license,
                    status=CompatibilityStatus.INCOMPATIBLE,
                    conditions=[],
                    rules_applied=rules_applied,
                )
            if rule.status == CompatibilityStatus.CONDITIONAL:
                conditions.append(rule.condition)
                if rule.quota_limit > 0:
                    quota_remaining = max(0, rule.quota_limit - current_quota_usage)
                    if quota_remaining <= 0:
                        return CompatibilityResult(
                            from_license=from_license,
                            to_license=to_license,
                            status=CompatibilityStatus.INCOMPATIBLE,
                            conditions=[f"quota exhausted: {rule.quota_limit}"],
                            quota_remaining=0,
                            rules_applied=rules_applied,
                        )
            if rule.status == CompatibilityStatus.COMPATIBLE:
                if rule.condition:
                    conditions.append(rule.condition)
                return CompatibilityResult(
                    from_license=from_license,
                    to_license=to_license,
                    status=CompatibilityStatus.COMPATIBLE,
                    conditions=conditions,
                    quota_remaining=quota_remaining,
                    rules_applied=rules_applied,
                )

    # Step 2: Zone-based analysis
    from_zone = _get_zone(from_license)
    to_zone = _get_zone(to_license)
    rules_applied.append(f"zone:{from_zone}->{to_zone}")

    # Same zone = cumulation applies (free combination)
    if from_zone == to_zone and from_zone != "unknown" and from_zone != "proprietary":
        return CompatibilityResult(
            from_license=from_license,
            to_license=to_license,
            status=CompatibilityStatus.COMPATIBLE,
            conditions=["cumulation: same zone"],
            rules_applied=rules_applied,
        )

    # Cross-zone rules
    if from_zone == "public_domain" and to_zone in ("permissive", "weak_copyleft", "copyleft"):
        return CompatibilityResult(
            from_license=from_license,
            to_license=to_license,
            status=CompatibilityStatus.COMPATIBLE,
            conditions=["public domain is compatible with all"],
            rules_applied=rules_applied,
        )

    if from_zone == "permissive" and to_zone in ("permissive", "public_domain"):
        return CompatibilityResult(
            from_license=from_license,
            to_license=to_license,
            status=CompatibilityStatus.COMPATIBLE,
            conditions=["permissive zone cumulation"],
            rules_applied=rules_applied,
        )

    if from_zone == "copyleft" and to_zone == "permissive":
        return CompatibilityResult(
            from_license=from_license,
            to_license=to_license,
            status=CompatibilityStatus.COMPATIBLE,
            conditions=["copyleft_governs: permissive code can be incorporated but copyleft obligations apply"],
            rules_applied=rules_applied,
        )

    if from_zone == "permissive" and to_zone == "copyleft":
        return CompatibilityResult(
            from_license=from_license,
            to_license=to_license,
            status=CompatibilityStatus.CONDITIONAL,
            conditions=["copyleft_inheritance: including copyleft code may impose obligations on your work"],
            rules_applied=rules_applied,
        )

    if from_zone in ("copyleft", "weak_copyleft") and to_zone == "proprietary":
        return CompatibilityResult(
            from_license=from_license,
            to_license=to_license,
            status=CompatibilityStatus.INCOMPATIBLE,
            conditions=["copyleft cannot be combined with proprietary"],
            rules_applied=rules_applied,
        )

    if from_zone == "proprietary":
        return CompatibilityResult(
            from_license=from_license,
            to_license=to_license,
            status=CompatibilityStatus.INCOMPATIBLE,
            conditions=["proprietary licenses restrict combination"],
            rules_applied=rules_applied,
        )

    # Step 3: Anti-circumvention check
    for pattern in _CIRCUMVENTION_PATTERNS:
        if from_license.startswith(pattern["from"]) and to_license == pattern["to"]:
            anti_circumvention = True
            conditions.append(f"anti_circumvention: potential transshipment via {pattern['intermediate']}")
            rules_applied.append(f"anti_circumvention:{pattern['intermediate']}")

    # Default: conditional with warning
    return CompatibilityResult(
        from_license=from_license,
        to_license=to_license,
        status=CompatibilityStatus.CONDITIONAL,
        conditions=conditions or ["unknown compatibility — manual review recommended"],
        anti_circumvention_flag=anti_circumvention,
        quota_remaining=quota_remaining,
        rules_applied=rules_applied,
    )


def get_zone(license_id: str) -> str:
    """Public API to get the zone for a license."""
    return _get_zone(license_id)
