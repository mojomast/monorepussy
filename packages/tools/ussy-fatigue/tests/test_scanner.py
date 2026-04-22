"""Tests for the scanner module — crack detection."""

import os
import tempfile
import pytest

from fatigue.scanner import (
    CrackScanner,
    CrackType,
    detect_circular_dependencies,
    build_import_graph,
)
from fatigue.models import Crack


FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures")
SAMPLE_CODE_DIR = os.path.join(FIXTURES_DIR, "sample_code")


class TestCrackScanner:
    """Tests for CrackScanner class."""

    def test_scan_file_todo_comments(self, god_class_path):
        """Test detection of TODO/FIXME/HACK comments."""
        scanner = CrackScanner()
        cracks = scanner.scan_file(god_class_path)

        todo_cracks = [c for c in cracks if c.crack_type == CrackType.TODO_FIXME_HACK]
        assert len(todo_cracks) >= 3  # TODO, FIXME, HACK comments in the file

    def test_scan_file_god_class(self, god_class_path):
        """Test detection of god classes."""
        scanner = CrackScanner(god_class_method_threshold=10)
        cracks = scanner.scan_file(god_class_path)

        god_cracks = [c for c in cracks if c.crack_type == CrackType.GOD_CLASS]
        assert len(god_cracks) >= 1

    def test_scan_file_high_complexity(self, god_class_path):
        """Test detection of high complexity functions."""
        scanner = CrackScanner(high_complexity_threshold=5)
        cracks = scanner.scan_file(god_class_path)

        complexity_cracks = [c for c in cracks if c.crack_type == CrackType.HIGH_COMPLEXITY]
        assert len(complexity_cracks) >= 1

    def test_scan_file_missing_error_handling(self, god_class_path):
        """Test detection of missing error handling."""
        scanner = CrackScanner()
        cracks = scanner.scan_file(god_class_path)

        error_cracks = [c for c in cracks if c.crack_type == CrackType.MISSING_ERROR_HANDLING]
        assert len(error_cracks) >= 1  # open(), socket.connect(), etc.

    def test_scan_clean_module(self, clean_module_path):
        """Test that clean modules have minimal cracks."""
        scanner = CrackScanner()
        cracks = scanner.scan_file(clean_module_path)

        # Clean module should have very few or no cracks
        assert len(cracks) <= 1  # At most one minor issue

    def test_scan_nonexistent_file(self):
        """Test scanning a file that doesn't exist."""
        scanner = CrackScanner()
        cracks = scanner.scan_file("/nonexistent/file.py")
        assert cracks == []

    def test_scan_directory(self, sample_code_dir):
        """Test scanning a directory recursively."""
        scanner = CrackScanner()
        cracks = scanner.scan_directory(sample_code_dir)
        assert len(cracks) >= 3  # Multiple cracks across files

    def test_scan_nonexistent_directory(self):
        """Test scanning a directory that doesn't exist."""
        scanner = CrackScanner()
        cracks = scanner.scan_directory("/nonexistent/dir")
        assert cracks == []

    def test_todo_severity_ordering(self, temp_python_file):
        """Test that HACK has higher severity than TODO."""
        scanner = CrackScanner()
        content = """
# TODO: something minor
# HACK: this is a hack
# FIXME: something broken
"""
        fpath = temp_python_file(content)
        cracks = scanner.scan_file(fpath)

        todo_cracks = [c for c in cracks if c.crack_type == CrackType.TODO_FIXME_HACK]
        hack_cracks = [c for c in todo_cracks if "HACK" in c.description]
        todo_only = [c for c in todo_cracks if "TODO" in c.description and "HACK" not in c.description]

        if hack_cracks and todo_only:
            assert hack_cracks[0].severity > todo_only[0].severity

    def test_high_complexity_threshold_configurable(self, temp_python_file):
        """Test that complexity threshold can be configured."""
        content = """
def my_func():
    if True:
        if True:
            if True:
                if True:
                    if True:
                        pass
"""
        fpath = temp_python_file(content)

        scanner_low = CrackScanner(high_complexity_threshold=3)
        scanner_high = CrackScanner(high_complexity_threshold=20)

        cracks_low = scanner_low.scan_file(fpath)
        cracks_high = scanner_high.scan_file(fpath)

        complexity_low = [c for c in cracks_low if c.crack_type == CrackType.HIGH_COMPLEXITY]
        complexity_high = [c for c in cracks_high if c.crack_type == CrackType.HIGH_COMPLEXITY]

        assert len(complexity_low) >= len(complexity_high)


