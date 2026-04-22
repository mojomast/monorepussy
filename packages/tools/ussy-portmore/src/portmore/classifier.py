"""General Interpretative Rules (GIRs) for multi-license resolution."""
from __future__ import annotations

from portmore.models import (
    ClassifiedLicense,
    GIRResult,
    LicenseFamily,
    MultiLicenseResolution,
)
from portmore.hs_codes import classify_by_family, get_family, lookup_hs_code


# ── Restrictiveness ordering ──────────────────────────────────────────────────

_FAMILY_RESTRICTIVENESS: dict[LicenseFamily, int] = {
    LicenseFamily.PUBLIC_DOMAIN: 0,
    LicenseFamily.PERMISSIVE: 1,
    LicenseFamily.WEAK_COPYLEFT: 2,
    LicenseFamily.STRONG_COPYLEFT: 3,
    LicenseFamily.PROPRIETARY: 4,
}

# Licenses with specificity bonuses (more specific description wins in GIR 3a)
_SPECIFICITY_BONUS: dict[str, int] = {
    "Apache-2.0": 1,       # patent grant + retaliation clause
    "GPL-3.0": 1,          # explicit patent grant
    "AGPL-3.0": 2,         # network copyleft provision
    "MPL-2.0": 1,          # file-level copyleft scope
    "LGPL-2.1": 1,         # dynamic linking exception
    "LGPL-3.0": 1,         # dynamic linking exception
    "GPL-2.0-only": 1,     # only qualifier adds specificity
    "GPL-3.0-only": 1,     # only qualifier adds specificity
}


def _specificity_score(spdx_id: str) -> int:
    """Compute specificity score for GIR 3a comparison."""
    base = 0
    # WITH clause adds specificity
    if "WITH" in spdx_id.upper():
        base += 2
    # Known specificity bonuses
    base += _SPECIFICITY_BONUS.get(spdx_id, 0)
    # Longer identifiers tend to be more specific
    base += len(spdx_id) // 10
    return base


def _restrictiveness(spdx_id: str) -> int:
    """Get restrictiveness score for a license."""
    fam = get_family(spdx_id)
    if fam is None:
        return 0
    return _FAMILY_RESTRICTIVENESS.get(fam, 0)


# ── GIR Implementation ───────────────────────────────────────────────────────

def apply_gir1(licenses: list[str], project_license: str | None = None) -> GIRResult:
    """GIR 1: Classify by headings and section notes FIRST.

    The license in the project's LICENSE file governs,
    not incidental licenses in vendored code.
    """
    if project_license and project_license in licenses:
        return GIRResult(
            rule="GIR 1",
            description="Classify by headings and section notes first",
            applied=True,
            outcome=f"Project LICENSE file governs: {project_license}",
        )
    return GIRResult(
        rule="GIR 1",
        description="Classify by headings and section notes first",
        applied=False,
        outcome="No explicit project license found or not in detected list",
    )


def apply_gir2a(licenses: list[str], fork_ratio: float = 0.0) -> GIRResult:
    """GIR 2a: Incomplete/unfinished works classified by essential character.

    A fork with >= 90% original code keeps the original's license.
    """
    if len(licenses) <= 1:
        return GIRResult(
            rule="GIR 2a",
            description="Incomplete/unfinished works: essential character",
            applied=False,
            outcome="Single license — no fork analysis needed",
        )

    if fork_ratio >= 0.90:
        # Fork is mostly original code → original license governs
        return GIRResult(
            rule="GIR 2a",
            description="Incomplete/unfinished works: essential character",
            applied=True,
            outcome=f"Fork retains {fork_ratio:.0%} original code — original license governs",
        )

    return GIRResult(
        rule="GIR 2a",
        description="Incomplete/unfinished works: essential character",
        applied=False,
        outcome=f"Fork has {fork_ratio:.0%} original code — substantial transformation may apply",
    )


def apply_gir2b(licenses: list[str], core_license: str | None = None) -> GIRResult:
    """GIR 2b: Mixtures classified by essential-character component.

    The component providing core functionality sets the license.
    """
    if core_license and core_license in licenses:
        return GIRResult(
            rule="GIR 2b",
            description="Mixtures: essential-character component governs",
            applied=True,
            outcome=f"Core functionality license governs: {core_license}",
        )
    return GIRResult(
        rule="GIR 2b",
        description="Mixtures: essential-character component governs",
        applied=False,
        outcome="No core component identified",
    )


