"""Tests for Bonded Warehousing — Dependency Quarantine."""
import pytest

from portmore.quarantine import (
    check_class5_manipulation,
    check_constructive_warehouse,
    classify_dependency_zone,
    domestic_withdrawal,
    export_withdrawal,
    generate_quarantine_report,
    in_bond_movement,
)
from portmore.models import DependencyZone, QuarantineEntry, WithdrawalType


class TestClassifyDependencyZone:
    """Tests for dependency zone classification."""

    def test_dev_dependency_bonded(self):
        entry = classify_dependency_zone("pytest", is_dev_only=True)
        assert entry.zone == DependencyZone.BONDED
        assert entry.legal_status == "duty-deferred"
        assert entry.obligations == []

    def test_runtime_dependency_domestic(self):
        entry = classify_dependency_zone("requests", is_dev_only=False, license_id="Apache-2.0")
        assert entry.zone == DependencyZone.DOMESTIC
        assert entry.legal_status == "duty-paid"
        assert len(entry.obligations) > 0

    def test_dev_with_license_id(self):
        entry = classify_dependency_zone("mypy", is_dev_only=True, license_id="MIT")
        assert entry.zone == DependencyZone.BONDED
        # Dev deps have no obligations until withdrawn
        assert entry.obligations == []

    def test_runtime_gpl_obligations(self):
        entry = classify_dependency_zone("gpl-lib", is_dev_only=False, license_id="GPL-3.0")
        assert "source_disclosure" in entry.obligations
        assert "copyleft_inheritance" in entry.obligations


class TestExportWithdrawal:
    """Tests for export withdrawal (removed from production)."""

    def test_runtime_to_bonded(self):
        entry = QuarantineEntry(
            dependency="lib", zone=DependencyZone.DOMESTIC,
            legal_status="duty-paid", obligations=["attribution"],
        )
        result = export_withdrawal(entry)
        assert result.zone == DependencyZone.BONDED
        assert result.legal_status == "duty-deferred"
        assert result.obligations == []
        assert result.withdrawal_type == WithdrawalType.EXPORT

    def test_zero_duty(self):
        entry = QuarantineEntry(
            dependency="lib", zone=DependencyZone.DOMESTIC,
            legal_status="duty-paid", obligations=["attribution", "source_disclosure"],
        )
        result = export_withdrawal(entry)
        assert result.obligations == []


class TestDomesticWithdrawal:
    """Tests for domestic withdrawal (included in runtime)."""

    def test_bonded_to_domestic(self):
        entry = QuarantineEntry(
            dependency="lib", zone=DependencyZone.BONDED,
            legal_status="duty-deferred", obligations=[],
        )
        result = domestic_withdrawal(entry, license_id="MIT")
        assert result.zone == DependencyZone.DOMESTIC
        assert result.legal_status == "duty-paid"
        assert result.withdrawal_type == WithdrawalType.DOMESTIC
        assert len(result.obligations) > 0

    def test_full_duty_applies(self):
        entry = QuarantineEntry(
            dependency="lib", zone=DependencyZone.BONDED,
            legal_status="duty-deferred", obligations=[],
        )
        result = domestic_withdrawal(entry, license_id="GPL-3.0")
        assert "source_disclosure" in result.obligations


class TestClass5Manipulation:
    """Tests for Class 5 manipulation rule."""

    def test_dev_not_compiled(self):
        entry = check_class5_manipulation("pytest", is_dev_only=True, compiled_into_runtime=False)
        assert entry.zone == DependencyZone.BONDED
        assert entry.manipulation_warning is False

    def test_dev_compiled_into_runtime(self):
        entry = check_class5_manipulation(
            "bundled-tool", is_dev_only=True, compiled_into_runtime=True, license_id="GPL-3.0"
        )
        assert entry.zone == DependencyZone.DOMESTIC
        assert entry.manipulation_warning is True
        assert "Class 5" in entry.legal_status

    def test_runtime_not_affected(self):
        entry = check_class5_manipulation("lib", is_dev_only=False, compiled_into_runtime=True)
        assert entry.manipulation_warning is False

    def test_retroactive_obligations(self):
        entry = check_class5_manipulation(
            "tool", is_dev_only=True, compiled_into_runtime=True, license_id="Apache-2.0"
        )
        assert len(entry.obligations) > 0


