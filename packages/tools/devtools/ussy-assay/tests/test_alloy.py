"""Tests for the alloy detection module."""

import pytest

from assay.alloy import detect_alloys, find_pure_functions, _count_interleavings, _generate_suggestions
from assay.models import Category, ClassifiedLine, FunctionAnalysis, AlloyInfo


def _make_func(name: str, categories: list[Category]) -> FunctionAnalysis:
    """Helper to create a FunctionAnalysis with given category sequence."""
    lines = [
        ClassifiedLine(i + 1, f"line {i}", cat)
        for i, cat in enumerate(categories)
    ]
    return FunctionAnalysis(
        name=name, file_path="t.py", start_line=1, end_line=len(lines), lines=lines,
    )


class TestDetectAlloys:
    def test_no_alloy_below_threshold(self):
        """Functions with fewer than 3 concerns are not alloyed."""
        func = _make_func("f", [Category.BUSINESS, Category.BUSINESS, Category.LOGGING])
        results = detect_alloys([func])
        assert len(results) == 0

    def test_alloy_detected_with_interleaving(self):
        """Function with 3+ concerns and interleaving is alloyed."""
        func = _make_func("f", [
            Category.BUSINESS,
            Category.VALIDATION,
            Category.BUSINESS,
            Category.LOGGING,
            Category.BUSINESS,
            Category.VALIDATION,
        ])
        results = detect_alloys([func])
        assert len(results) >= 1

    def test_sequential_concerns_not_interleaved(self):
        """3 concerns but sequential (no interleaving) may not be alloyed."""
        func = _make_func("f", [
            Category.BUSINESS,
            Category.BUSINESS,
            Category.VALIDATION,
            Category.VALIDATION,
            Category.LOGGING,
            Category.LOGGING,
        ])
        # This has only 2 transitions (biz->val, val->log)
        results = detect_alloys([func])
        # Interleaving count is 2, which equals threshold, so it IS alloyed
        # Let's check
        interleaving = _count_interleavings(func)
        assert interleaving == 2

    def test_empty_function(self):
        func = FunctionAnalysis(name="f", file_path="t.py", start_line=1, end_line=1, lines=[])
        results = detect_alloys([func])
        assert len(results) == 0


class TestCountInterleavings:
    def test_no_interleaving(self):
        func = _make_func("f", [Category.BUSINESS, Category.BUSINESS])
        assert _count_interleavings(func) == 0

    def test_one_transition(self):
        func = _make_func("f", [Category.BUSINESS, Category.VALIDATION])
        assert _count_interleavings(func) == 1

    def test_multiple_transitions(self):
        func = _make_func("f", [
            Category.BUSINESS,
            Category.VALIDATION,
            Category.BUSINESS,
            Category.LOGGING,
        ])
        assert _count_interleavings(func) == 3

    def test_slag_ignored(self):
        func = _make_func("f", [
            Category.BUSINESS,
            Category.SLAG,
            Category.BUSINESS,
        ])
        # SLAG is skipped, so no transition
        assert _count_interleavings(func) == 0


class TestFindPureFunctions:
    def test_pure_function_found(self):
        func = _make_func("f", [
            Category.BUSINESS,
            Category.BUSINESS,
            Category.BUSINESS,
        ])
        pure = find_pure_functions([func], min_grade=70.0)
        assert len(pure) == 1

    def test_impure_function_excluded(self):
        func = _make_func("f", [
            Category.BUSINESS,
            Category.LOGGING,
            Category.VALIDATION,
            Category.ERROR_HANDLING,
        ])
        pure = find_pure_functions([func], min_grade=70.0)
        assert len(pure) == 0

    def test_high_grade_but_alloyed(self):
        """High grade but many concerns should be excluded."""
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
            ClassifiedLine(2, "y = 2", Category.BUSINESS),
            ClassifiedLine(3, "isinstance(x, int)", Category.VALIDATION),
            ClassifiedLine(4, "logger.info('x')", Category.LOGGING),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=4, lines=lines,
        )
        pure = find_pure_functions([func], min_grade=50.0)
        # concern_count > 2, so excluded
        assert len(pure) == 0


class TestGenerateSuggestions:
    def test_suggestions_generated(self):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
            ClassifiedLine(2, "isinstance(x, int)", Category.VALIDATION),
            ClassifiedLine(3, "logger.info('x')", Category.LOGGING),
            ClassifiedLine(4, "try:", Category.ERROR_HANDLING),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=4, lines=lines,
        )
        suggestions = _generate_suggestions(func)
        assert len(suggestions) >= 1