def apply_gir3a(licenses: list[str]) -> GIRResult:
    """GIR 3a: Specific description prevails over general.

    "Apache-2.0 WITH Classpath-exception" > "GPL-2.0" in specificity.
    """
    if len(licenses) <= 1:
        return GIRResult(
            rule="GIR 3a",
            description="Specific description prevails over general",
            applied=False,
            outcome="Single license — no specificity comparison needed",
        )

    scores = {lic: _specificity_score(lic) for lic in licenses}
    max_score = max(scores.values())
    most_specific = [lic for lic, s in scores.items() if s == max_score]

    if len(most_specific) == 1:
        return GIRResult(
            rule="GIR 3a",
            description="Specific description prevails over general",
            applied=True,
            outcome=f"Most specific: {most_specific[0]} (score: {max_score})",
        )

    return GIRResult(
        rule="GIR 3a",
        description="Specific description prevails over general",
        applied=False,
        outcome=f"Tie in specificity among: {', '.join(most_specific)}",
    )


def apply_gir3b(licenses: list[str]) -> GIRResult:
    """GIR 3b: Essential character determines mixture classification.

    The component providing core functionality sets the license.
    If not determinable by other means, use family restrictiveness.
    """
    if len(licenses) <= 1:
        return GIRResult(
            rule="GIR 3b",
            description="Essential character determines mixture classification",
            applied=False,
            outcome="Single license — no essential character analysis needed",
        )

    families = classify_by_family(licenses)
    if len(families) == 1:
        # All same family — essential character doesn't differentiate
        return GIRResult(
            rule="GIR 3b",
            description="Essential character determines mixture classification",
            applied=False,
            outcome="All licenses in same family — no differentiation",
        )

    # Most restrictive family provides essential character for copyleft analysis
    most_restrictive_family = max(families.keys(), key=lambda f: _FAMILY_RESTRICTIVENESS.get(f, 0))
    dominant_licenses = families[most_restrictive_family]

    return GIRResult(
        rule="GIR 3b",
        description="Essential character determines mixture classification",
        applied=True,
        outcome=f"Dominant family {most_restrictive_family.value}: {', '.join(dominant_licenses)}",
    )


def apply_gir3c(licenses: list[str]) -> GIRResult:
    """GIR 3c: Tiebreaker — most restrictive governs (last-heading analog)."""
    if len(licenses) <= 1:
        return GIRResult(
            rule="GIR 3c",
            description="Tiebreaker: most restrictive governs",
            applied=False,
            outcome="Single license — no tiebreaker needed",
        )

    most_restrictive = max(licenses, key=lambda lic: (_restrictiveness(lic), _specificity_score(lic)))
    return GIRResult(
        rule="GIR 3c",
        description="Tiebreaker: most restrictive governs",
        applied=True,
        outcome=f"Most restrictive governs: {most_restrictive}",
    )


# ── Sequential GIR Application ───────────────────────────────────────────────

