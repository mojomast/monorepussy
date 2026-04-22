"""Tests for the compose module."""

from pathlib import Path

import pytest

from ussy_assay.classifier import classify_source
from ussy_assay.compose import compose_function, compose_module, compose_bar
from ussy_assay.models import Category, ClassifiedLine, FunctionAnalysis


class TestComposeFunction:
    def test_composition_keys(self):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
            ClassifiedLine(2, "isinstance(x, int)", Category.VALIDATION),
            ClassifiedLine(3, "logger.info('x')", Category.LOGGING),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=3, lines=lines,
        )
        comp = compose_function(func)
        assert "business" in comp
        assert "validation" in comp
        assert "logging" in comp

    def test_composition_percentages(self):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
            ClassifiedLine(2, "y = 2", Category.BUSINESS),
            ClassifiedLine(3, "logger.info('x')", Category.LOGGING),
            ClassifiedLine(4, "raise Error", Category.ERROR_HANDLING),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=4, lines=lines,
        )
        comp = compose_function(func)
        assert comp["business"]["percentage"] == 50.0
        assert comp["logging"]["percentage"] == 25.0
        assert comp["error_handling"]["percentage"] == 25.0

    def test_composition_has_lines_count(self):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
            ClassifiedLine(2, "y = 2", Category.BUSINESS),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=2, lines=lines,
        )
        comp = compose_function(func)
        assert comp["business"]["lines"] == 2

    def test_composition_has_icons(self):
        lines = [
            ClassifiedLine(1, "x = 1", Category.BUSINESS),
        ]
        func = FunctionAnalysis(
            name="f", file_path="t.py", start_line=1, end_line=1, lines=lines,
        )
        comp = compose_function(func)
        assert comp["business"]["icon"] == Category.BUSINESS.icon


class TestComposeModule:
    def test_module_composition(self, business_file):
        results = compose_module(business_file)
        assert len(results) >= 1
        for r in results:
            assert "name" in r
            assert "composition" in r
            assert "total_lines" in r
            assert "grade" in r

    def test_module_has_functions(self, mixed_file):
        results = compose_module(mixed_file)
        assert any(r["name"] == "process_order" for r in results)


class TestComposeBar:
    def test_full_bar(self):
        bar = compose_bar(100.0, width=10)
        assert bar == "\u25a0" * 10

    def test_empty_bar(self):
        bar = compose_bar(0.0, width=10)
        assert bar == "\u2591" * 10

    def test_half_bar(self):
        bar = compose_bar(50.0, width=10)
        assert "\u25a0" in bar
        assert "\u2591" in bar

    def test_bar_width(self):
        bar = compose_bar(50.0, width=12)
        assert len(bar) == 12
