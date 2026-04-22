"""Tests for endemic.scanner module."""

import os
import pytest
import tempfile

from ussy_endemic.scanner import PatternScanner, ASTChecker, BUILTIN_PATTERNS
from ussy_endemic.models import PatternType, Compartment


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


class TestASTChecker:
    def test_bare_except(self):
        import ast
        code = """
try:
    x = 1
except:
    pass
"""
        tree = ast.parse(code)
        result = ASTChecker.bare_except(tree)
        assert len(result) == 1

    def test_no_bare_except(self):
        import ast
        code = """
try:
    x = 1
except ValueError:
    pass
"""
        tree = ast.parse(code)
        result = ASTChecker.bare_except(tree)
        assert len(result) == 0

    def test_broad_except(self):
        import ast
        code = """
try:
    x = 1
except Exception:
    pass
"""
        tree = ast.parse(code)
        result = ASTChecker.broad_except(tree)
        assert len(result) == 1

    def test_pass_in_except(self):
        import ast
        code = """
try:
    x = 1
except ValueError:
    pass
"""
        tree = ast.parse(code)
        result = ASTChecker.pass_in_except(tree)
        assert len(result) == 1

    def test_god_class(self):
        import ast
        methods = "\n".join(f"    def method{i}(self): pass" for i in range(16))
        code = f"class BigClass:\n{methods}\n"
        tree = ast.parse(code)
        result = ASTChecker.god_class(tree)
        assert len(result) == 1

    def test_not_god_class(self):
        import ast
        methods = "\n".join(f"    def method{i}(self): pass" for i in range(5))
        code = f"class SmallClass:\n{methods}\n"
        tree = ast.parse(code)
        result = ASTChecker.god_class(tree)
        assert len(result) == 0

    def test_print_debugging(self):
        import ast
        code = 'print("hello")\n'
        tree = ast.parse(code)
        result = ASTChecker.print_debugging(tree)
        assert len(result) == 1

    def test_no_type_hints(self):
        import ast
        code = "def foo(x):\n    return x\n"
        tree = ast.parse(code)
        result = ASTChecker.no_type_hints(tree)
        assert len(result) == 1

    def test_with_type_hints(self):
        import ast
        code = "def foo(x: int) -> int:\n    return x\n"
        tree = ast.parse(code)
        result = ASTChecker.no_type_hints(tree)
        assert len(result) == 0

    def test_dunder_methods_excluded(self):
        import ast
        code = "def __init__(self):\n    pass\n"
        tree = ast.parse(code)
        result = ASTChecker.no_type_hints(tree)
        assert len(result) == 0


class TestPatternScanner:
    def test_default_patterns(self):
        scanner = PatternScanner()
        assert len(scanner.patterns) > 0

    def test_scan_bad_fixture(self):
        scanner = PatternScanner()
        filepath = os.path.join(FIXTURES_DIR, "sample_bad.py")
        results = scanner.scan_file(filepath)
        assert "bare-except" in results
        assert "pass-in-except" in results
        assert "broad-except" in results

    def test_scan_good_fixture(self):
        scanner = PatternScanner()
        filepath = os.path.join(FIXTURES_DIR, "sample_good.py")
        results = scanner.scan_file(filepath)
        # Should have structured-logging
        assert "structured-logging" in results
        # Should have type-hinted-returns
        assert "type-hinted-returns" in results

    def test_scan_nonexistent_file(self):
        scanner = PatternScanner()
        results = scanner.scan_file("/nonexistent/path.py")
        assert results == {}

    def test_scan_directory(self):
        scanner = PatternScanner()
        results = scanner.scan_path(FIXTURES_DIR)
        assert len(results) > 0

    def test_scan_path_is_file(self):
        scanner = PatternScanner()
        filepath = os.path.join(FIXTURES_DIR, "sample_bad.py")
        results = scanner.scan_path(filepath)
        assert len(results) > 0

    def test_build_modules(self):
        scanner = PatternScanner()
        filepath = os.path.join(FIXTURES_DIR, "sample_bad.py")
        scan_results = scanner.scan_path(filepath)
        modules = scanner.build_modules(scan_results)
        assert len(modules) > 0

    def test_compute_pattern_stats(self):
        scanner = PatternScanner()
        filepath = os.path.join(FIXTURES_DIR, "sample_bad.py")
        scan_results = scanner.scan_path(filepath)
        stats = scanner.compute_pattern_stats(scan_results, total_modules=4)
        # Should find bare-except with prevalence > 0
        bare_except = next(p for p in stats if p.name == "bare-except")
        assert bare_except.prevalence_count > 0

    def test_scan_with_syntax_error(self):
        """Scanner should handle files with syntax errors gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def broken(:\n")
            f.flush()
            scanner = PatternScanner()
            results = scanner.scan_file(f.name)
            # Should not crash, may still find regex patterns
            assert isinstance(results, dict)
            os.unlink(f.name)


class TestBuiltinPatterns:
    def test_all_have_names(self):
        for p in BUILTIN_PATTERNS:
            assert p["name"]

    def test_bad_patterns(self):
        bad = [p for p in BUILTIN_PATTERNS if p["pattern_type"] == PatternType.BAD]
        assert len(bad) >= 5

    def test_good_patterns(self):
        good = [p for p in BUILTIN_PATTERNS if p["pattern_type"] == PatternType.GOOD]
        assert len(good) >= 2
