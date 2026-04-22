"""Tests for the crucible module."""

import pytest

from assay.crucible import build_crucible, count_callers, crucible_rank_emoji, _call_name
from assay.models import (
    Category,
    ClassifiedLine,
    CrucibleEntry,
    FunctionAnalysis,
    ModuleAnalysis,
    ProjectAnalysis,
)
import ast


class TestCountCallers:
    def test_no_calls(self):
        func = FunctionAnalysis(name="f", file_path="t.py", start_line=1, end_line=1)
        mod = ModuleAnalysis(file_path="t.py", functions=[func])
        project = ProjectAnalysis(modules=[mod])
        callers = count_callers(project)
        # No actual calls in the project
        assert isinstance(callers, dict)

    def test_with_calls(self, tmp_path):
        source = "def foo():\n    return 1\n\ndef bar():\n    return foo()\n"
        f = tmp_path / "test.py"
        f.write_text(source)

        from assay.classifier import classify_source
        func_analyses = classify_source(source, str(f))
        mod = ModuleAnalysis(file_path=str(f), functions=func_analyses)
        project = ProjectAnalysis(modules=[mod])

        callers = count_callers(project)
        assert callers.get("foo", 0) >= 1


class TestBuildCrucible:
    def test_crucible_top_bottom(self):
        lines_biz = [ClassifiedLine(1, "x = 1", Category.BUSINESS)]
        func_biz = FunctionAnalysis(
            name="pure_func", file_path="a.py", start_line=1, end_line=1, lines=lines_biz,
        )
        lines_slag = [ClassifiedLine(1, "logger.debug('x')", Category.SLAG)]
        func_slag = FunctionAnalysis(
            name="waste_func", file_path="b.py", start_line=1, end_line=1, lines=lines_slag,
        )
        mod = ModuleAnalysis(file_path="a.py", functions=[func_biz, func_slag])
        project = ProjectAnalysis(modules=[mod])

        crucible = build_crucible(project)
        assert "top" in crucible
        assert "bottom" in crucible
        assert len(crucible["top"]) >= 1

    def test_crucible_ranking_order(self):
        """Higher grade functions should rank higher."""
        lines_hi = [ClassifiedLine(i, "biz", Category.BUSINESS) for i in range(5)]
        func_hi = FunctionAnalysis(
            name="high_grade", file_path="a.py", start_line=1, end_line=5, lines=lines_hi,
        )
        lines_lo = [ClassifiedLine(i, "slag", Category.SLAG) for i in range(5)]
        func_lo = FunctionAnalysis(
            name="low_grade", file_path="b.py", start_line=1, end_line=5, lines=lines_lo,
        )
        mod = ModuleAnalysis(file_path="a.py", functions=[func_hi, func_lo])
        project = ProjectAnalysis(modules=[mod])

        crucible = build_crucible(project)
        top = crucible["top"]
        assert top[0].function.name == "high_grade"


class TestCrucibleRankEmoji:
    def test_diamond3(self):
        lines = [ClassifiedLine(1, "x", Category.BUSINESS)]
        func = FunctionAnalysis(name="f", file_path="t.py", start_line=1, end_line=1, lines=lines)
        entry = CrucibleEntry(function=func, caller_count=10)
        assert crucible_rank_emoji(entry) == "\U0001f48e\U0001f48e\U0001f48e"

    def test_warning(self):
        lines = [ClassifiedLine(1, "x", Category.SLAG)]
        func = FunctionAnalysis(name="f", file_path="t.py", start_line=1, end_line=1, lines=lines)
        entry = CrucibleEntry(function=func, caller_count=0)
        assert crucible_rank_emoji(entry) == "\u26a0\ufe0f"


class TestCallName:
    def test_simple_call(self):
        tree = ast.parse("foo()")
        call = tree.body[0].value
        assert _call_name(call) == "foo"

    def test_attribute_call(self):
        tree = ast.parse("obj.method()")
        call = tree.body[0].value
        assert _call_name(call) == "method"

    def test_complex_call(self):
        tree = ast.parse("(lambda: 1)()")
        call = tree.body[0].value
        assert _call_name(call) is None