def classify_licenses(
    licenses: list[str],
    project_license: str | None = None,
    core_license: str | None = None,
    fork_ratio: float = 0.0,
) -> MultiLicenseResolution:
    """Apply GIRs sequentially to determine governing license.

    GIRs are applied in order 1 → 2a → 2b → 3a → 3b → 3c.
    The first rule that decisively resolves classification is used.
    """
    if not licenses:
        return MultiLicenseResolution(
            licenses_found=[],
            gir_results=[],
            governing_license="UNKNOWN",
            reasoning_chain=["No licenses detected"],
        )

    if len(licenses) == 1:
        hs = lookup_hs_code(licenses[0])
        return MultiLicenseResolution(
            licenses_found=licenses,
            gir_results=[GIRResult("GIR 1", "Single license", True, f"Sole license: {licenses[0]}")],
            governing_license=licenses[0],
            governing_hs_code=hs.code if hs else "",
            reasoning_chain=[f"Single license detected: {licenses[0]}"],
        )

    gir_results: list[GIRResult] = []
    reasoning_chain: list[str] = []
    governing = licenses[0]  # fallback
    governing_hs = ""

    # GIR 1
    r1 = apply_gir1(licenses, project_license)
    gir_results.append(r1)
    if r1.applied:
        governing = project_license  # type: ignore[assignment]
        reasoning_chain.append(f"GIR 1 applied: {r1.outcome}")
        hs = lookup_hs_code(governing)
        governing_hs = hs.code if hs else ""
        return MultiLicenseResolution(
            licenses_found=licenses,
            gir_results=gir_results,
            governing_license=governing,
            governing_hs_code=governing_hs,
            reasoning_chain=reasoning_chain,
        )

    # GIR 2a
    r2a = apply_gir2a(licenses, fork_ratio)
    gir_results.append(r2a)
    if r2a.applied:
        # Fork keeps original license — the first one in the list (assumed original)
        governing = licenses[0]
        reasoning_chain.append(f"GIR 2a applied: {r2a.outcome}")
        hs = lookup_hs_code(governing)
        governing_hs = hs.code if hs else ""
        return MultiLicenseResolution(
            licenses_found=licenses,
            gir_results=gir_results,
            governing_license=governing,
            governing_hs_code=governing_hs,
            reasoning_chain=reasoning_chain,
        )

    # GIR 2b
    r2b = apply_gir2b(licenses, core_license)
    gir_results.append(r2b)
    if r2b.applied:
        governing = core_license  # type: ignore[assignment]
        reasoning_chain.append(f"GIR 2b applied: {r2b.outcome}")
        hs = lookup_hs_code(governing)
        governing_hs = hs.code if hs else ""
        return MultiLicenseResolution(
            licenses_found=licenses,
            gir_results=gir_results,
            governing_license=governing,
            governing_hs_code=governing_hs,
            reasoning_chain=reasoning_chain,
        )

    # GIR 3a
    r3a = apply_gir3a(licenses)
    gir_results.append(r3a)
    if r3a.applied:
        # Extract the most specific license from the outcome
        governing = _extract_license_from_outcome(r3a.outcome, licenses)
        reasoning_chain.append(f"GIR 3a applied: {r3a.outcome}")
        hs = lookup_hs_code(governing)
        governing_hs = hs.code if hs else ""
        return MultiLicenseResolution(
            licenses_found=licenses,
            gir_results=gir_results,
            governing_license=governing,
            governing_hs_code=governing_hs,
            reasoning_chain=reasoning_chain,
        )

    # GIR 3b
    r3b = apply_gir3b(licenses)
    gir_results.append(r3b)
    if r3b.applied:
        reasoning_chain.append(f"GIR 3b applied: {r3b.outcome}")
        # Use the most restrictive from the dominant family
        families = classify_by_family(licenses)
        most_restrictive_family = max(families.keys(), key=lambda f: _FAMILY_RESTRICTIVENESS.get(f, 0))
        governing = families[most_restrictive_family][0]
        hs = lookup_hs_code(governing)
        governing_hs = hs.code if hs else ""
        return MultiLicenseResolution(
            licenses_found=licenses,
            gir_results=gir_results,
            governing_license=governing,
            governing_hs_code=governing_hs,
            reasoning_chain=reasoning_chain,
        )

    # GIR 3c — final tiebreaker
    r3c = apply_gir3c(licenses)
    gir_results.append(r3c)
    governing = _extract_license_from_outcome(r3c.outcome, licenses)
    reasoning_chain.append(f"GIR 3c applied: {r3c.outcome}")
    hs = lookup_hs_code(governing)
    governing_hs = hs.code if hs else ""

    return MultiLicenseResolution(
        licenses_found=licenses,
        gir_results=gir_results,
        governing_license=governing,
        governing_hs_code=governing_hs,
        reasoning_chain=reasoning_chain,
    )


def _extract_license_from_outcome(outcome: str, candidates: list[str]) -> str:
    """Extract the governing license name from a GIR outcome string."""
    for lic in candidates:
        if lic in outcome:
            return lic
    # Fallback: return most restrictive
    return max(candidates, key=lambda lic: (_restrictiveness(lic), _specificity_score(lic)))
