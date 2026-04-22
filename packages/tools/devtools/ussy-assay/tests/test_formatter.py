"""Tests for the formatter module."""

import pytest

from ussy_assay.formatter import (
    format_grade_report,
    format_compose_report,
    format_alloy_report,
    format_crucible_report,
    format_slag_report,
    _grade_bar,
    _compose_bar,
)
from ussy_assay.models import (
    Category,
    ClassifiedLine,
    CrucibleEntry,
    FunctionAnalysis,
    ModuleAnalysis,
    ProjectAnalysis,
    SlagItem,
    SlagReport,
    AlloyInfo,
)


class TestFormatGradeReport:
    def test_basic_report(self):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
            ClassifiedLine(2, "logger.info('x')", Category.LOGGING),
        ]
        func = FunctionAnalysis(
            name="compute", file_path="test.py", start_line=1, end_line=2, lines=lines,
        )
        mod = ModuleAnalysis(file_path="test.py", functions=[func])
        project = ProjectAnalysis(modules=[mod])

        report = format_grade_report(project)
        assert "ASSAY REPORT" in report
        assert "compute" in report
        assert "50%" in report

    def test_empty_project(self):
        project = ProjectAnalysis()
        report = format_grade_report(project)
        assert "ASSAY REPORT" in report


class TestFormatComposeReport:
    def test_compose_report(self):
        composition = {
            "business": {"lines": 3, "percentage": 60.0, "icon": "\U0001f48e", "display_name": "Business"},
            "logging": {"lines": 2, "percentage": 40.0, "icon": "\U0001f4dd", "display_name": "Logging"},
        }
        report = format_compose_report("my_func", composition)
        assert "my_func" in report
        assert "Elemental Composition" in report
        assert "Business" in report
        assert "Logging" in report


class TestFormatAlloyReport:
    def test_alloyed_functions(self):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
            ClassifiedLine(2, "isinstance(x, int)", Category.VALIDATION),
            ClassifiedLine(3, "logger.info('x')", Category.LOGGING),
            ClassifiedLine(4, "raise Error", Category.ERROR_HANDLING),
        ]
        func = FunctionAnalysis(
            name="mixed", file_path="t.py", start_line=1, end_line=4, lines=lines,
        )
        alloy = AlloyInfo(function=func)

        report = format_alloy_report([alloy], [])
        assert "MIXED CONCERNS" in report
        assert "mixed" in report

    def test_pure_functions(self):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
            ClassifiedLine(2, "return x", Category.BUSINESS),
        ]
        func = FunctionAnalysis(
            name="pure", file_path="t.py", start_line=1, end_line=2, lines=lines,
        )

        report = format_alloy_report([], [func])
        assert "PURE FUNCTIONS" in report
        assert "pure" in report


class TestFormatCrucibleReport:
    def test_crucible_report(self):
        lines = [ClassifiedLine(1, "x = 1", Category.BUSINESS)]
        func = FunctionAnalysis(
            name="valuable", file_path="t.py", start_line=1, end_line=1, lines=lines,
        )
        entry = CrucibleEntry(function=func, caller_count=5)

        report = format_crucible_report({"top": [entry], "bottom": [entry]})
        assert "MOST VALUABLE" in report
        assert "valuable" in report


class TestFormatSlagReport:
    def test_slag_report(self):
        items = [
            SlagItem("a.py", 10, "# TODO: fix", "todo_comment"),
            SlagItem("b.py", 5, "logger.debug('x')", "debug_log"),
        ]
        report_obj = SlagReport(items=items)

        report = format_slag_report(report_obj)
        assert "SLAG INVENTORY" in report
        assert "TODO" in report
        assert "debug" in report.lower()


class TestGradeBar:
    def test_full_grade(self):
        bar = _grade_bar(100)
        assert "\u25a0" in bar

    def test_zero_grade(self):
        bar = _grade_bar(0)
        assert "\u2591" in bar


class TestComposeBar:
    def test_bar_characters(self):
        bar = _compose_bar(50, width=10)
        assert len(bar) == 10
        assert "\u25a0" in bar
        assert "\u2591" in bar
