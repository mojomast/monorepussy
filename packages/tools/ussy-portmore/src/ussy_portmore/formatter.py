"""Output formatting for Portmore results."""
from __future__ import annotations

import json
from typing import Any

from ussy_portmore.models import (
    CompatibilityResult,
    CompatibilityStatus,
    ContagionAssessment,
    DependencyZone,
    MultiLicenseResolution,
    OriginDetermination,
    OriginStatus,
    QuarantineReport,
    ValuationHierarchy,
)


def format_resolution(resolution: MultiLicenseResolution, fmt: str = "text") -> str:
    """Format a multi-license resolution result."""
    if fmt == "json":
        return json.dumps({
            "licenses_found": resolution.licenses_found,
            "governing_license": resolution.governing_license,
            "governing_hs_code": resolution.governing_hs_code,
            "reasoning_chain": resolution.reasoning_chain,
            "gir_results": [
                {"rule": r.rule, "applied": r.applied, "outcome": r.outcome}
                for r in resolution.gir_results
            ],
        }, indent=2)

    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("PORTMORE — Multi-License Classification")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Licenses detected:")
    for lic in resolution.licenses_found:
        lines.append(f"  • {lic}")
    lines.append("")
    lines.append("GIR Analysis:")
    for r in resolution.gir_results:
        marker = "✓" if r.applied else "✗"
        lines.append(f"  [{marker}] {r.rule}: {r.description}")
        if r.applied and r.outcome:
            lines.append(f"       → {r.outcome}")
    lines.append("")
    lines.append(f"Governing License: {resolution.governing_license}")
    if resolution.governing_hs_code:
        lines.append(f"HS Code: {resolution.governing_hs_code}")
    lines.append("")
    lines.append("Reasoning Chain:")
    for step in resolution.reasoning_chain:
        lines.append(f"  → {step}")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_origin(det: OriginDetermination, fmt: str = "text") -> str:
    """Format an origin determination result."""
    if fmt == "json":
        return json.dumps({
            "module": det.module,
            "status": det.status.value,
            "wholly_obtained": det.wholly_obtained,
            "ct_classification_changed": det.ct_classification_changed,
            "value_added_ratio": det.value_added_ratio,
            "de_minimis_ratio": det.de_minimis_ratio,
            "accumulation_applied": det.accumulation_applied,
            "absorption_applied": det.absorption_applied,
        }, indent=2)

    status_symbols = {
        OriginStatus.WHOLLY_OBTAINED: "✓ WHOLLY OBTAINED",
        OriginStatus.SUBSTANTIALLY_TRANSFORMED: "⚡ SUBSTANTIALLY TRANSFORMED",
        OriginStatus.NON_ORIGINATING: "✗ NON-ORIGINATING",
    }

    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"PORTMORE — Origin Determination: {det.module}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Status: {status_symbols.get(det.status, det.status.value)}")
    lines.append(f"Wholly Obtained: {'Yes' if det.wholly_obtained else 'No'}")
    lines.append(f"CT Classification Changed: {'Yes' if det.ct_classification_changed else 'No'}")
    lines.append(f"Value-Added Ratio: {det.value_added_ratio:.2%} (threshold: {det.threshold:.0%})")
    lines.append(f"De Minimis Ratio: {det.de_minimis_ratio:.2%} (threshold: {det.deminimis_threshold:.0%})")
    lines.append(f"Accumulation Applied: {'Yes' if det.accumulation_applied else 'No'}")
    lines.append(f"Absorption Applied: {'Yes' if det.absorption_applied else 'No'}")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_compatibility(result: CompatibilityResult, fmt: str = "text") -> str:
    """Format a compatibility result."""
    if fmt == "json":
        return json.dumps({
            "from_license": result.from_license,
            "to_license": result.to_license,
            "status": result.status.value,
            "conditions": result.conditions,
            "quota_remaining": result.quota_remaining,
            "anti_circumvention_flag": result.anti_circumvention_flag,
            "rules_applied": result.rules_applied,
        }, indent=2)

    status_symbols = {
        CompatibilityStatus.COMPATIBLE: "✓ COMPATIBLE",
        CompatibilityStatus.CONDITIONAL: "⚠ CONDITIONAL",
        CompatibilityStatus.INCOMPATIBLE: "✗ INCOMPATIBLE",
    }

    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("PORTMORE — License Compatibility Analysis")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"From: {result.from_license}")
    lines.append(f"To: {result.to_license}")
    lines.append(f"Status: {status_symbols.get(result.status, result.status.value)}")
    if result.conditions:
        lines.append("")
        lines.append("Conditions:")
        for cond in result.conditions:
            lines.append(f"  • {cond}")
    if result.quota_remaining > 0:
        lines.append(f"Quota Remaining: {result.quota_remaining}")
    if result.anti_circumvention_flag:
        lines.append("⚠ Anti-circumvention flag raised!")
    if result.rules_applied:
        lines.append("")
        lines.append("Rules Applied:")
        for rule in result.rules_applied:
            lines.append(f"  • {rule}")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_valuation(hierarchy: ValuationHierarchy, fmt: str = "text") -> str:
    """Format a valuation hierarchy result."""
    if fmt == "json":
        return json.dumps({
            "final_value": hierarchy.final_value,
            "final_method": hierarchy.final_method.name,
            "methods": [
                {
                    "method": r.method.name,
                    "value": r.value,
                    "article8_adjustments": r.article8_adjustments,
                    "related_party_adjustment": r.related_party_adjustment,
                    "reasoning": r.reasoning,
                }
                for r in hierarchy.results
            ],
        }, indent=2)

    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("PORTMORE — Compliance Value Assessment")
    lines.append("=" * 60)
    lines.append("")
    for r in hierarchy.results:
        marker = "→" if r.method == hierarchy.final_method else " "
        lines.append(f" {marker} Method {r.method.value} ({r.method.name}): "
                     f"${r.value:,.2f}")
        if r.article8_adjustments:
            lines.append(f"     Article 8 adjustments: +${r.article8_adjustments:,.2f}")
        if r.related_party_adjustment:
            lines.append(f"     Related-party adjustment: +${r.related_party_adjustment:,.2f}")
        if r.reasoning:
            lines.append(f"     {r.reasoning}")
    lines.append("")
    lines.append(f"Final Compliance Value: ${hierarchy.final_value:,.2f} "
                 f"(Method {hierarchy.final_method.value}: {hierarchy.final_method.name})")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_contagion(assessment: ContagionAssessment, fmt: str = "text") -> str:
    """Format a contagion assessment result."""
    if fmt == "json":
        return json.dumps({
            "license_id": assessment.license_id,
            "dumping_margin": assessment.dumping_margin,
            "copyleft_ratio": assessment.copyleft_ratio,
            "within_duty_order": assessment.within_duty_order,
            "injury_indicators": [i.value for i in assessment.injury_indicators],
            "causal_link_established": assessment.causal_link_established,
            "lesser_duty_remedy": assessment.lesser_duty_remedy,
            "scope_ruling": assessment.scope_ruling,
            "threshold": assessment.threshold,
        }, indent=2)

    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"PORTMORE — Copyleft Contagion Assessment: {assessment.license_id}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Dumping Margin: {assessment.dumping_margin:+.1f} "
                 f"({'DUMPING' if assessment.dumping_margin < 0 else 'FAIR VALUE'})")
    lines.append(f"Copyleft Code Ratio: {assessment.copyleft_ratio:.1%}")
    lines.append(f"Within Duty Order: {'Yes' if assessment.within_duty_order else 'No'} "
                 f"(threshold: {assessment.threshold:.0%})")
    lines.append("")
    lines.append("Injury Indicators:")
    if assessment.injury_indicators:
        for indicator in assessment.injury_indicators:
            lines.append(f"  • {indicator.value}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append(f"Causal Link Established: {'Yes' if assessment.causal_link_established else 'No'}")
    lines.append(f"Lesser Duty Remedy: {assessment.lesser_duty_remedy}")
    if assessment.scope_ruling:
        lines.append(f"Scope Ruling: {assessment.scope_ruling}")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_quarantine(report: QuarantineReport, fmt: str = "text") -> str:
    """Format a quarantine report."""
    if fmt == "json":
        return json.dumps({
            "entries": [
                {
                    "dependency": e.dependency,
                    "zone": e.zone.value,
                    "legal_status": e.legal_status,
                    "obligations": e.obligations,
                    "manipulation_warning": e.manipulation_warning,
                    "constructive_warehouse": e.constructive_warehouse,
                }
                for e in report.entries
            ],
            "boundary_violations": report.boundary_violations,
            "manipulation_warnings": report.manipulation_warnings,
        }, indent=2)

    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("PORTMORE — Dependency Quarantine Report")
    lines.append("=" * 60)
    lines.append("")

    for entry in report.entries:
        zone_symbol = "📦" if entry.zone == DependencyZone.BONDED else "🏠"
        lines.append(f" {zone_symbol} {entry.dependency}")
        lines.append(f"    Zone: {entry.zone.value}")
        lines.append(f"    Status: {entry.legal_status}")
        if entry.obligations:
            lines.append(f"    Obligations: {', '.join(entry.obligations)}")
        if entry.manipulation_warning:
            lines.append("    ⚠ Class 5 manipulation detected!")
        if entry.constructive_warehouse:
            lines.append("    ⚠ Constructive warehouse — dev dep in runtime!")
        if entry.in_bond_movement:
            lines.append("    ↗ In-bond movement")
        lines.append("")

    if report.boundary_violations:
        lines.append("Boundary Violations:")
        for v in report.boundary_violations:
            lines.append(f"  ⚠ {v}")
        lines.append("")

    if report.manipulation_warnings:
        lines.append("Manipulation Warnings:")
        for w in report.manipulation_warnings:
            lines.append(f"  ⚠ {w}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
