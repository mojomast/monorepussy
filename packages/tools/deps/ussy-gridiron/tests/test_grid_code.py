"""Tests for the grid code inspector instrument."""

import pytest

from ussy_gridiron.graph import DependencyGraph
from ussy_gridiron.instruments.grid_code import GridCodeInspector
from ussy_gridiron.models import (
    ComplianceCategory,
    ComplianceResult,
    DependencyEdge,
    GridCodeReport,
    PackageInfo,
)


def _make_compliant_graph():
    """Create a graph with compliant packages."""
    g = DependencyGraph()
    g.add_package(PackageInfo(
        name="app", is_direct=False,
        semver_compliance=0.95, side_effect_ratio=0.02, type_pollution=0.01,
        metadata_completeness=0.95, version_rigidity=0.3,
        has_types=True, has_docs=True, has_tests=True,
        backup_packages=["fallback"],
    ))
    g.add_package(PackageInfo(
        name="good_lib", is_direct=True,
        semver_compliance=0.9, side_effect_ratio=0.05, type_pollution=0.02,
        metadata_completeness=0.85, version_rigidity=0.4,
        has_types=True, has_docs=True, has_tests=True,
        backup_packages=["alt_lib"],
    ))
    g.add_edge(DependencyEdge(source="app", target="good_lib"))
    return g


def _make_noncompliant_graph():
    """Create a graph with non-compliant packages."""
    g = DependencyGraph()
    g.add_package(PackageInfo(
        name="bad_lib", is_direct=True,
        semver_compliance=0.2, side_effect_ratio=0.5, type_pollution=0.3,
        metadata_completeness=0.3, version_rigidity=1.0,
        has_types=False, has_docs=False, has_tests=False,
        backup_packages=[],
    ))
    return g


class TestGridCodeInspector:
    """Tests for IEEE 1547 interconnection compliance."""

    def test_inspect_all(self):
        g = _make_compliant_graph()
        inspector = GridCodeInspector(g)
        reports = inspector.inspect_all()
        assert len(reports) == 2

    def test_inspect_package(self):
        g = _make_compliant_graph()
        inspector = GridCodeInspector(g)
        report = inspector.inspect_package("good_lib")
        assert report.package == "good_lib"

    def test_compliant_package_passes(self):
        g = _make_compliant_graph()
        inspector = GridCodeInspector(g)
        report = inspector.inspect_package("good_lib")
        assert report.overall_compliance in (ComplianceResult.PASS, ComplianceResult.WARNING)

    def test_noncompliant_package_fails(self):
        g = _make_noncompliant_graph()
        inspector = GridCodeInspector(g)
        report = inspector.inspect_package("bad_lib")
        assert report.overall_compliance == ComplianceResult.FAIL

    def test_checks_populated(self):
        g = _make_compliant_graph()
        inspector = GridCodeInspector(g)
        report = inspector.inspect_package("good_lib")
        assert len(report.checks) == 6  # 6 checks total

    def test_voltage_regulation_check(self):
        g = _make_noncompliant_graph()
        inspector = GridCodeInspector(g)
        report = inspector.inspect_package("bad_lib")
        vr_check = next(c for c in report.checks if c.name == "voltage_regulation")
        assert vr_check.result in (ComplianceResult.WARNING, ComplianceResult.FAIL)

    def test_side_effects_check(self):
        g = _make_noncompliant_graph()
        inspector = GridCodeInspector(g)
        report = inspector.inspect_package("bad_lib")
        se_check = next(c for c in report.checks if c.name == "side_effects")
        assert se_check.result == ComplianceResult.FAIL

    def test_type_pollution_check(self):
        g = _make_noncompliant_graph()
        inspector = GridCodeInspector(g)
        report = inspector.inspect_package("bad_lib")
        tp_check = next(c for c in report.checks if c.name == "type_pollution")
        assert tp_check.result == ComplianceResult.FAIL

    def test_metadata_completeness_check(self):
        g = _make_noncompliant_graph()
        inspector = GridCodeInspector(g)
        report = inspector.inspect_package("bad_lib")
        mc_check = next(c for c in report.checks if c.name == "metadata_completeness")
        assert mc_check.result == ComplianceResult.FAIL

    def test_power_factor(self):
        g = _make_compliant_graph()
        inspector = GridCodeInspector(g)
        report = inspector.inspect_package("good_lib")
        assert 0 <= report.power_factor <= 1.0

    def test_ridethrough_tests(self):
        g = _make_compliant_graph()
        inspector = GridCodeInspector(g)
        report = inspector.inspect_package("good_lib")
        assert "patch_bump" in report.ride_through_results
        assert "minor_bump" in report.ride_through_results
        assert "major_bump" in report.ride_through_results

    def test_category_determination(self):
        # Category III: high semver, types, tests
        g = DependencyGraph()
        g.add_package(PackageInfo(
            name="robust",
            semver_compliance=0.95, has_types=True, has_tests=True,
        ))
        inspector = GridCodeInspector(g)
        report = inspector.inspect_package("robust")
        assert report.category == ComplianceCategory.CATEGORY_III

    def test_category_i_for_low_semver(self):
        g = DependencyGraph()
        g.add_package(PackageInfo(
            name="basic",
            semver_compliance=0.3, has_types=False, has_tests=False,
        ))
        inspector = GridCodeInspector(g)
        report = inspector.inspect_package("basic")
        assert report.category == ComplianceCategory.CATEGORY_I

    def test_rigid_package_fails_ridethrough(self):
        g = DependencyGraph()
        g.add_package(PackageInfo(
            name="rigid_pkg",
            version_rigidity=1.0,
            semver_compliance=0.5,
            has_types=False,
            backup_packages=[],
        ))
        inspector = GridCodeInspector(g)
        report = inspector.inspect_package("rigid_pkg")
        assert report.ride_through_results["minor_bump"] is False
        assert report.ride_through_results["major_bump"] is False
