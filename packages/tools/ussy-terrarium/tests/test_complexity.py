"""Tests for the complexity analysis module."""

import ast
import os
import tempfile

import pytest

from terrarium.metrics.complexity import (
    ComplexityVisitor,
    analyze_complexity,
    analyze_file_complexity,
    analyze_directory_complexity,
)


class TestComplexityVisitor:
    """Tests for the AST complexity visitor."""

    def test_simple_function(self):
        """Simple function has base complexity of 1."""
        source = "def foo():\n    return 1\n"
        total, functions = analyze_complexity(source)
        assert total == 1
        assert len(functions) == 1
        assert functions[0]["name"] == "foo"
        assert functions[0]["complexity"] == 1

    def test_if_statement(self):
        """If statement increases complexity by 1."""
        source = "def foo(x):\n    if x > 0:\n        return x\n    return -x\n"
        total, functions = analyze_complexity(source)
        assert total == 2  # base 1 + if 1
        assert functions[0]["complexity"] == 2

    def test_for_loop(self):
        """For loop increases complexity by 1."""
        source = "def foo(items):\n    for item in items:\n        print(item)\n"
        total, functions = analyze_complexity(source)
        assert total == 2

    def test_while_loop(self):
        """While loop increases complexity by 1."""
        source = "def foo(n):\n    while n > 0:\n        n -= 1\n"
        total, functions = analyze_complexity(source)
        assert total == 2

    def test_try_except(self):
        """Except handler increases complexity."""
        source = "def foo():\n    try:\n        x = 1\n    except ValueError:\n        pass\n"
        total, functions = analyze_complexity(source)
        assert total == 2

    def test_with_statement(self):
        """With statement increases complexity."""
        source = "def foo():\n    with open('f') as f:\n        pass\n"
        total, functions = analyze_complexity(source)
        assert total == 2

    def test_boolean_op(self):
        """Boolean 'and'/'or' increases complexity."""
        source = "def foo(a, b):\n    if a and b:\n        return True\n"
        total, functions = analyze_complexity(source)
        assert total == 3  # base + if + boolop

    def test_multiple_functions(self):
        """Each function is tracked separately."""
        source = "def simple():\n    return 1\n\ndef complex(x):\n    if x:\n        return x\n"
        total, functions = analyze_complexity(source)
        assert total == 3  # 1 + 2
        assert len(functions) == 2

    def test_async_function(self):
        """Async functions are handled."""
        source = "async def foo():\n    return 1\n"
        total, functions = analyze_complexity(source)
        assert total == 1
        assert functions[0]["name"] == "foo"

    def test_nested_complexity(self):
        """Nested control flow increases complexity."""
        source = '''
def nested(data):
    if data:
        for item in data:
            if item > 0:
                try:
                    process(item)
                except Exception:
                    pass
    return data
'''
        total, functions = analyze_complexity(source)
        assert total == 5  # base + if + for + if + except

    def test_syntax_error(self):
        """Syntax errors return 0 complexity."""
        source = "def broken(:\n    return\n"
        total, functions = analyze_complexity(source)
        assert total == 0
        assert functions == []

    def test_empty_source(self):
        """Empty source has 0 complexity."""
        total, functions = analyze_complexity("")
        assert total == 0
        assert functions == []

    def test_class_methods(self):
        """Methods inside classes are tracked."""
        source = '''
class MyClass:
    def method_a(self):
        if True:
            pass

    def method_b(self):
        return 1
'''
        total, functions = analyze_complexity(source)
        assert total == 3  # 2 + 1
        assert len(functions) == 2


class TestAnalyzeFileComplexity:
    """Tests for file-level complexity analysis."""

    def test_analyze_real_file(self, temp_project_dir):
        """Analyze complexity of a real file."""
        filepath = os.path.join(temp_project_dir, "src", "utils.py")
        total, functions = analyze_file_complexity(filepath)
        assert total > 0
        assert len(functions) >= 2  # add, mul

    def test_analyze_nonexistent_file(self):
        """Non-existent file returns 0 complexity."""
        total, functions = analyze_file_complexity("/nonexistent/file.py")
        assert total == 0
        assert functions == []

    def test_analyze_complex_file(self, temp_project_dir):
        """Complex file has higher complexity than simple file."""
        simple_path = os.path.join(temp_project_dir, "src", "utils.py")
        complex_path = os.path.join(temp_project_dir, "src", "complex.py")
        simple_total, _ = analyze_file_complexity(simple_path)
        complex_total, _ = analyze_file_complexity(complex_path)
        assert complex_total > simple_total


class TestAnalyzeDirectoryComplexity:
    """Tests for directory-level complexity analysis."""

    def test_analyze_directory(self, temp_project_dir):
        """Analyze all Python files in a directory."""
        results = analyze_directory_complexity(temp_project_dir)
        assert len(results) > 0
        # Should find at least our src/ files
        src_files = [p for p in results if p.startswith("src")]
        assert len(src_files) >= 3

    def test_empty_directory(self):
        """Empty directory returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = analyze_directory_complexity(tmpdir)
            assert results == {}
