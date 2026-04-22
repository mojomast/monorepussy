"""Bonded Warehousing — Dependency Quarantine."""
from __future__ import annotations

from portmore.models import (
    DependencyZone,
    QuarantineEntry,
    QuarantineReport,
    WithdrawalType,
)
from portmore.hs_codes import get_family, LicenseFamily


def classify_dependency_zone(
    dependency: str,
    is_dev_only: bool,
    license_id: str = "",
) -> QuarantineEntry:
    """Classify a dependency into bonded (dev) or domestic (runtime) zone."""
    if is_dev_only:
        zone = DependencyZone.BONDED
        legal_status = "duty-deferred"
        obligations = []
    else:
        zone = DependencyZone.DOMESTIC
        legal_status = "duty-paid"
        obligations = _runtime_obligations(license_id)

    return QuarantineEntry(
        dependency=dependency,
        zone=zone,
        legal_status=legal_status,
        obligations=obligations,
    )


def _runtime_obligations(license_id: str) -> list[str]:
    """Determine runtime obligations for a license."""
    fam = get_family(license_id)
    if fam == LicenseFamily.PUBLIC_DOMAIN:
        return []
    if fam == LicenseFamily.PERMISSIVE:
        return ["attribution", "notice_retention"]
    if fam == LicenseFamily.WEAK_COPYLEFT:
        return ["attribution", "source_disclosure", "copyleft_inheritance"]
    if fam == LicenseFamily.STRONG_COPYLEFT:
        return ["attribution", "source_disclosure", "copyleft_inheritance",
                "changes_disclosure"]
    if fam == LicenseFamily.PROPRIETARY:
        return ["license_compliance", "redistribution_restriction"]
    return ["attribution"]


def export_withdrawal(entry: QuarantineEntry) -> QuarantineEntry:
    """Export withdrawal: dependency removed from production = ZERO duty.

    Changes zone to BONDED and clears obligations.
    """
    return QuarantineEntry(
        dependency=entry.dependency,
        zone=DependencyZone.BONDED,
        legal_status="duty-deferred",
        obligations=[],
        withdrawal_type=WithdrawalType.EXPORT,
        manipulation_warning=entry.manipulation_warning,
        constructive_warehouse=entry.constructive_warehouse,
        in_bond_movement=entry.in_bond_movement,
    )


def domestic_withdrawal(entry: QuarantineEntry, license_id: str = "") -> QuarantineEntry:
    """Domestic withdrawal: dependency included in runtime = FULL duty applies.

    Changes zone to DOMESTIC and activates all obligations.
    """
    obligations = _runtime_obligations(license_id) if license_id else entry.obligations
    return QuarantineEntry(
        dependency=entry.dependency,
        zone=DependencyZone.DOMESTIC,
        legal_status="duty-paid",
        obligations=obligations,
        withdrawal_type=WithdrawalType.DOMESTIC,
        manipulation_warning=entry.manipulation_warning,
        constructive_warehouse=entry.constructive_warehouse,
        in_bond_movement=entry.in_bond_movement,
    )


def check_class5_manipulation(
    dependency: str,
    is_dev_only: bool,
    compiled_into_runtime: bool,
    license_id: str = "",
) -> QuarantineEntry:
    """Class 5 Manipulation Rule.

    If a dev-only dependency's code is compiled INTO the runtime
    (not just executed during build), it crosses the warehouse boundary
    → status changes from 'duty-deferred' to 'duty-paid'
    → all obligations activate retroactively
    """
    entry = classify_dependency_zone(dependency, is_dev_only, license_id)

    if is_dev_only and compiled_into_runtime:
        entry.zone = DependencyZone.DOMESTIC
        entry.legal_status = "duty-paid (Class 5 manipulation)"
        entry.obligations = _runtime_obligations(license_id)
        entry.manipulation_warning = True

    return entry


def check_constructive_warehouse(
    dependency: str,
    is_dev_only: bool,
    runtime_import: bool,
    license_id: str = "",
) -> QuarantineEntry:
    """Constructive Warehouse.

    If runtime code imports from a dev-only dependency at runtime
    (lazy import, reflection, plugin loading), the dev dependency
    is 'constructively' in the domestic zone
    → obligations apply even though it's listed as dev-only
    """
    entry = classify_dependency_zone(dependency, is_dev_only, license_id)

    if is_dev_only and runtime_import:
        entry.constructive_warehouse = True
        entry.legal_status = "constructively duty-paid"
        entry.obligations = _runtime_obligations(license_id)

    return entry


def in_bond_movement(
    entry: QuarantineEntry,
    target_project: str,
) -> QuarantineEntry:
    """In-Bond Movement.

    Moving a dependency between projects within same org
    → maintains its quarantine status (no new duty assessment)
    → BUT: origin documentation must be preserved
    """
    return QuarantineEntry(
        dependency=entry.dependency,
        zone=entry.zone,
        legal_status=entry.legal_status,
        obligations=list(entry.obligations),
        withdrawal_type=entry.withdrawal_type,
        manipulation_warning=entry.manipulation_warning,
        constructive_warehouse=entry.constructive_warehouse,
        in_bond_movement=True,
    )


def generate_quarantine_report(
    dependencies: list[dict],
) -> QuarantineReport:
    """Generate a full quarantine report for a project.

    Args:
        dependencies: List of dicts with keys:
            name, is_dev_only, license_id, compiled_into_runtime,
            runtime_import
    """
    entries: list[QuarantineEntry] = []
    boundary_violations: list[str] = []
    manipulation_warnings: list[str] = []

    for dep in dependencies:
        name = dep.get("name", "unknown")
        is_dev = dep.get("is_dev_only", False)
        lic_id = dep.get("license_id", "")
        compiled = dep.get("compiled_into_runtime", False)
        runtime_import = dep.get("runtime_import", False)

        # Check Class 5 manipulation first
        entry = check_class5_manipulation(name, is_dev, compiled, lic_id)

        # Then check constructive warehouse
        if is_dev and runtime_import:
            entry = check_constructive_warehouse(name, is_dev, runtime_import, lic_id)

        # Detect boundary violations
        if is_dev and (compiled or runtime_import):
            violation_type = "compiled_into_runtime" if compiled else "runtime_import"
            boundary_violations.append(
                f"{name}: dev-only dependency has {violation_type} — boundary crossed"
            )
            if compiled:
                manipulation_warnings.append(
                    f"{name}: Class 5 manipulation — dev code compiled into runtime"
                )

        entries.append(entry)

    return QuarantineReport(
        entries=entries,
        boundary_violations=boundary_violations,
        manipulation_warnings=manipulation_warnings,
    )
