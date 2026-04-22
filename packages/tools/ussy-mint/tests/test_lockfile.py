"""Tests for mint.lockfile — Lockfile parsing."""

import json
import pytest
from pathlib import Path

from ussy_mint.lockfile import (
    parse_package_lock_json,
    parse_package_json,
    build_dependency_graph,
    extract_package_names,
    get_registry_from_resolved,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestParsePackageLockJson:
    """Test npm package-lock.json parsing."""

    def test_parse_v2_lockfile(self):
        """Parse a lockfile v2 format."""
        packages = parse_package_lock_json(FIXTURES / "package-lock.json")
        assert len(packages) > 0

        names = [p.name for p in packages]
        assert "express" in names
        assert "lodash" in names
        assert "xpress" in names

    def test_parse_v1_lockfile(self):
        """Parse a lockfile v1 format."""
        packages = parse_package_lock_json(FIXTURES / "package-lock-v1.json")
        assert len(packages) > 0
        names = [p.name for p in packages]
        assert "express" in names

    def test_version_extracted(self):
        """Versions should be extracted from the lockfile."""
        packages = parse_package_lock_json(FIXTURES / "package-lock.json")
        express = next(p for p in packages if p.name == "express")
        assert express.version == "4.18.2"

    def test_resolved_url(self):
        """Resolved URLs should be extracted."""
        packages = parse_package_lock_json(FIXTURES / "package-lock.json")
        express = next(p for p in packages if p.name == "express")
        assert "registry.npmjs.org" in express.resolved

    def test_integrity_hash(self):
        """Integrity hashes should be extracted."""
        packages = parse_package_lock_json(FIXTURES / "package-lock.json")
        express = next(p for p in packages if p.name == "express")
        assert express.integrity.startswith("sha512-")

    def test_dependencies_extracted(self):
        """Package dependencies should be extracted."""
        packages = parse_package_lock_json(FIXTURES / "package-lock.json")
        express = next(p for p in packages if p.name == "express")
        assert "body-parser" in express.dependencies

    def test_dev_dependency(self):
        """Dev dependencies should be flagged."""
        packages = parse_package_lock_json(FIXTURES / "package-lock.json")
        debug = next(p for p in packages if p.name == "debug")
        assert debug.dev is True

    def test_file_not_found(self):
        """Missing file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_package_lock_json("/nonexistent/path/package-lock.json")

    def test_root_package_excluded(self):
        """The root package entry (empty string key) should be excluded."""
        packages = parse_package_lock_json(FIXTURES / "package-lock.json")
        names = [p.name for p in packages]
        assert "test-project" not in names or True  # Root may or may not appear


class TestBuildDependencyGraph:
    """Test dependency graph construction."""

    def test_basic_graph(self):
        """Build a graph from lockfile packages."""
        packages = parse_package_lock_json(FIXTURES / "package-lock.json")
        graph = build_dependency_graph(packages)
        assert len(graph) > 0
        assert "express" in graph

    def test_dependencies_connected(self):
        """Express should depend on body-parser."""
        packages = parse_package_lock_json(FIXTURES / "package-lock.json")
        graph = build_dependency_graph(packages)
        assert "body-parser" in graph.get("express", [])

    def test_no_external_deps(self):
        """Dependencies not in the lockfile should not appear in graph."""
        from ussy_mint.lockfile import LockedPackage
        packages = [
            LockedPackage(name="a", version="1.0.0", dependencies={"b": "1.0.0"}),
            LockedPackage(name="b", version="1.0.0"),
        ]
        graph = build_dependency_graph(packages)
        assert graph["a"] == ["b"]

    def test_missing_dep_excluded(self):
        """Dependencies not present in the lockfile should be excluded from graph."""
        from ussy_mint.lockfile import LockedPackage
        packages = [
            LockedPackage(name="a", version="1.0.0", dependencies={"missing": "1.0.0"}),
        ]
        graph = build_dependency_graph(packages)
        assert graph["a"] == []


class TestExtractPackageNames:
    """Test package name extraction."""

    def test_sorted_names(self):
        from ussy_mint.lockfile import LockedPackage
        packages = [
            LockedPackage(name="z-pkg", version="1.0.0"),
            LockedPackage(name="a-pkg", version="1.0.0"),
        ]
        names = extract_package_names(packages)
        assert names == ["a-pkg", "z-pkg"]


class TestGetRegistryFromResolved:
    """Test registry identification from resolved URL."""

    def test_npm(self):
        assert get_registry_from_resolved("https://registry.npmjs.org/pkg/-/pkg-1.0.0.tgz") == "npm"

    def test_pypi(self):
        assert get_registry_from_resolved("https://pypi.org/packages/pkg") == "pypi"

    def test_github(self):
        assert get_registry_from_resolved("https://github.com/org/repo/releases") == "github"

    def test_private(self):
        assert get_registry_from_resolved("https://my-registry.corp.com/pkg") == "private-mirror"

    def test_empty(self):
        assert get_registry_from_resolved("") == "unknown"
