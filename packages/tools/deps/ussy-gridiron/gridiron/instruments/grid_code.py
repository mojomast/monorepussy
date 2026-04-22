"""Instrument 6: Grid Code Inspector — IEEE 1547 Interconnection Compliance.

IEEE 1547 requirements mapped to dependency ecosystem:
  1. Voltage regulation → API stability bounds
  2. Frequency ride-through → consumer tolerance for version bumps
  3. Power quality → side-effect ratio, type pollution
  4. Reactive capability → metadata completeness
  5. Category certification → I (patch-safe), II (minor-safe), III (major-safe)
"""

from __future__ import annotations

from typing import Dict, List, Optional

from gridiron.graph import DependencyGraph
from gridiron.models import (
    ComplianceCategory,
    ComplianceResult,
    GridCodeReport,
    InterconnectionCheck,
    PackageInfo,
)


class GridCodeInspector:
    """IEEE 1547 interconnection compliance analysis."""

    # Thresholds
    VOLTAGE_MIN_PU = 0.917
    VOLTAGE_MAX_PU = 1.058
    SIDE_EFFECT_MAX = 0.1
    TYPE_POLLUTION_MAX = 0.05
    METADATA_MIN_BASIC = 0.5
    METADATA_MIN_STANDARD = 0.7
    METADATA_MIN_ROBUST = 0.9

    # API change bounds per version bump type
    API_CHANGE_PATCH_MAX = 0.0
    API_CHANGE_MINOR_MAX = 0.05
    API_CHANGE_MAJOR_MAX = 1.0

    def __init__(self, graph: DependencyGraph) -> None:
        self.graph = graph

    def inspect_all(self) -> List[GridCodeReport]:
        """Run interconnection compliance checks on all packages."""
        reports = []
        for pkg_name in sorted(self.graph.packages.keys()):
            report = self.inspect_package(pkg_name)
            reports.append(report)
        return reports

    def inspect_package(self, package: str) -> GridCodeReport:
        """Run interconnection compliance checks on a single package."""
        pkg = self.graph.packages.get(package, PackageInfo(name=package))

        # Determine category based on semver compliance
        category = self._determine_category(pkg)

        checks: List[InterconnectionCheck] = []

        # 1. Voltage regulation: API stability bounds
        checks.append(self._check_voltage_regulation(pkg))

        # 2. Frequency ride-through: consumer tolerance
        checks.append(self._check_frequency_ridethrough(pkg))

        # 3. Power quality: side effects and type pollution
        checks.append(self._check_side_effects(pkg))
        checks.append(self._check_type_pollution(pkg))

        # 4. Reactive capability: metadata completeness
        checks.append(self._check_metadata_completeness(pkg, category))

        # 5. Category certification
        checks.append(self._check_category_certification(pkg, category))

        # Overall compliance
        any_fail = any(c.result == ComplianceResult.FAIL for c in checks)
        any_warning = any(c.result == ComplianceResult.WARNING for c in checks)

        if any_fail:
            overall = ComplianceResult.FAIL
        elif any_warning:
            overall = ComplianceResult.WARNING
        else:
            overall = ComplianceResult.PASS

        # Power factor: metadata completeness analog
        power_factor = pkg.metadata_completeness

        # Ride-through test results
        ride_through = self._run_ridethrough_tests(pkg)

        return GridCodeReport(
            package=package,
            category=category,
            checks=checks,
            overall_compliance=overall,
            power_factor=power_factor,
            ride_through_results=ride_through,
        )

    def _determine_category(self, pkg: PackageInfo) -> ComplianceCategory:
        """Determine IEEE 1547 category based on package characteristics."""
        if pkg.semver_compliance >= 0.9 and pkg.has_types and pkg.has_tests:
            return ComplianceCategory.CATEGORY_III
        elif pkg.semver_compliance >= 0.7:
            return ComplianceCategory.CATEGORY_II
        else:
            return ComplianceCategory.CATEGORY_I

    def _check_voltage_regulation(self, pkg: PackageInfo) -> InterconnectionCheck:
        """Check API stability bounds (voltage regulation analog)."""
        # API change rate should respect semver bounds
        # For a patch: no breaking changes; minor: < 5% API surface change
        api_churn = pkg.side_effect_ratio + pkg.type_pollution
        threshold = self.API_CHANGE_MINOR_MAX  # minor as default

        if api_churn <= threshold:
            result = ComplianceResult.PASS
        elif api_churn <= threshold * 2:
            result = ComplianceResult.WARNING
        else:
            result = ComplianceResult.FAIL

        return InterconnectionCheck(
            name="voltage_regulation",
            result=result,
            value=api_churn,
            threshold=threshold,
            details=f"API churn rate: {api_churn:.3f} (threshold: {threshold:.3f})",
        )

    def _check_frequency_ridethrough(self, pkg: PackageInfo) -> InterconnectionCheck:
        """Check if consumers can survive version bumps (ride-through analog)."""
        # Packages with flexible version ranges support ride-through
        flexibility = 1.0 - pkg.version_rigidity
        threshold = 0.3  # minimum flexibility for ride-through

        if flexibility >= threshold:
            result = ComplianceResult.PASS
        elif flexibility >= threshold * 0.5:
            result = ComplianceResult.WARNING
        else:
            result = ComplianceResult.FAIL

        return InterconnectionCheck(
            name="frequency_ridethrough",
            result=result,
            value=flexibility,
            threshold=threshold,
            details=f"Version flexibility: {flexibility:.3f} (threshold: {threshold:.3f})",
        )

    def _check_side_effects(self, pkg: PackageInfo) -> InterconnectionCheck:
        """Check side-effect ratio (DC injection analog)."""
        threshold = self.SIDE_EFFECT_MAX

        if pkg.side_effect_ratio <= threshold:
            result = ComplianceResult.PASS
        elif pkg.side_effect_ratio <= threshold * 2:
            result = ComplianceResult.WARNING
        else:
            result = ComplianceResult.FAIL

        return InterconnectionCheck(
            name="side_effects",
            result=result,
            value=pkg.side_effect_ratio,
            threshold=threshold,
            details=f"Side-effect ratio: {pkg.side_effect_ratio:.3f} (max: {threshold:.3f})",
        )

    def _check_type_pollution(self, pkg: PackageInfo) -> InterconnectionCheck:
        """Check type pollution (harmonics analog)."""
        threshold = self.TYPE_POLLUTION_MAX

        if pkg.type_pollution <= threshold:
            result = ComplianceResult.PASS
        elif pkg.type_pollution <= threshold * 2:
            result = ComplianceResult.WARNING
        else:
            result = ComplianceResult.FAIL

        return InterconnectionCheck(
            name="type_pollution",
            result=result,
            value=pkg.type_pollution,
            threshold=threshold,
            details=f"Type pollution: {pkg.type_pollution:.3f} (max: {threshold:.3f})",
        )

    def _check_metadata_completeness(
        self, pkg: PackageInfo, category: ComplianceCategory
    ) -> InterconnectionCheck:
        """Check metadata completeness (reactive capability analog)."""
        if category == ComplianceCategory.CATEGORY_III:
            threshold = self.METADATA_MIN_ROBUST
        elif category == ComplianceCategory.CATEGORY_II:
            threshold = self.METADATA_MIN_STANDARD
        else:
            threshold = self.METADATA_MIN_BASIC

        if pkg.metadata_completeness >= threshold:
            result = ComplianceResult.PASS
        elif pkg.metadata_completeness >= threshold * 0.8:
            result = ComplianceResult.WARNING
        else:
            result = ComplianceResult.FAIL

        return InterconnectionCheck(
            name="metadata_completeness",
            result=result,
            value=pkg.metadata_completeness,
            threshold=threshold,
            details=f"Metadata completeness: {pkg.metadata_completeness:.3f} "
                    f"(required for Category {category.value}: {threshold:.3f})",
        )

    def _check_category_certification(
        self, pkg: PackageInfo, category: ComplianceCategory
    ) -> InterconnectionCheck:
        """Check if package meets its category certification requirements."""
        score = 0.0
        max_score = 0.0

        # Patch-safe (Category I): semver compliance
        max_score += 1.0
        if pkg.semver_compliance >= 0.5:
            score += 1.0

        # Minor-safe (Category II): + types or docs
        if category.value in ("II", "III"):
            max_score += 1.0
            if pkg.has_types or pkg.has_docs:
                score += 1.0

        # Major-safe (Category III): + tests + fallback
        if category.value == "III":
            max_score += 1.0
            if pkg.has_tests and len(pkg.backup_packages) > 0:
                score += 1.0

        compliance_ratio = score / max_score if max_score > 0 else 0.0

        if compliance_ratio >= 1.0:
            result = ComplianceResult.PASS
        elif compliance_ratio >= 0.5:
            result = ComplianceResult.WARNING
        else:
            result = ComplianceResult.FAIL

        return InterconnectionCheck(
            name="category_certification",
            result=result,
            value=compliance_ratio,
            threshold=1.0,
            details=f"Category {category.value} certification: {compliance_ratio:.1%}",
        )

    def _run_ridethrough_tests(self, pkg: PackageInfo) -> Dict[str, bool]:
        """Simulate ride-through tests for version bumps."""
        results = {}

        # Patch ride-through: all packages should survive
        results["patch_bump"] = True  # patches should never break

        # Minor ride-through: flexible packages survive
        results["minor_bump"] = pkg.version_rigidity < 0.8

        # Major ride-through: only Category III with fallbacks
        results["major_bump"] = (
            pkg.semver_compliance >= 0.9
            and pkg.has_types
            and len(pkg.backup_packages) > 0
        )

        return results
