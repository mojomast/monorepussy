"""Tests for data models."""

import pytest

from ussy_assay.models import (
    Category,
    ClassifiedLine,
    FunctionAnalysis,
    ModuleAnalysis,
    ProjectAnalysis,
    AlloyInfo,
    SlagItem,
    SlagReport,
    CrucibleEntry,
    GradeTrend,
)


class TestCategory:
    def test_category_values(self):
        assert Category.BUSINESS.value == "business"
        assert Category.VALIDATION.value == "validation"
        assert Category.ERROR_HANDLING.value == "error_handling"
        assert Category.LOGGING.value == "logging"
        assert Category.FRAMEWORK.value == "framework"
        assert Category.SLAG.value == "slag"
        assert Category.UNKNOWN.value == "unknown"

    def test_category_icon(self):
        assert Category.BUSINESS.icon == "\U0001f48e"
        assert Category.SLAG.icon == "\U0001f5d1\ufe0f"

    def test_category_display_name(self):
        assert Category.BUSINESS.display_name == "Business"
        assert Category.ERROR_HANDLING.display_name == "Error Handling"

    def test_category_is_str(self):
        assert isinstance(Category.BUSINESS, str)
        assert Category.BUSINESS == "business"


class TestClassifiedLine:
    def test_creation(self):
        line = ClassifiedLine(
            line_number=1,
            content="x = 1",
            category=Category.BUSINESS,
        )
        assert line.line_number == 1
        assert line.category == Category.BUSINESS
        assert line.is_comment is False

    def test_comment_line(self):
        line = ClassifiedLine(
            line_number=5,
            content="# note",
            category=Category.UNKNOWN,
            is_comment=True,
        )
        assert line.is_comment is True


class TestFunctionAnalysis:
    def test_basic_analysis(self):
        lines = [
            ClassifiedLine(1, "def f():", Category.BUSINESS),
            ClassifiedLine(2, "    x = 1", Category.BUSINESS),
            ClassifiedLine(3, "    logger.info('x')", Category.LOGGING),
            ClassifiedLine(4, "    return x", Category.BUSINESS),
        ]
        func = FunctionAnalysis(
            name="f",
            file_path="test.py",
            start_line=1,
            end_line=4,
            lines=lines,
        )
        assert func.total_lines == 4
        assert func.business_lines == 3
        assert func.grade == 75.0
        assert func.concern_count == 2  # business + logging

    def test_empty_function(self):
        func = FunctionAnalysis(
            name="empty",
            file_path="test.py",
            start_line=1,
            end_line=1,
            lines=[],
        )
        assert func.total_lines == 1
        assert func.business_lines == 0
        assert func.grade == 0.0

    def test_slag_lines_property(self):
        lines = [
            ClassifiedLine(1, "# TODO", Category.SLAG),
            ClassifiedLine(2, "x = 1", Category.BUSINESS),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=2, lines=lines,
        )
        assert func.slag_lines == 1

    def test_category_counts(self):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
            ClassifiedLine(2, "logger.info('x')", Category.LOGGING),
            ClassifiedLine(3, "# TODO", Category.SLAG),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=3, lines=lines,
        )
        assert func.category_counts["business"] == 1
        assert func.category_counts["logging"] == 1
        assert func.category_counts["slag"] == 1

    def test_default_grade_value(self):
        """Grade should have a default so it's not a required init arg."""
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=1,
        )
        assert func.grade == 0.0


class TestModuleAnalysis:
    def test_module_grade(self):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
            ClassifiedLine(2, "logger.info('x')", Category.LOGGING),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=2, lines=lines,
        )
        mod = ModuleAnalysis(file_path="t.py", functions=[func])
        assert mod.grade == 50.0
        assert mod.total_lines == 2
        assert mod.business_lines == 1


class TestProjectAnalysis:
    def test_project_grade(self):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
        ]
        func = FunctionAnalysis(
            name="f", file_path="a.py", start_line=1, end_line=1, lines=lines,
        )
        mod = ModuleAnalysis(file_path="a.py", functions=[func])
        project = ProjectAnalysis(modules=[mod])
        assert project.grade == 100.0

    def test_all_functions(self):
        func1 = FunctionAnalysis(name="f1", file_path="a.py", start_line=1, end_line=1)
        func2 = FunctionAnalysis(name="f2", file_path="b.py", start_line=1, end_line=1)
        mod1 = ModuleAnalysis(file_path="a.py", functions=[func1])
        mod2 = ModuleAnalysis(file_path="b.py", functions=[func2])
        project = ProjectAnalysis(modules=[mod1, mod2])
        assert len(project.all_functions) == 2


class TestAlloyInfo:
    def test_alloy_default_suggestions(self):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
            ClassifiedLine(2, "isinstance(x, int)", Category.VALIDATION),
            ClassifiedLine(3, "logger.info('x')", Category.LOGGING),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=3, lines=lines,
        )
        alloy = AlloyInfo(function=func)
        assert alloy.concern_count == 3
        assert alloy.projected_grade >= 0


class TestSlagReport:
    def test_empty_report(self):
        report = SlagReport()
        assert report.total_lines == 0
        assert report.files_affected == 0

    def test_report_with_items(self):
        items = [
            SlagItem("a.py", 1, "# TODO", "todo_comment"),
            SlagItem("a.py", 5, "# FIXME", "todo_comment"),
            SlagItem("b.py", 3, "# HACK", "todo_comment"),
        ]
        report = SlagReport(items=items)
        assert report.total_lines == 3
        assert report.files_affected == 2

    def test_by_type(self):
        items = [
            SlagItem("a.py", 1, "# TODO", "todo_comment"),
            SlagItem("a.py", 5, "logger.debug('x')", "debug_log"),
        ]
        report = SlagReport(items=items)
        by_type = report.by_type
        assert "todo_comment" in by_type
        assert "debug_log" in by_type
        assert len(by_type["todo_comment"]) == 1


class TestCrucibleEntry:
    def test_value_score_auto(self):
        lines = [ClassifiedLine(1, "x = 1", Category.BUSINESS)]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=1, lines=lines,
        )
        entry = CrucibleEntry(function=func, caller_count=5)
        assert entry.value_score == 100.0 * 6  # grade 100 * (5+1)

    def test_value_score_no_callers(self):
        lines = [ClassifiedLine(1, "x = 1", Category.BUSINESS)]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=1, lines=lines,
        )
        entry = CrucibleEntry(function=func)
        assert entry.value_score == 100.0 * 1  # grade 100 * (0+1)


class TestGradeTrend:
    def test_positive_trend(self):
        trend = GradeTrend("f", current_grade=80.0, previous_grade=70.0)
        assert trend.delta == 10.0
        assert trend.trend_symbol == "\u25b2"

    def test_negative_trend(self):
        trend = GradeTrend("f", current_grade=50.0, previous_grade=60.0)
        assert trend.delta == -10.0
        assert trend.trend_symbol == "\u25bc"

    def test_no_trend(self):
        trend = GradeTrend("f", current_grade=50.0, previous_grade=50.0)
        assert trend.delta == 0.0
        assert trend.trend_symbol == "\u2500"
