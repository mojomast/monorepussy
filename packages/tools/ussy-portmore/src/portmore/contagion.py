"""Anti-Dumping/CVD — Copyleft Contagion Containment."""
from __future__ import annotations

from portmore.models import (
    ContagionAssessment,
    InjuryIndicator,
)
from portmore.hs_codes import get_family, LicenseFamily


# ── Obligation weights for dumping margin ─────────────────────────────────────

_RIGHTS_GRANTED: dict[str, float] = {
    "MIT": 100.0,
    "BSD-2-Clause": 100.0,
    "BSD-3-Clause": 95.0,
    "BSD-4-Clause": 85.0,
    "Apache-2.0": 90.0,
    "ISC": 100.0,
    "Unlicense": 100.0,
    "Zlib": 100.0,
    "LGPL-2.0": 60.0,
    "LGPL-2.1": 60.0,
    "LGPL-3.0": 55.0,
    "MPL-2.0": 65.0,
    "GPL-2.0": 30.0,
    "GPL-2.0-only": 25.0,
    "GPL-3.0": 20.0,
    "GPL-3.0-only": 15.0,
    "AGPL-3.0": 10.0,
    "AGPL-3.0-only": 5.0,
    "Proprietary": 0.0,
    "CC0-1.0": 100.0,
}

_OBLIGATIONS_SURRENDERED: dict[str, float] = {
    "MIT": 5.0,
    "BSD-2-Clause": 5.0,
    "BSD-3-Clause": 10.0,
    "BSD-4-Clause": 25.0,
    "Apache-2.0": 20.0,
    "ISC": 5.0,
    "Unlicense": 0.0,
    "Zlib": 5.0,
    "LGPL-2.0": 50.0,
    "LGPL-2.1": 50.0,
    "LGPL-3.0": 55.0,
    "MPL-2.0": 45.0,
    "GPL-2.0": 80.0,
    "GPL-2.0-only": 85.0,
    "GPL-3.0": 90.0,
    "GPL-3.0-only": 95.0,
    "AGPL-3.0": 95.0,
    "AGPL-3.0-only": 100.0,
    "Proprietary": 100.0,
    "CC0-1.0": 0.0,
}


def compute_dumping_margin(license_id: str) -> float:
    """Compute dumping margin.

    DM = Rights_granted_by_license - Rights_surrendered_by_obligations

    Negative DM = "dumping" (you surrender more than you receive).
    """
    rights = _RIGHTS_GRANTED.get(license_id, 50.0)
    obligations = _OBLIGATIONS_SURRENDERED.get(license_id, 50.0)
    return rights - obligations


def material_injury_test(
    license_id: str,
    lost_licensing_options: bool = False,
    forced_code_disclosure: bool = False,
    competitive_disadvantage: bool = False,
) -> list[InjuryIndicator]:
    """Material Injury Test.

    1. Has the copyleft dependency reduced your licensing options?
    2. Has it forced code disclosure?
    3. Has it created competitive disadvantage?
    """
    indicators: list[InjuryIndicator] = []
    fam = get_family(license_id)

    # Copyleft licenses automatically have potential for injury
    if fam in (LicenseFamily.STRONG_COPYLEFT, LicenseFamily.WEAK_COPYLEFT):
        if lost_licensing_options:
            indicators.append(InjuryIndicator.LOST_LICENSING_OPTIONS)
        if forced_code_disclosure:
            indicators.append(InjuryIndicator.FORCED_CODE_DISCLOSURE)
        if competitive_disadvantage:
            indicators.append(InjuryIndicator.COMPETITIVE_DISADVANTAGE)
        # Auto-detect for strong copyleft
        if fam == LicenseFamily.STRONG_COPYLEFT and not indicators:
            indicators.append(InjuryIndicator.LOST_LICENSING_OPTIONS)

    return indicators


