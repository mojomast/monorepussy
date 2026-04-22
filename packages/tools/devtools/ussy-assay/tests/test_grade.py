"""Tests for the grade module."""

from pathlib import Path

import pytest

from ussy_assay.grade import grade_project, grade_module, grade_label, compute_trends
from ussy_assay.models import ProjectAnalysis, ModuleAnalysis, FunctionAnalysis, GradeTrend


class TestGradeProject:
    def test_grade_business_file(self, business_file):
        project = grade_project(business_file)
        assert len(project.modules) == 1
        assert project.grade > 0

    def test_grade_mixed_file(self, mixed_file, business_file):
        project = grade_project(mixed_file)
        assert len(project.modules) == 1
        # Mixed file should have lower grade than business file
        biz_project = grade_project(business_file)
        assert project.grade < biz_project.grade

    def test_grade_directory(self, fixtures_dir):
        project = grade_project(fixtures_dir)
        assert len(project.modules) >= 4
        assert project.total_lines > 0

    def test_grade_empty_dir(self, tmp_path):
        project = grade_project(tmp_path)
        assert len(project.modules) == 0
        assert project.grade == 0.0


class TestGradeModule:
    def test_single_module(self, business_file):
        mod = grade_module(business_file)
        assert mod.file_path == str(business_file)
        assert len(mod.functions) >= 1

    def test_module_has_grade(self, mixed_file):
        mod = grade_module(mixed_file)
        assert 0 <= mod.grade <= 100


class TestGradeLabel:
    def test_high_grade(self):
        assert grade_label(80) == "High-grade ore"

    def test_medium_grade(self):
        assert grade_label(55) == "Medium-grade ore"

    def test_low_grade(self):
        assert grade_label(30) == "Low-grade ore"

    def test_tailings(self):
        assert grade_label(10) == "Tailings"

    def test_boundary_high(self):
        assert grade_label(75) == "High-grade ore"

    def test_boundary_medium(self):
        assert grade_label(50) == "Medium-grade ore"

    def test_boundary_low(self):
        assert grade_label(25) == "Low-grade ore"


class TestComputeTrends:
    def test_no_previous(self):
        lines = []
        func = FunctionAnalysis(name="f", file_path="t.py", start_line=1, end_line=1, lines=lines)
        mod = ModuleAnalysis(file_path="t.py", functions=[func])
        current = ProjectAnalysis(modules=[mod])

        trends = compute_trends(current)
        assert len(trends) == 1
        assert trends[0].current_grade == 0.0

    def test_with_previous(self):
        func1 = FunctionAnalysis(name="f", file_path="a.py", start_line=1, end_line=1, grade=50.0)
        mod1 = ModuleAnalysis(file_path="a.py", functions=[func1])
        current = ProjectAnalysis(modules=[mod1])

        func2 = FunctionAnalysis(name="f", file_path="a.py", start_line=1, end_line=1, grade=40.0)
        mod2 = ModuleAnalysis(file_path="a.py", functions=[func2])
        previous = ProjectAnalysis(modules=[mod2])

        trends = compute_trends(current, previous)
        assert len(trends) == 1
        assert trends[0].delta == 10.0
