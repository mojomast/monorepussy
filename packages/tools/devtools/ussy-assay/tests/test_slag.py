"""Tests for the slag detection module."""

from pathlib import Path

import pytest

from assay.slag import (
    detect_slag_in_function,
    detect_slag_in_source,
    detect_slag_in_project,
    grade_improvement_estimate,
    _classify_slag_type,
)
from assay.models import Category, ClassifiedLine, FunctionAnalysis, SlagItem


class TestDetectSlagInFunction:
    def test_todo_comment_detected(self):
        lines = [
            ClassifiedLine(1, "# TODO: fix", Category.SLAG),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=1, lines=lines,
        )
        items = detect_slag_in_function(func)
        assert len(items) >= 1
        assert items[0].slag_type == "todo_comment"

    def test_commented_code_detected(self):
        lines = [
            ClassifiedLine(1, "# def old():", Category.SLAG),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=1, lines=lines,
        )
        items = detect_slag_in_function(func)
        assert any(item.slag_type == "commented_out" for item in items)

    def test_no_slag(self):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
            ClassifiedLine(2, "return x", Category.BUSINESS),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=2, lines=lines,
        )
        items = detect_slag_in_function(func)
        assert len(items) == 0

    def test_debug_log_slag(self):
        lines = [
            ClassifiedLine(1, "logger.debug('trace')", Category.SLAG),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=1, lines=lines,
        )
        items = detect_slag_in_function(func)
        assert any(item.slag_type == "debug_log" for item in items)


class TestDetectSlagInSource:
    def test_slag_file(self, slag_file):
        report = detect_slag_in_source(slag_file)
        assert report.total_lines >= 1

    def test_business_file_minimal_slag(self, business_file):
        report = detect_slag_in_source(business_file)
        # Business file should have very little or no slag
        assert report.total_lines <= 2  # might have some unknown comments

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        report = detect_slag_in_source(f)
        assert report.total_lines == 0


class TestDetectSlagInProject:
    def test_project_slag(self, fixtures_dir):
        report = detect_slag_in_project(fixtures_dir)
        assert report.total_lines >= 1

    def test_project_files_affected(self, fixtures_dir):
        report = detect_slag_in_project(fixtures_dir)
        assert report.files_affected >= 1


class TestClassifySlagType:
    def test_todo(self):
        assert _classify_slag_type("# TODO: fix") == "todo_comment"

    def test_fixme(self):
        assert _classify_slag_type("# FIXME: broken") == "todo_comment"

    def test_hack(self):
        assert _classify_slag_type("# HACK: bypass") == "todo_comment"

    def test_commented_def(self):
        assert _classify_slag_type("# def old():") == "commented_out"

    def test_debug_log(self):
        assert _classify_slag_type("logger.debug('x')") == "debug_log"

    def test_other_slag(self):
        assert _classify_slag_type("something") == "other_slag"


class TestGradeImprovementEstimate:
    def test_no_slag(self):
        result = grade_improvement_estimate(50.0, 100, 0)
        assert result == 50.0

    def test_with_slag(self):
        # 50% grade, 100 lines total, 10 slag lines
        # current business = 50 lines, new total = 90, new grade = 50/90*100
        result = grade_improvement_estimate(50.0, 100, 10)
        assert result > 50.0

    def test_zero_lines(self):
        result = grade_improvement_estimate(0.0, 0, 0)
        assert result == 0.0

    def test_all_slag(self):
        # All slag removed
        result = grade_improvement_estimate(10.0, 10, 9)
        # business = 1 line, new total = 1
        assert result == 100.0
