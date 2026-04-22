"""Customs Valuation — License Compliance Cost Assessment."""
from __future__ import annotations

from ussy_portmore.models import (
    LicenseObligation,
    ValuationHierarchy,
    ValuationMethod,
    ValuationResult,
)
from ussy_portmore.hs_codes import get_family, LicenseFamily


# ── Obligation cost defaults ─────────────────────────────────────────────────

_OBLIGATION_COSTS: dict[str, float] = {
    "source_disclosure": 5000.0,
    "patent_grant": 8000.0,
    "attribution": 100.0,
    "copyleft_inheritance": 15000.0,
    "trademark_restriction": 2000.0,
    "indemnification": 10000.0,
    "installation_info": 500.0,
    "notice_retention": 200.0,
    "changes_disclosure": 3000.0,
}

# ── License obligation profiles ───────────────────────────────────────────────

_LICENSE_OBLIGATIONS: dict[str, list[str]] = {
    "MIT": ["attribution", "notice_retention"],
    "BSD-2-Clause": ["attribution", "notice_retention"],
    "BSD-3-Clause": ["attribution", "notice_retention", "trademark_restriction"],
    "BSD-4-Clause": ["attribution", "notice_retention", "trademark_restriction", "installation_info"],
    "Apache-2.0": ["attribution", "notice_retention", "patent_grant", "changes_disclosure"],
    "ISC": ["attribution", "notice_retention"],
    "Unlicense": [],
    "Zlib": ["attribution", "notice_retention"],
    "LGPL-2.0": ["attribution", "source_disclosure", "copyleft_inheritance", "changes_disclosure"],
    "LGPL-2.1": ["attribution", "source_disclosure", "copyleft_inheritance", "changes_disclosure"],
    "LGPL-3.0": ["attribution", "source_disclosure", "copyleft_inheritance", "changes_disclosure",
                 "patent_grant"],
    "MPL-2.0": ["attribution", "source_disclosure", "copyleft_inheritance", "changes_disclosure"],
    "GPL-2.0": ["attribution", "source_disclosure", "copyleft_inheritance", "changes_disclosure"],
    "GPL-2.0-only": ["attribution", "source_disclosure", "copyleft_inheritance", "changes_disclosure"],
    "GPL-3.0": ["attribution", "source_disclosure", "copyleft_inheritance", "changes_disclosure",
                 "patent_grant", "installation_info"],
    "GPL-3.0-only": ["attribution", "source_disclosure", "copyleft_inheritance", "changes_disclosure",
                      "patent_grant", "installation_info"],
    "AGPL-3.0": ["attribution", "source_disclosure", "copyleft_inheritance", "changes_disclosure",
                 "patent_grant", "installation_info", "indemnification"],
    "CC0-1.0": [],
    "Proprietary": ["indemnification", "trademark_restriction"],
}


def get_obligations(license_id: str) -> list[LicenseObligation]:
    """Get the obligation profile for a license."""
    names = _LICENSE_OBLIGATIONS.get(license_id, ["attribution"])
    return [LicenseObligation(name=n, cost=_OBLIGATION_COSTS.get(n, 0.0)) for n in names]


def method1_transaction_value(license_id: str) -> ValuationResult:
    """Method 1 — Transaction Value (license as stated).

    CV₁ = Σ obligations_i × cost_i
    """
    obligations = get_obligations(license_id)
    value = sum(ob.cost for ob in obligations)
    return ValuationResult(
        method=ValuationMethod.TRANSACTION,
        value=value,
        obligations=obligations,
        reasoning=f"Sum of {len(obligations)} obligations for {license_id}",
    )


def method2_identical_goods(license_id: str, similar_project_costs: list[float] | None = None) -> ValuationResult:
    """Method 2 — Identical Goods (same license in similar projects).

    CV₂ = average compliance cost for same license across N similar projects
    """
    if similar_project_costs:
        avg_cost = sum(similar_project_costs) / len(similar_project_costs)
    else:
        # Fallback: use transaction value as baseline
        m1 = method1_transaction_value(license_id)
        avg_cost = m1.value * 1.05  # 5% estimation margin

    return ValuationResult(
        method=ValuationMethod.IDENTICAL,
        value=avg_cost,
        reasoning=f"Average compliance cost across similar projects for {license_id}",
    )


def method3_similar_goods(license_id: str) -> ValuationResult:
    """Method 3 — Similar Goods (analogous license obligations).

    CV₃ = compliance cost for most similar license type
    """
    m1 = method1_transaction_value(license_id)
    fam = get_family(license_id)

    # Similar license adjustment based on family
    family_multiplier = {
        LicenseFamily.PUBLIC_DOMAIN: 0.8,
        LicenseFamily.PERMISSIVE: 1.0,
        LicenseFamily.WEAK_COPYLEFT: 1.3,
        LicenseFamily.STRONG_COPYLEFT: 1.5,
        LicenseFamily.PROPRIETARY: 1.2,
    }

    multiplier = family_multiplier.get(fam, 1.0) if fam else 1.0
    similar_value = m1.value * multiplier

    return ValuationResult(
        method=ValuationMethod.SIMILAR,
        value=similar_value,
        reasoning=f"Analogous compliance cost for {fam.value if fam else 'unknown'} family",
    )


