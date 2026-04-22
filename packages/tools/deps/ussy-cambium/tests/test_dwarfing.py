"""Tests for Cambium dwarfing module."""

from __future__ import annotations

import pytest

from ussy_cambium.dwarfing import (
    analyze_dependency_chain,
    compute_chain_capability,
    compute_dwarf_factor,
    find_dwarfing_dependencies,
    format_dwarfing_report,
)
from ussy_cambium.models import DependencyNode, DwarfFactor


class TestComputeDwarfFactor:
    """Tests for compute_dwarf_factor."""

    def test_no_dwarfing(self):
        df = compute_dwarf_factor(0.95, 1.0)
        assert not df.is_dwarfing

    def test_dwarfing(self):
        df = compute_dwarf_factor(0.42, 1.0)
        assert df.is_dwarfing

    def test_equal_capability(self):
        df = compute_dwarf_factor(1.0, 1.0)
        assert df.dwarf_ratio == pytest.approx(1.0)
        assert not df.is_dwarfing


class TestAnalyzeDependencyChain:
    """Tests for analyze_dependency_chain."""

    def test_single_node(self):
        root = DependencyNode(name="app", capability=1.0)
        result = analyze_dependency_chain(root)
        assert len(result) == 1
        assert result[0]["name"] == "app"

    def test_linear_chain(self):
        root = DependencyNode(name="app", capability=1.0, children=[
            DependencyNode(name="lib_a", capability=0.9),
        ])
        result = analyze_dependency_chain(root)
        assert len(result) == 2

    def test_dwarfing_detected(self):
        root = DependencyNode(name="app", capability=1.0, children=[
            DependencyNode(name="sync-lib", capability=0.4),
        ])
        result = analyze_dependency_chain(root)
        dwarfing = [r for r in result if r["is_dwarfing"]]
        assert len(dwarfing) == 1
        assert dwarfing[0]["name"] == "sync-lib"

    def test_nested_chain(self):
        root = DependencyNode(name="webapp", capability=1.0, children=[
            DependencyNode(name="fastapi", capability=0.95, children=[
                DependencyNode(name="pydantic", capability=0.88),
            ]),
            DependencyNode(name="sync-lib", capability=0.42, children=[
                DependencyNode(name="blocking-io", capability=0.31),
            ]),
        ])
        result = analyze_dependency_chain(root)
        assert len(result) == 5
        dwarfing = [r for r in result if r["is_dwarfing"]]
        assert len(dwarfing) >= 1


class TestFindDwarfingDependencies:
    """Tests for find_dwarfing_dependencies."""

    def test_find_dwarfing(self):
        root = DependencyNode(name="app", capability=1.0, children=[
            DependencyNode(name="good-lib", capability=0.95),
            DependencyNode(name="bad-lib", capability=0.3),
        ])
        result = find_dwarfing_dependencies(root)
        assert len(result) == 1
        assert result[0]["name"] == "bad-lib"

    def test_no_dwarfing(self):
        root = DependencyNode(name="app", capability=1.0, children=[
            DependencyNode(name="lib_a", capability=0.95),
            DependencyNode(name="lib_b", capability=0.85),
        ])
        result = find_dwarfing_dependencies(root)
        assert len(result) == 0


class TestComputeChainCapability:
    """Tests for compute_chain_capability."""

    def test_single_node(self):
        root = DependencyNode(name="app", capability=1.0)
        assert compute_chain_capability(root) == pytest.approx(1.0)

    def test_chain_with_children(self):
        root = DependencyNode(name="app", capability=0.9, children=[
            DependencyNode(name="lib", capability=0.8),
        ])
        cap = compute_chain_capability(root)
        expected = 1.0 / (1.0 / 0.9 + 1.0 / 0.8)
        assert cap == pytest.approx(expected, rel=0.01)


class TestFormatDwarfingReport:
    """Tests for format_dwarfing_report."""

    def test_report_with_dwarfing(self):
        root = DependencyNode(name="webapp", capability=1.0, children=[
            DependencyNode(name="fastapi", capability=0.95),
            DependencyNode(name="sync-lib", capability=0.42),
        ])
        report = format_dwarfing_report(root)
        assert "Dwarf Factor Analysis" in report
        assert "sync-lib" in report
        assert "DWARFING" in report

    def test_report_without_dwarfing(self):
        root = DependencyNode(name="app", capability=1.0, children=[
            DependencyNode(name="good-lib", capability=0.95),
        ])
        report = format_dwarfing_report(root)
        assert "No dwarfing dependencies detected" in report
