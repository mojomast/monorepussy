"""Tests for core data models."""

import math
from datetime import datetime, timezone

import pytest

from ussy_gridiron.models import (
    CTIViolation,
    ComplianceCategory,
    ComplianceResult,
    ContingencyResult,
    DependencyEdge,
    ErrorHandlerContext,
    FullReport,
    GridCodeReport,
    HandlerZone,
    HealthStatus,
    InterconnectionCheck,
    N1Report,
    OPFReport,
    PackageInfo,
    RelayReport,
    SystemState,
    VersionShock,
    VoltageResult,
    VoltageReport,
)


class TestPackageInfo:
    """Tests for PackageInfo dataclass."""

    def test_default_values(self):
        pkg = PackageInfo(name="test-pkg")
        assert pkg.name == "test-pkg"
        assert pkg.version == "0.0.0"
        assert pkg.is_direct is False
        assert pkg.maintainers == 1
        assert pkg.version_rigidity == 0.5

    def test_major_version(self):
        pkg = PackageInfo(name="test", version="3.2.1")
        assert pkg.major == 3

    def test_minor_version(self):
        pkg = PackageInfo(name="test", version="3.2.1")
        assert pkg.minor == 2

    def test_patch_version(self):
        pkg = PackageInfo(name="test", version="3.2.1")
        assert pkg.patch == 1

    def test_version_with_missing_parts(self):
        pkg = PackageInfo(name="test", version="3")
        assert pkg.major == 3
        assert pkg.minor == 0
        assert pkg.patch == 0

    def test_backup_packages_default(self):
        pkg = PackageInfo(name="test")
        assert pkg.backup_packages == []

    def test_custom_values(self):
        pkg = PackageInfo(
            name="flask",
            version="3.0.0",
            is_direct=True,
            maintainers=5,
            risk_weight=2.5,
            version_rigidity=0.8,
        )
        assert pkg.name == "flask"
        assert pkg.version == "3.0.0"
        assert pkg.is_direct is True
        assert pkg.maintainers == 5
        assert pkg.risk_weight == 2.5
        assert pkg.version_rigidity == 0.8


class TestDependencyEdge:
    """Tests for DependencyEdge dataclass."""

    def test_default_values(self):
        edge = DependencyEdge(source="app", target="lib")
        assert edge.source == "app"
        assert edge.target == "lib"
        assert edge.version_constraint == "*"
        assert edge.coupling_strength == 1.0
        assert edge.is_dev is False

    def test_custom_values(self):
        edge = DependencyEdge(
            source="app", target="lib",
            version_constraint="^1.0.0",
            coupling_strength=0.7,
            is_dev=True,
        )
        assert edge.version_constraint == "^1.0.0"
        assert edge.coupling_strength == 0.7
        assert edge.is_dev is True


class TestErrorHandlerContext:
    """Tests for ErrorHandlerContext trip time calculation."""

    def test_normal_trip_time(self):
        ctx = ErrorHandlerContext(package="pkg", tds=1.0, pickup=1.0)
        t = ctx.trip_time(fault_current=5.0)
        assert t > 0
        assert t != float("inf")

    def test_higher_tds_slower_trip(self):
        fast = ErrorHandlerContext(package="fast", tds=0.5, pickup=1.0)
        slow = ErrorHandlerContext(package="slow", tds=2.0, pickup=1.0)
        assert fast.trip_time(5.0) < slow.trip_time(5.0)

    def test_zero_current_infinite_time(self):
        ctx = ErrorHandlerContext(package="pkg")
        assert ctx.trip_time(0.0) == float("inf")

    def test_current_below_pickup_infinite_time(self):
        ctx = ErrorHandlerContext(package="pkg", pickup=5.0)
        assert ctx.trip_time(3.0) == float("inf")

    def test_negative_current_infinite_time(self):
        ctx = ErrorHandlerContext(package="pkg")
        assert ctx.trip_time(-1.0) == float("inf")

    def test_zero_pickup_infinite_time(self):
        ctx = ErrorHandlerContext(package="pkg", pickup=0.0)
        assert ctx.trip_time(5.0) == float("inf")