def causal_link_test(
    license_id: str,
    copyleft_code_ratio: float,
    would_obligation_exist_without: bool = False,
) -> bool:
    """Causal Link Test.

    Must prove THIS dependency caused the injury, not other factors.
    Counterfactual: Would the obligation exist without this dependency?
    """
    if would_obligation_exist_without:
        return False  # Obligation exists independently
    fam = get_family(license_id)
    if fam == LicenseFamily.STRONG_COPYLEFT and copyleft_code_ratio > 0:
        return True
    if fam == LicenseFamily.WEAK_COPYLEFT and copyleft_code_ratio > 0.30:
        return True
    return False


def circumvention_threshold_test(
    copyleft_ratio: float,
    threshold: float = 0.60,
) -> bool:
    """60% Circumvention Threshold.

    If a module contains >60% code from copyleft source:
      C_copyleft / C_total > 0.60 → module is within the 'duty order'
    Below 60%: de minimis, obligations don't propagate.
    """
    return copyleft_ratio > threshold


def lesser_duty_remedy(license_id: str, copyleft_ratio: float) -> str:
    """Lesser Duty Rule.

    Compliance remedy = minimum obligation sufficient to resolve violation.
    Not: 'must open-source entire project'
    But: 'must provide source for the GPL-linked module only'
    """
    fam = get_family(license_id)

    if fam == LicenseFamily.STRONG_COPYLEFT:
        if copyleft_ratio > 0.90:
            return "Must provide complete corresponding source code for the linked module"
        elif copyleft_ratio > 0.60:
            return "Must provide source code for the copyleft-linked module only"
        else:
            return "Must provide attribution and notice for copyleft components"
    elif fam == LicenseFamily.WEAK_COPYLEFT:
        if copyleft_ratio > 0.60:
            return "Must provide source for modified weak-copyleft files only"
        else:
            return "Must provide attribution and LGPL notices"
    elif fam == LicenseFamily.PERMISSIVE:
        return "Must provide attribution notices"
    else:
        return "Review compliance obligations with legal counsel"


def scope_ruling(linkage_type: str) -> str:
    """Scope Ruling — does the specific usage pattern fall within copyleft scope?

    Static link: YES (within scope)
    Dynamic link (LGPL): NO (outside scope)
    Socket/API call: Context-dependent (requires ruling)
    Microservice: Usually NO (separate process boundary)
    """
    rulings = {
        "static": "YES — static linking places usage within copyleft scope",
        "dynamic": "NO — dynamic linking falls outside LGPL copyleft scope",
        "socket": "CONTEXT-DEPENDENT — socket/API communication requires specific ruling on functional independence",
        "api": "CONTEXT-DEPENDENT — API calls may or may not create derivative work depending on integration depth",
        "microservice": "USUALLY NO — separate process boundary typically excludes from copyleft scope",
        "plugin": "CONTEXT-DEPENDENT — plugin architecture may create derivative work depending on coupling",
    }
    return rulings.get(linkage_type, "UNKNOWN — requires manual scope determination")


def assess_contagion(
    license_id: str,
    copyleft_ratio: float,
    lost_licensing_options: bool = False,
    forced_code_disclosure: bool = False,
    competitive_disadvantage: bool = False,
    would_obligation_exist_without: bool = False,
    linkage_type: str = "static",
    threshold: float = 0.60,
) -> ContagionAssessment:
    """Full copyleft contagion assessment (anti-dumping analog)."""
    dm = compute_dumping_margin(license_id)
    injury = material_injury_test(license_id, lost_licensing_options,
                                  forced_code_disclosure, competitive_disadvantage)
    causal = causal_link_test(license_id, copyleft_ratio, would_obligation_exist_without)
    within_duty = circumvention_threshold_test(copyleft_ratio, threshold)
    remedy = lesser_duty_remedy(license_id, copyleft_ratio)
    ruling = scope_ruling(linkage_type)

    return ContagionAssessment(
        license_id=license_id,
        dumping_margin=dm,
        copyleft_ratio=copyleft_ratio,
        within_duty_order=within_duty,
        injury_indicators=injury,
        causal_link_established=causal,
        lesser_duty_remedy=remedy,
        scope_ruling=ruling,
        threshold=threshold,
    )
