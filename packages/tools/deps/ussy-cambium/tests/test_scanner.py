"""Tests for Cambium scanner module."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from cambium.scanner import (
    format_scan_report,
    scan_project,
    _parse_dependencies,
    _build_dependency_tree,
)
from cambium.models import DependencyNode


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestScanProject:
    """Tests for scan_project."""

    def test_scan_directory(self):
        results = scan_project(FIXTURES_DIR)
        assert results["project_path"] == os.path.abspath(FIXTURES_DIR)
        assert results["modules_scanned"] > 0

    def test_scan_single_file(self):
        path = os.path.join(FIXTURES_DIR, "consumer.py")
        results = scan_project(path)
        assert results["modules_scanned"] >= 1
        assert "consumer" in results["module_names"]

    def test_scan_nonexistent(self):
        results = scan_project("/nonexistent/path")
        assert results["modules_scanned"] == 0

    def test_scan_results_structure(self):
        results = scan_project(FIXTURES_DIR)
        assert "project_path" in results
        assert "modules_scanned" in results
        assert "module_names" in results
        assert "dependencies_found" in results
        assert "pair_analysis" in results
        assert "dwarfing_analysis" in results


class TestParseDependencies:
    """Tests for _parse_dependencies."""

    def test_parse_requirements_txt(self):
        deps = _parse_dependencies(FIXTURES_DIR)
        assert len(deps) > 0
        names = [d["name"] for d in deps]
        assert "requests" in names
        assert "flask" in names
        assert "numpy" in names

    def test_parse_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            deps = _parse_dependencies(tmpdir)
            assert len(deps) == 0


class TestBuildDependencyTree:
    """Tests for _build_dependency_tree."""

    def test_basic_tree(self):
        deps = [
            {"name": "requests", "version_spec": ">=2.28"},
            {"name": "asyncio-lib", "version_spec": ">=1.0"},
        ]
        tree = _build_dependency_tree(deps)
        assert tree.name == "project"
        assert len(tree.children) == 2

    def test_async_capability_heuristic(self):
        deps = [{"name": "aiohttp", "version_spec": ""}]
        tree = _build_dependency_tree(deps)
        assert tree.children[0].capability > 0.9

    def test_sync_capability_heuristic(self):
        deps = [{"name": "sync-blocking-lib", "version_spec": ""}]
        tree = _build_dependency_tree(deps)
        assert tree.children[0].capability < 0.5


class TestFormatScanReport:
    """Tests for format_scan_report."""

    def test_basic_report(self):
        results = scan_project(FIXTURES_DIR)
        report = format_scan_report(results)
        assert "Cambium Project Scan Report" in report
        assert "Modules scanned" in report

    def test_empty_results(self):
        results = {
            "project_path": "/tmp/test",
            "modules_scanned": 0,
            "module_names": [],
            "dependencies_found": 0,
            "dependencies": [],
            "pair_analysis": [],
            "dwarfing_analysis": [],
            "chain_capability": 1.0,
        }
        report = format_scan_report(results)
        assert "Modules scanned: 0" in report
