"""Tests for the SQLite storage module."""

import json
from pathlib import Path

import pytest

from ussy_assay.models import (
    Category,
    ClassifiedLine,
    FunctionAnalysis,
    ModuleAnalysis,
    ProjectAnalysis,
)
from ussy_assay.storage import save_analysis, load_latest_run, list_runs


class TestSaveAndLoad:
    def test_save_and_load(self, tmp_path):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
            ClassifiedLine(2, "logger.info('x')", Category.LOGGING),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=2, lines=lines,
        )
        mod = ModuleAnalysis(file_path="t.py", functions=[func])
        project = ProjectAnalysis(modules=[mod])

        run_id = save_analysis(project, str(tmp_path))
        assert run_id >= 1

        loaded = load_latest_run(str(tmp_path))
        assert loaded is not None
        assert len(loaded.modules) == 1
        assert loaded.modules[0].functions[0].name == "f"

    def test_load_nonexistent(self, tmp_path):
        result = load_latest_run(str(tmp_path))
        assert result is None

    def test_multiple_runs(self, tmp_path):
        lines = [ClassifiedLine(1, "x = 1", Category.BUSINESS)]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=1, lines=lines,
        )
        mod = ModuleAnalysis(file_path="t.py", functions=[func])
        project = ProjectAnalysis(modules=[mod])

        save_analysis(project, str(tmp_path))
        save_analysis(project, str(tmp_path))

        loaded = load_latest_run(str(tmp_path))
        assert loaded is not None

    def test_list_runs(self, tmp_path):
        lines = [ClassifiedLine(1, "x = 1", Category.BUSINESS)]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=1, lines=lines,
        )
        mod = ModuleAnalysis(file_path="t.py", functions=[func])
        project = ProjectAnalysis(modules=[mod])

        save_analysis(project, str(tmp_path))
        runs = list_runs(str(tmp_path))
        assert len(runs) >= 1
        assert "timestamp" in runs[0]

    def test_list_runs_empty(self, tmp_path):
        runs = list_runs(str(tmp_path))
        assert runs == []

    def test_category_counts_preserved(self, tmp_path):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
            ClassifiedLine(2, "logger.info('x')", Category.LOGGING),
            ClassifiedLine(3, "# TODO", Category.SLAG),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=3, lines=lines,
        )
        mod = ModuleAnalysis(file_path="t.py", functions=[func])
        project = ProjectAnalysis(modules=[mod])

        save_analysis(project, str(tmp_path))
        loaded = load_latest_run(str(tmp_path))
        func_loaded = loaded.modules[0].functions[0]
        # category_counts are loaded from JSON, not recomputed from empty lines
        assert func_loaded.category_counts.get("business") == 1
        assert func_loaded.category_counts.get("logging") == 1
        assert func_loaded.category_counts.get("slag") == 1