def method4_deductive(project_value: float, obligation_fraction: float = 0.0,
                      license_id: str = "") -> ValuationResult:
    """Method 4 — Deductive Value (from resale price).

    CV₄ = project_value × obligation_fraction
    """
    if obligation_fraction <= 0 and license_id:
        # Estimate fraction from license family
        fam = get_family(license_id)
        fraction_map = {
            LicenseFamily.PUBLIC_DOMAIN: 0.0,
            LicenseFamily.PERMISSIVE: 0.02,
            LicenseFamily.WEAK_COPYLEFT: 0.15,
            LicenseFamily.STRONG_COPYLEFT: 0.40,
            LicenseFamily.PROPRIETARY: 0.10,
        }
        obligation_fraction = fraction_map.get(fam, 0.05) if fam else 0.05

    value = project_value * obligation_fraction
    return ValuationResult(
        method=ValuationMethod.DEDUCTIVE,
        value=value,
        reasoning=f"Project value ({project_value}) × obligation fraction ({obligation_fraction:.2%})",
    )


def method5_computed(development_cost: float, compliance_overhead: float = 0.0,
                     risk_multiplier: float = 1.0, license_id: str = "") -> ValuationResult:
    """Method 5 — Computed Value (from cost of creation).

    CV₅ = (development_cost + compliance_overhead) × risk_multiplier
    """
    if compliance_overhead <= 0 and license_id:
        m1 = method1_transaction_value(license_id)
        compliance_overhead = m1.value

    value = (development_cost + compliance_overhead) * risk_multiplier
    return ValuationResult(
        method=ValuationMethod.COMPUTED,
        value=value,
        reasoning=f"({development_cost} + {compliance_overhead}) × {risk_multiplier}",
    )


def method6_fallback(results: list[ValuationResult], upper_bound: bool = True) -> ValuationResult:
    """Method 6 — Fall-back (best available).

    CV₆ = max(CV₁...CV₅) if lower-bound, min(CV₁...CV₅) if upper-bound
    """
    if not results:
        return ValuationResult(
            method=ValuationMethod.FALLBACK,
            value=0.0,
            reasoning="No previous valuation results available",
        )

    values = [r.value for r in results]
    value = min(values) if upper_bound else max(values)
    qualifier = "upper" if upper_bound else "lower"

    return ValuationResult(
        method=ValuationMethod.FALLBACK,
        value=value,
        reasoning=f"Fall-back ({qualifier} bound): {'min' if upper_bound else 'max'} of {[round(v, 2) for v in values]}",
    )


def article8_adjustments(
    royalties: float = 0.0,
    assists: float = 0.0,
    resale_proceeds: float = 0.0,
) -> float:
    """Article 8 Adjustments (adds to transaction value).

    + Royalties & license fees paid as condition of sale
    + Assists (tools/infrastructure provided to the developer)
    + Proceeds of subsequent resale accruing to the seller
    """
    return royalties + assists + resale_proceeds


def related_party_test(is_same_org: bool, transaction_value: float,
                       arms_length_value: float | None = None) -> float:
    """Related-Party Test.

    If dependency and dependent are same org (monorepo),
    transaction value may be understated → apply arm's-length test.
    """
    if not is_same_org:
        return 0.0
    if arms_length_value is not None and arms_length_value > transaction_value:
        return arms_length_value - transaction_value
    return 0.0


def compute_valuation_hierarchy(
    license_id: str,
    project_value: float = 0.0,
    development_cost: float = 0.0,
    similar_project_costs: list[float] | None = None,
    obligation_fraction: float = 0.0,
    compliance_overhead: float = 0.0,
    risk_multiplier: float = 1.0,
    article8: dict[str, float] | None = None,
    is_same_org: bool = False,
    arms_length_value: float | None = None,
) -> ValuationHierarchy:
    """Compute the full 6-method sequential valuation hierarchy.

    Methods are applied in order; the first available method with
    sufficient data is preferred.
    """
    results: list[ValuationResult] = []

    # Method 1: Transaction Value
    m1 = method1_transaction_value(license_id)
    results.append(m1)

    # Method 2: Identical Goods
    m2 = method2_identical_goods(license_id, similar_project_costs)
    results.append(m2)

    # Method 3: Similar Goods
    m3 = method3_similar_goods(license_id)
    results.append(m3)

    # Method 4: Deductive Value
    if project_value > 0:
        m4 = method4_deductive(project_value, obligation_fraction, license_id)
        results.append(m4)

    # Method 5: Computed Value
    if development_cost > 0:
        m5 = method5_computed(development_cost, compliance_overhead, risk_multiplier, license_id)
        results.append(m5)

    # Method 6: Fall-back
    m6 = method6_fallback(results, upper_bound=True)
    results.append(m6)

    # Determine final value — prefer Method 1 when available
    final_method = ValuationMethod.TRANSACTION
    final_value = m1.value

    # Article 8 adjustments
    a8 = article8_adjustments(**(article8 or {}))
    if a8 > 0 and results:
        results[0].article8_adjustments = a8
        final_value += a8

    # Related-party adjustment
    rp_adj = related_party_test(is_same_org, final_value, arms_length_value)
    if rp_adj > 0 and results:
        results[0].related_party_adjustment = rp_adj
        final_value += rp_adj

    return ValuationHierarchy(
        results=results,
        final_value=final_value,
        final_method=final_method,
    )
