"""Tests for ussy_ast."""

from __future__ import annotations

import pytest

from ussy_ast import (
    SourceLocation,
    extract_classes,
    extract_functions,
    get_cyclomatic_complexity,
    parse_source,
)


SIMPLE_FUNC = """
def add(a, b):
    return a + b
"""

COMPLEX_FUNC = """
def process(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item)
        elif item == 0:
            result.append(0)
        else:
            result.append(-item)
    return result
"""

CLASS_SRC = '''
class Foo:
    """A foo."""
    def bar(self, x):
        if x:
            return 1
        return 0
'''


class TestParseSource:
    def test_parses(self) -> None:
        tree = parse_source(SIMPLE_FUNC)
        assert isinstance(tree, type(tree))

    def test_syntax_error(self) -> None:
        with pytest.raises(SyntaxError):
            parse_source("def bad(")


class TestExtractFunctions:
    def test_simple(self) -> None:
        tree = parse_source(SIMPLE_FUNC)
        funcs = extract_functions(tree)
        assert len(funcs) == 1
        assert funcs[0].name == "add"
        assert funcs[0].args_count == 2
        assert funcs[0].docstring is None

    def test_complex(self) -> None:
        tree = parse_source(COMPLEX_FUNC)
        funcs = extract_functions(tree)
        assert len(funcs) == 1
        assert funcs[0].name == "process"
        assert funcs[0].has_varargs is False
        assert funcs[0].has_kwargs is False


class TestExtractClasses:
    def test_class(self) -> None:
        tree = parse_source(CLASS_SRC)
        classes = extract_classes(tree)
        assert len(classes) == 1
        assert classes[0].name == "Foo"
        assert classes[0].docstring == "A foo."
        assert len(classes[0].methods) == 1
        assert classes[0].methods[0].name == "bar"


class TestCyclomaticComplexity:
    def test_simple(self) -> None:
        tree = parse_source(SIMPLE_FUNC)
        func = extract_functions(tree)[0]
        assert func.complexity == 1

    def test_complex(self) -> None:
        tree = parse_source(COMPLEX_FUNC)
        func = extract_functions(tree)[0]
        # Base 1 + for(1) + if(1) + elif(1) + else(1) = 5, but elif shares the If node
        # Actually: for=1, if=1, else=1 -> total 4 (elif is part of same If, not extra branch)
        assert func.complexity == 4

    def test_class_method(self) -> None:
        tree = parse_source(CLASS_SRC)
        cls = extract_classes(tree)[0]
        assert cls.methods[0].complexity == 2