class TestCTIViolation:
    """Tests for CTIViolation computation."""

    def test_no_violation(self):
        v = CTIViolation(
            primary_handler="h1",
            backup_handler="h2",
            primary_trip_time=0.1,
            backup_trip_time=0.5,
            cti_required=0.2,
        )
        assert v.cti_actual == 0.4
        assert v.violation_severity == "none"

    def test_marginal_violation(self):
        v = CTIViolation(
            primary_handler="h1",
            backup_handler="h2",
            primary_trip_time=0.3,
            backup_trip_time=0.4,
            cti_required=0.2,
        )
        assert abs(v.cti_actual - 0.1) < 0.001
        assert v.violation_severity == "marginal"

    def test_severe_violation(self):
        v = CTIViolation(
            primary_handler="h1",
            backup_handler="h2",
            primary_trip_time=0.5,
            backup_trip_time=0.3,
            cti_required=0.2,
        )
        assert v.cti_actual == -0.2
        assert v.violation_severity == "severe"


class TestN1Report:
    """Tests for N1Report score calculation."""

    def test_compliance_score_calculation(self):
        report = N1Report(total_packages=10, passing_packages=9)
        assert report.compliance_score == 90.0

    def test_full_compliance(self):
        report = N1Report(total_packages=5, passing_packages=5)
        assert report.compliance_score == 100.0

    def test_zero_packages(self):
        report = N1Report(total_packages=0, passing_packages=0)
        assert report.compliance_score == 100.0

    def test_no_compliance(self):
        report = N1Report(total_packages=10, passing_packages=0)
        assert report.compliance_score == 0.0


class TestEnums:
    """Tests for enum values."""

    def test_health_status_values(self):
        assert HealthStatus.NORMAL.value == "normal"
        assert HealthStatus.WARNING.value == "warning"
        assert HealthStatus.ALERT.value == "alert"
        assert HealthStatus.EMERGENCY.value == "emergency"

    def test_system_state_values(self):
        assert SystemState.FUNCTIONAL.value == "functional"
        assert SystemState.DEGRADED.value == "degraded"
        assert SystemState.FAILED.value == "failed"

    def test_compliance_category_values(self):
        assert ComplianceCategory.CATEGORY_I.value == "I"
        assert ComplianceCategory.CATEGORY_II.value == "II"
        assert ComplianceCategory.CATEGORY_III.value == "III"

    def test_handler_zone_values(self):
        assert HandlerZone.ZONE_1.value == "zone_1"
        assert HandlerZone.ZONE_2.value == "zone_2"
        assert HandlerZone.ZONE_3.value == "zone_3"


class TestVersionShock:
    """Tests for VersionShock."""

    def test_default_values(self):
        shock = VersionShock(package="lib")
        assert shock.package == "lib"
        assert shock.severity == 1.0
        assert shock.is_breaking is False
        assert shock.timestamp is None

    def test_custom_values(self):
        ts = datetime.now(timezone.utc)
        shock = VersionShock(
            package="lib",
            old_version="1.0.0",
            new_version="2.0.0",
            severity=0.8,
            is_breaking=True,
            timestamp=ts,
        )
        assert shock.old_version == "1.0.0"
        assert shock.new_version == "2.0.0"
        assert shock.is_breaking is True
        assert shock.timestamp == ts


class TestFullReport:
    """Tests for FullReport."""

    def test_default_values(self):
        report = FullReport()
        assert report.project_path == ""
        assert report.overall_status == HealthStatus.NORMAL
        assert report.n1_report is None
        assert report.frequency_report is None

    def test_with_timestamp(self):
        report = FullReport(project_path="/tmp/test")
        assert report.project_path == "/tmp/test"
        assert report.timestamp is not None
