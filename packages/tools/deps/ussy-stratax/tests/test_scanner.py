"""Tests for project scanner integration."""
import os
import tempfile
import pytest
from strata.models import ProbeResult, VersionProbeResult
from strata.scanner.lockfile import Dependency
from strata.scanner.scanner import ProjectScanner


def make_version_results(pass_patterns):
    """Create VersionProbeResult list from pass/fail patterns."""
    results = []
    for i, pattern in enumerate(pass_patterns):
        version = f"1.{i}.0"
        probe_results = [
            ProbeResult(f"probe_{j}", "pkg", version, passed=p)
            for j, p in enumerate(pattern)
        ]
        results.append(
            VersionProbeResult(package="pkg", version=version, results=probe_results)
        )
    return results


class TestProjectScanner:
    def setup_method(self):
        self.scanner = ProjectScanner()

    def test_scan_dependencies_empty(self):
        deps = []
        result = self.scanner.scan_dependencies(deps, "test.lock")
        assert result.packages_scanned == 0

    def test_scan_dependencies_without_data(self):
        deps = [Dependency("numpy", "1.24.0", "pip")]
        result = self.scanner.scan_dependencies(deps, "test.lock")
        # Without version data, no hazards found
        assert result.packages_scanned == 1

    def test_scan_with_version_data(self):
        # Provide proper version data format
        version_data = {
            "numpy": {
                "stable_fn": make_version_results([
                    [True, True],
                    [True, True],
                    [True, True],
                ]),
            }
        }
        scanner = ProjectScanner(version_data=version_data)
        deps = [Dependency("numpy", "1.24.0", "pip")]
        result = scanner.scan_dependencies(deps, "test.lock")
        assert result.packages_scanned == 1
        # All stable, no hazards
        assert not result.has_hazards

    def test_scan_classifies_hazards(self):
        # Version data showing a package with fault lines
        version_data = {
            "eroding_pkg": {
                "bedrock_fn": make_version_results([
                    [True],
                    [True],
                    [True],
                ]),
                "volatile_fn": make_version_results([
                    [True],
                    [False],
                    [False],
                ]),
            }
        }
        scanner = ProjectScanner(version_data=version_data)
        deps = [Dependency("eroding_pkg", "1.2.0", "pip")]
        result = scanner.scan_dependencies(deps, "test.lock")
        assert result.lockfile == "test.lock"
        # Should detect fault line between bedrock_fn and volatile_fn
        assert len(result.fault_lines) >= 1

    def test_scan_result_structure(self):
        deps = [Dependency("pkg1", "1.0", "pip"), Dependency("pkg2", "2.0", "npm")]
        result = self.scanner.scan_dependencies(deps, "test.lock")
        assert result.lockfile == "test.lock"
        assert result.packages_scanned == 2
        assert isinstance(result.fault_lines, list)
        assert isinstance(result.quicksand_zones, list)
        assert isinstance(result.erosion_warnings, list)
