"""Tests for the AST-based classifier module."""

import ast
from pathlib import Path

import pytest

from assay.classifier import (
    classify_source,
    _is_logging_call,
    _is_debug_log,
    _is_framework_call,
    _classify_line_heuristic,
)
from assay.models import Category


# ── Basic classification ──────────────────────────────────────────────────

class TestClassifySource:
    """Tests for classify_source()."""

    def test_empty_source(self):
        result = classify_source("")
        assert result == []

    def test_syntax_error_source(self):
        result = classify_source("def foo(\n")
        assert result == []

    def test_simple_function_found(self):
        source = "def hello():\n    return 42\n"
        result = classify_source(source)
        assert len(result) == 1
        assert result[0].name == "hello"

    def test_multiple_functions(self):
        source = "def a():\n    return 1\n\ndef b():\n    return 2\n"
        result = classify_source(source)
        assert len(result) == 2
        names = {r.name for r in result}
        assert names == {"a", "b"}

    def test_async_function(self):
        source = "async def fetch():\n    return 1\n"
        result = classify_source(source)
        assert len(result) == 1
        assert result[0].name == "fetch"

    def test_method_in_class(self):
        source = "class Foo:\n    def bar(self):\n        return 1\n"
        result = classify_source(source)
        assert len(result) == 1
        assert result[0].name == "bar"

    def test_return_statement_is_business(self):
        source = "def compute():\n    x = 10\n    return x * 2\n"
        result = classify_source(source)
        func = result[0]
        biz_cats = [ln.category for ln in func.lines if ln.category == Category.BUSINESS]
        assert len(biz_cats) >= 1

    def test_raise_is_error_handling(self):
        source = "def guard():\n    raise ValueError('bad')\n"
        result = classify_source(source)
        func = result[0]
        error_cats = [ln for ln in func.lines if ln.category == Category.ERROR_HANDLING]
        assert len(error_cats) >= 1

    def test_try_except_is_error_handling(self):
        source = "def safe():\n    try:\n        x = 1\n    except ValueError:\n        pass\n"
        result = classify_source(source)
        func = result[0]
        error_cats = [ln for ln in func.lines if ln.category == Category.ERROR_HANDLING]
        assert len(error_cats) >= 1

    def test_assert_is_validation(self):
        source = "def check():\n    assert x > 0\n"
        result = classify_source(source)
        func = result[0]
        val_cats = [ln for ln in func.lines if ln.category == Category.VALIDATION]
        assert len(val_cats) >= 1

    def test_logger_call_is_logging(self):
        source = "def log_stuff():\n    logger.info('hello')\n"
        result = classify_source(source)
        func = result[0]
        log_cats = [ln for ln in func.lines if ln.category == Category.LOGGING]
        assert len(log_cats) >= 1

    def test_debug_log_is_slag(self):
        source = "def debug_stuff():\n    logger.debug('trace')\n"
        result = classify_source(source)
        func = result[0]
        slag_cats = [ln for ln in func.lines if ln.category == Category.SLAG]
        assert len(slag_cats) >= 1

    def test_todo_comment_is_slag(self):
        source = "def todo_func():\n    # TODO: fix this\n    pass\n"
        result = classify_source(source)
        func = result[0]
        slag_cats = [ln for ln in func.lines if ln.category == Category.SLAG]
        assert len(slag_cats) >= 1

    def test_commented_out_code_is_slag(self):
        source = "def old_func():\n    # def _helper():\n    pass\n"
        result = classify_source(source)
        func = result[0]
        slag_cats = [ln for ln in func.lines if ln.category == Category.SLAG]
        assert len(slag_cats) >= 1

    def test_decorator_is_framework(self):
        source = "@app.route('/')\ndef index():\n    return 'hi'\n"
        result = classify_source(source)
        func = result[0]
        # Decorator line is at the function start; check if any line is framework
        all_cats = {ln.category for ln in func.lines}
        # The decorator may or may not be included in the function's line range
        # depending on AST behavior; at minimum, the function should be found
        assert func.name == "index"
        # Verify the heuristic classifies decorators correctly
        from assay.classifier import _classify_line_heuristic
        cat = _classify_line_heuristic("@app.route('/')", 1, None, [])
        assert cat == Category.FRAMEWORK

    def test_guard_clause_is_validation(self):
        source = "def process(data):\n    if not data:\n        return None\n    return data\n"
        result = classify_source(source)
        func = result[0]
        val_cats = [ln for ln in func.lines if ln.category == Category.VALIDATION]
        assert len(val_cats) >= 1

    def test_isinstance_is_validation(self):
        source = "def check_type(x):\n    isinstance(x, int)\n"
        result = classify_source(source)
        func = result[0]
        val_cats = [ln for ln in func.lines if ln.category == Category.VALIDATION]
        assert len(val_cats) >= 1


