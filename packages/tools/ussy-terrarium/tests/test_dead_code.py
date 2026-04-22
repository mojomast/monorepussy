"""Tests for the dead code detection module."""

import os
import tempfile

import pytest

from terrarium.metrics.dead_code import (
    ImportCollector,
    ExportCollector,
    find_unused_exports,
    analyze_file_dead_code,
    scan_project_dead_code,
)


class TestImportCollector:
    """Tests for the AST import collector."""

    def test_collect_import(self):
        """Collect simple imports."""
        source = "import os\nimport sys\n"
        import ast
        tree = ast.parse(source)
        collector = ImportCollector()
        collector.visit(tree)
        assert "os" in collector.imports
        assert "sys" in collector.imports

    def test_collect_from_import(self):
        """Collect from-imports."""
        source = "from os.path import join, exists\n"
        import ast
        tree = ast.parse(source)
        collector = ImportCollector()
        collector.visit(tree)
        assert "os.path" in collector.from_imports
        assert "join" in collector.from_imports["os.path"]
        assert "exists" in collector.from_imports["os.path"]

    def test_no_imports(self):
        """Source with no imports."""
        source = "x = 1\n"
        import ast
        tree = ast.parse(source)
        collector = ImportCollector()
        collector.visit(tree)
        assert collector.imports == []
        assert collector.from_imports == {}


class TestExportCollector:
    """Tests for the AST export collector."""

    def test_collect_functions(self):
        """Collect non-private function definitions."""
        source = "def foo():\n    pass\n\ndef _private():\n    pass\n"
        import ast
        tree = ast.parse(source)
        collector = ExportCollector()
        collector.visit(tree)
        assert "foo" in collector.exports
        assert "_private" not in collector.exports

    def test_collect_classes(self):
        """Collect non-private class definitions."""
        source = "class MyClass:\n    pass\n\nclass _Private:\n    pass\n"
        import ast
        tree = ast.parse(source)
        collector = ExportCollector()
        collector.visit(tree)
        assert "MyClass" in collector.exports
        assert "_Private" not in collector.exports

    def test_collect_assignments(self):
        """Collect non-private top-level assignments."""
        source = "CONSTANT = 42\n_internal = 7\n"
        import ast
        tree = ast.parse(source)
        collector = ExportCollector()
        collector.visit(tree)
        assert "CONSTANT" in collector.exports
        assert "_internal" not in collector.exports


class TestFindUnusedExports:
    """Tests for unused export detection."""

    def test_with_project_imports(self):
        """Find exports not present in project imports."""
        source = "def used_func():\n    pass\n\ndef unused_func():\n    pass\n"
        project_imports = {"used_func"}
        unused = find_unused_exports(source, project_imports)
        assert "unused_func" in unused
        assert "used_func" not in unused

    def test_without_project_imports(self):
        """Without project imports, returns empty list."""
        source = "def func():\n    pass\n"
        unused = find_unused_exports(source)
        assert unused == []

    def test_syntax_error(self):
        """Syntax errors return empty list."""
        unused = find_unused_exports("def broken(:\n", {"something"})
        assert unused == []


class TestAnalyzeFileDeadCode:
    """Tests for file-level dead code analysis."""

    def test_analyze_real_file(self, temp_project_dir):
        """Analyze a real file."""
        filepath = os.path.join(temp_project_dir, "src", "utils.py")
        exports, imports = analyze_file_dead_code(filepath)
        assert isinstance(exports, list)
        assert isinstance(imports, list)
        assert "add" in exports
        assert "mul" in exports

    def test_nonexistent_file(self):
        """Non-existent file returns empty lists."""
        exports, imports = analyze_file_dead_code("/nonexistent/file.py")
        assert exports == []
        assert imports == []


class TestScanProjectDeadCode:
    """Tests for project-wide dead code scanning."""

    def test_scan_project(self, temp_project_dir):
        """Scan a project for dead code."""
        result = scan_project_dead_code(temp_project_dir)
        assert isinstance(result, dict)
        # At least some files should have potentially unused exports
        # (since nothing imports from the project itself)

    def test_scan_empty_directory(self):
        """Empty directory returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = scan_project_dead_code(tmpdir)
            assert result == {}