class TestConstructiveWarehouse:
    """Tests for constructive warehouse detection."""

    def test_dev_no_runtime_import(self):
        entry = check_constructive_warehouse("pytest", is_dev_only=True, runtime_import=False)
        assert entry.constructive_warehouse is False

    def test_dev_with_runtime_import(self):
        entry = check_constructive_warehouse(
            "lazy-lib", is_dev_only=True, runtime_import=True, license_id="MIT"
        )
        assert entry.constructive_warehouse is True
        assert "constructively" in entry.legal_status
        assert len(entry.obligations) > 0

    def test_runtime_no_constructive(self):
        entry = check_constructive_warehouse("lib", is_dev_only=False, runtime_import=True)
        assert entry.constructive_warehouse is False


class TestInBondMovement:
    """Tests for in-bond movement."""

    def test_preserves_zone(self):
        entry = QuarantineEntry(
            dependency="lib", zone=DependencyZone.BONDED,
            legal_status="duty-deferred", obligations=[],
        )
        result = in_bond_movement(entry, "other-project")
        assert result.zone == DependencyZone.BONDED
        assert result.in_bond_movement is True

    def test_preserves_obligations(self):
        entry = QuarantineEntry(
            dependency="lib", zone=DependencyZone.DOMESTIC,
            legal_status="duty-paid", obligations=["attribution"],
        )
        result = in_bond_movement(entry, "other-project")
        assert result.obligations == ["attribution"]


class TestQuarantineReport:
    """Tests for the full quarantine report generation."""

    def test_basic_report(self):
        deps = [
            {"name": "requests", "is_dev_only": False, "license_id": "Apache-2.0"},
            {"name": "pytest", "is_dev_only": True, "license_id": "MIT"},
        ]
        report = generate_quarantine_report(deps)
        assert len(report.entries) == 2
        assert report.entries[0].zone == DependencyZone.DOMESTIC
        assert report.entries[1].zone == DependencyZone.BONDED

    def test_boundary_violation_detected(self):
        deps = [
            {"name": "bundled-tool", "is_dev_only": True, "license_id": "GPL-3.0",
             "compiled_into_runtime": True},
        ]
        report = generate_quarantine_report(deps)
        assert len(report.boundary_violations) > 0

    def test_manipulation_warning(self):
        deps = [
            {"name": "tool", "is_dev_only": True, "license_id": "GPL-3.0",
             "compiled_into_runtime": True},
        ]
        report = generate_quarantine_report(deps)
        assert len(report.manipulation_warnings) > 0

    def test_no_violations_clean(self):
        deps = [
            {"name": "requests", "is_dev_only": False, "license_id": "Apache-2.0",
             "compiled_into_runtime": False, "runtime_import": False},
            {"name": "pytest", "is_dev_only": True, "license_id": "MIT",
             "compiled_into_runtime": False, "runtime_import": False},
        ]
        report = generate_quarantine_report(deps)
        assert len(report.boundary_violations) == 0
        assert len(report.manipulation_warnings) == 0

    def test_constructive_warehouse_in_report(self):
        deps = [
            {"name": "lazy-lib", "is_dev_only": True, "license_id": "MIT",
             "compiled_into_runtime": False, "runtime_import": True},
        ]
        report = generate_quarantine_report(deps)
        assert report.entries[0].constructive_warehouse is True

    def test_empty_deps(self):
        report = generate_quarantine_report([])
        assert len(report.entries) == 0

    def test_timestamp_populated(self):
        deps = [{"name": "lib", "is_dev_only": False, "license_id": "MIT"}]
        report = generate_quarantine_report(deps)
        assert report.timestamp != ""