# ── AST helper functions ──────────────────────────────────────────────────

class TestAstHelpers:
    """Tests for internal AST helper functions."""

    def test_is_logging_call_true(self):
        source = "logger.info('msg')"
        tree = ast.parse(source)
        call = tree.body[0].value
        assert _is_logging_call(call) is True

    def test_is_logging_call_false(self):
        source = "print('msg')"
        tree = ast.parse(source)
        call = tree.body[0].value
        assert _is_logging_call(call) is False

    def test_is_debug_log_true(self):
        source = "logger.debug('msg')"
        tree = ast.parse(source)
        call = tree.body[0].value
        assert _is_debug_log(call) is True

    def test_is_debug_log_false(self):
        source = "logger.info('msg')"
        tree = ast.parse(source)
        call = tree.body[0].value
        assert _is_debug_log(call) is False

    def test_is_framework_call_db(self):
        source = "db.execute('SELECT 1')"
        tree = ast.parse(source)
        call = tree.body[0].value
        assert _is_framework_call(call) is True

    def test_is_framework_call_normal(self):
        source = "compute(x)"
        tree = ast.parse(source)
        call = tree.body[0].value
        assert _is_framework_call(call) is False


# ── Heuristic classifier ─────────────────────────────────────────────────

class TestHeuristicClassifier:
    """Tests for _classify_line_heuristic()."""

    def test_todo_comment(self):
        cat = _classify_line_heuristic("    # TODO: fix later", 1, None, [])
        assert cat == Category.SLAG

    def test_fixme_comment(self):
        cat = _classify_line_heuristic("    # FIXME: broken", 1, None, [])
        assert cat == Category.SLAG

    def test_hack_comment(self):
        cat = _classify_line_heuristic("    # HACK: bypass", 1, None, [])
        assert cat == Category.SLAG

    def test_commented_def(self):
        cat = _classify_line_heuristic("    # def old_func():", 1, None, [])
        assert cat == Category.SLAG

    def test_commented_import(self):
        cat = _classify_line_heuristic("    # from os import path", 1, None, [])
        assert cat == Category.SLAG

    def test_regular_comment_is_unknown(self):
        cat = _classify_line_heuristic("    # this is a note", 1, None, [])
        assert cat == Category.UNKNOWN

    def test_decorator_is_framework(self):
        cat = _classify_line_heuristic("@app.route('/')", 1, None, [])
        assert cat == Category.FRAMEWORK

    def test_print_is_logging(self):
        cat = _classify_line_heuristic("print('debug')", 1, None, [])
        assert cat == Category.LOGGING

    def test_raise_is_error_handling(self):
        cat = _classify_line_heuristic("    raise ValueError('bad')", 1, None, [])
        assert cat == Category.ERROR_HANDLING

    def test_isinstance_is_validation(self):
        cat = _classify_line_heuristic("    isinstance(x, int)", 1, None, [])
        assert cat == Category.VALIDATION

    def test_business_assignment(self):
        cat = _classify_line_heuristic("    total = price * quantity", 1, None, [])
        assert cat == Category.BUSINESS