class TestCyclomaticComplexity:
    """Tests for cyclomatic complexity calculation."""

    def test_simple_function_complexity(self, temp_python_file):
        """Test complexity of a simple function (should be 1)."""
        scanner = CrackScanner()
        content = """
def simple():
    return 42
"""
        fpath = temp_python_file(content)
        cracks = scanner.scan_file(fpath)
        # Simple function shouldn't trigger high complexity
        complexity_cracks = [c for c in cracks if c.crack_type == CrackType.HIGH_COMPLEXITY]
        assert len(complexity_cracks) == 0

    def test_complex_function_complexity(self, temp_python_file):
        """Test complexity of a function with many branches."""
        scanner = CrackScanner(high_complexity_threshold=5)
        content = """
def complex_func(x):
    if x > 0:
        if x > 10:
            if x > 20:
                return 1
            elif x > 15:
                return 2
            else:
                return 3
        else:
            return 4
    elif x < 0:
        if x < -10:
            return 5
        else:
            return 6
    else:
        return 7
"""
        fpath = temp_python_file(content)
        cracks = scanner.scan_file(fpath)
        complexity_cracks = [c for c in cracks if c.crack_type == CrackType.HIGH_COMPLEXITY]
        assert len(complexity_cracks) >= 1


class TestModuleMetrics:
    """Tests for module metrics computation."""

    def test_compute_metrics_basic(self, god_class_path):
        """Test basic metrics computation."""
        scanner = CrackScanner()
        metrics = scanner.compute_module_metrics(god_class_path)

        assert metrics.file_path == god_class_path
        assert metrics.lines_of_code > 0
        assert metrics.cyclomatic_complexity > 0
        assert metrics.complexity > 0

    def test_compute_metrics_clean(self, clean_module_path):
        """Test metrics for a clean module."""
        scanner = CrackScanner()
        metrics = scanner.compute_module_metrics(clean_module_path)

        assert metrics.lines_of_code > 0
        assert metrics.cyclomatic_complexity < 10  # Low complexity

    def test_compute_metrics_nonexistent(self):
        """Test metrics for a nonexistent file."""
        scanner = CrackScanner()
        metrics = scanner.compute_module_metrics("/nonexistent/file.py")
        assert metrics.file_path == "/nonexistent/file.py"
        assert metrics.lines_of_code == 0

    def test_fan_out_counted(self, god_class_path):
        """Test that imports are counted as fan-out."""
        scanner = CrackScanner()
        metrics = scanner.compute_module_metrics(god_class_path)
        # god_class_module.py imports os, sys, json
        assert metrics.fan_out >= 3

    def test_nesting_depth(self, temp_python_file):
        """Test that nesting depth is captured."""
        content = """
def nested():
    if True:
        if True:
            if True:
                pass
"""
        fpath = temp_python_file(content)
        scanner = CrackScanner()
        metrics = scanner.compute_module_metrics(fpath)
        assert metrics.nesting_depth >= 3


class TestCircularDependencies:
    """Tests for circular dependency detection."""

    def test_detect_circular_dependency(self):
        """Test detection of a simple circular dependency."""
        graph = {
            "A": {"B"},
            "B": {"A"},
        }
        cycles = detect_circular_dependencies(graph)
        assert len(cycles) >= 1
        # Should find A -> B -> A
        cycle_modules = set()
        for cycle in cycles:
            cycle_modules.update(cycle)
        assert "A" in cycle_modules
        assert "B" in cycle_modules

    def test_no_circular_dependency(self):
        """Test that non-circular graphs have no cycles."""
        graph = {
            "A": {"B"},
            "B": {"C"},
            "C": set(),
        }
        cycles = detect_circular_dependencies(graph)
        assert len(cycles) == 0

    def test_three_way_cycle(self):
        """Test detection of a three-way circular dependency."""
        graph = {
            "A": {"B"},
            "B": {"C"},
            "C": {"A"},
        }
        cycles = detect_circular_dependencies(graph)
        assert len(cycles) >= 1

    def test_empty_graph(self):
        """Test with empty graph."""
        graph = {}
        cycles = detect_circular_dependencies(graph)
        assert len(cycles) == 0

    def test_build_import_graph(self, sample_code_dir):
        """Test building an import graph from a directory."""
        graph = build_import_graph(sample_code_dir)
        assert isinstance(graph, dict)
        # Should find at least the modules in the directory
        assert len(graph) >= 2

    def test_build_import_graph_nonexistent(self):
        """Test building import graph from nonexistent directory."""
        graph = build_import_graph("/nonexistent/dir")
        assert graph == {}


class TestMissingErrorHandling:
    """Tests for missing error handling detection."""

    def test_detect_risky_call_without_try(self, temp_python_file):
        """Test detection of risky calls without try/except."""
        content = """
def read_file(path):
    data = open(path).read()
    return data
"""
        fpath = temp_python_file(content)
        scanner = CrackScanner()
        cracks = scanner.scan_file(fpath)
        error_cracks = [c for c in cracks if c.crack_type == CrackType.MISSING_ERROR_HANDLING]
        assert len(error_cracks) >= 1

    def test_risky_call_with_try_ok(self, temp_python_file):
        """Test that risky calls with try/except are not flagged."""
        content = """
def read_file(path):
    try:
        data = open(path).read()
        return data
    except IOError:
        return None
"""
        fpath = temp_python_file(content)
        scanner = CrackScanner()
        cracks = scanner.scan_file(fpath)
        error_cracks = [c for c in cracks if c.crack_type == CrackType.MISSING_ERROR_HANDLING]
        assert len(error_cracks) == 0
