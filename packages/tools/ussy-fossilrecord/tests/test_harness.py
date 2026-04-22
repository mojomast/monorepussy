"""Tests for the harness plugins and runner."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from fossilrecord.corpus.loader import EsolangProgram, StressCategory
from fossilrecord.harness.plugins import (
    ParserPlugin,
    LinterPlugin,
    FormatterPlugin,
    AIPlugin,
    PluginResult,
    PluginStatus,
)
from fossilrecord.harness.runner import HarnessRunner, TestResult, TestSuiteResult


def _make_program(**kwargs):
    """Create a test EsolangProgram with sensible defaults."""
    defaults = {
        "name": "Test Program",
        "language": "Brainfuck",
        "source": "+++.",
        "expected_behavior": "Does something",
        "categories": [StressCategory.MINIMALISTIC],
        "difficulty": 1,
    }
    defaults.update(kwargs)
    return EsolangProgram(**defaults)


class TestPluginResult:
    """Tests for PluginResult dataclass."""

    def test_success_check(self):
        result = PluginResult(
            program_name="test",
            plugin_name="parser",
            status=PluginStatus.SUCCESS,
        )
        assert result.is_success

    def test_failure_not_success(self):
        result = PluginResult(
            program_name="test",
            plugin_name="parser",
            status=PluginStatus.FAILURE,
        )
        assert not result.is_success

    def test_crash_not_success(self):
        result = PluginResult(
            program_name="test",
            plugin_name="parser",
            status=PluginStatus.CRASH,
        )
        assert not result.is_success

    def test_timeout_not_success(self):
        result = PluginResult(
            program_name="test",
            plugin_name="parser",
            status=PluginStatus.TIMEOUT,
        )
        assert not result.is_success

    def test_to_dict_round_trip(self):
        result = PluginResult(
            program_name="test",
            plugin_name="linter",
            status=PluginStatus.SUCCESS,
            time_seconds=0.5,
            memory_peak_kb=128.0,
            error_message="",
            details={"warnings": 3},
        )
        d = result.to_dict()
        restored = PluginResult.from_dict(d)
        assert restored.program_name == result.program_name
        assert restored.plugin_name == result.plugin_name
        assert restored.status == result.status
        assert restored.time_seconds == result.time_seconds
        assert restored.memory_peak_kb == result.memory_peak_kb


class TestParserPlugin:
    """Tests for ParserPlugin."""

    def test_simulated_parser_succeeds_on_nonempty_source(self):
        plugin = ParserPlugin()
        prog = _make_program(source="print('hello')")
        result = plugin.run(prog)
        assert result.status == PluginStatus.SUCCESS

    def test_simulated_parser_fails_on_empty_source(self):
        plugin = ParserPlugin()
        prog = _make_program(source="")
        result = plugin.run(prog)
        assert result.status == PluginStatus.ERROR

    def test_simulated_parser_reports_source_length(self):
        plugin = ParserPlugin()
        source = "++++++++[>++++<-]>."
        prog = _make_program(source=source)
        result = plugin.run(prog)
        assert result.details["source_length"] == len(source)

    def test_simulated_parser_reports_line_count(self):
        plugin = ParserPlugin()
        source = "line1\nline2\nline3"
        prog = _make_program(source=source)
        result = plugin.run(prog)
        assert result.details["line_count"] == 3

    def test_simulated_parser_reports_unique_chars(self):
        plugin = ParserPlugin()
        source = "+++-"
        prog = _make_program(source=source)
        result = plugin.run(prog)
        assert result.details["unique_chars"] == 2  # + and -

    def test_missing_command_returns_error(self):
        plugin = ParserPlugin(command=["nonexistent_tool_xyz"])
        prog = _make_program()
        result = plugin.run(prog)
        # Could be ERROR or CRASH depending on how the OS handles it
        assert result.status in (PluginStatus.ERROR, PluginStatus.CRASH)

    def test_safe_run_wraps_with_timing(self):
        plugin = ParserPlugin()
        prog = _make_program(source="test")
        result = plugin._safe_run(prog)
        assert result.time_seconds >= 0

    def test_safe_run_wraps_with_memory(self):
        plugin = ParserPlugin()
        prog = _make_program(source="test")
        result = plugin._safe_run(prog)
        assert result.memory_peak_kb >= 0


class TestLinterPlugin:
    """Tests for LinterPlugin."""

    def test_simulated_linter_succeeds(self):
        plugin = LinterPlugin()
        prog = _make_program(source="print('hi')")
        result = plugin.run(prog)
        assert result.status == PluginStatus.SUCCESS

    def test_simulated_linter_warns_on_long_source(self):
        plugin = LinterPlugin()
        prog = _make_program(source="x" * 15000)
        result = plugin.run(prog)
        assert result.status == PluginStatus.SUCCESS
        assert any("long" in w.lower() for w in result.details.get("warnings", []))

    def test_simulated_linter_warns_on_single_line(self):
        plugin = LinterPlugin()
        prog = _make_program(source="single_line_no_newline")
        result = plugin.run(prog)
        assert result.status == PluginStatus.SUCCESS
        assert any("single" in w.lower() for w in result.details.get("warnings", []))

    def test_simulated_linter_warns_on_non_ascii(self):
        plugin = LinterPlugin()
        prog = _make_program(source="hello 世界")
        result = plugin.run(prog)
        assert result.status == PluginStatus.SUCCESS
        assert any("non-ascii" in w.lower() or "non ascii" in w.lower()
                    for w in result.details.get("warnings", []))


class TestFormatterPlugin:
    """Tests for FormatterPlugin."""

    def test_simulated_formatter_succeeds(self):
        plugin = FormatterPlugin()
        prog = _make_program(source="x = 1\n")
        result = plugin.run(prog)
        assert result.status == PluginStatus.SUCCESS

    def test_simulated_formatter_reports_trailing_newline(self):
        plugin = FormatterPlugin()
        prog = _make_program(source="x = 1\n")
        result = plugin.run(prog)
        assert result.details["has_trailing_newline"] is True

    def test_simulated_formatter_no_trailing_newline(self):
        plugin = FormatterPlugin()
        prog = _make_program(source="x = 1")
        result = plugin.run(prog)
        assert result.details["has_trailing_newline"] is False

    def test_simulated_formatter_indent_type(self):
        plugin = FormatterPlugin()
        prog = _make_program(source="\tindented")
        result = plugin.run(prog)
        assert result.details["indent_type"] == "tabs"


class TestAIPlugin:
    """Tests for AIPlugin."""

    def test_simulated_ai_succeeds(self):
        plugin = AIPlugin()
        prog = _make_program()
        result = plugin.run(prog)
        assert result.status == PluginStatus.SUCCESS

    def test_simulated_ai_comprehension_score_range(self):
        plugin = AIPlugin()
        for diff in range(1, 6):
            prog = _make_program(difficulty=diff)
            result = plugin.run(prog)
            score = result.details["comprehension_score"]
            assert 0.0 <= score <= 1.0

    def test_simulated_ai_hello_world_bonus(self):
        plugin = AIPlugin()
        prog = _make_program(
            expected_behavior="Prints Hello World",
            difficulty=1,
        )
        result = plugin.run(prog)
        score = result.details["comprehension_score"]
        # Hello World should get a bonus
        assert score >= 0.5

    def test_simulated_ai_high_difficulty_penalty(self):
        plugin = AIPlugin()
        easy = _make_program(difficulty=1, expected_behavior="Prints Hello World")
        hard = _make_program(difficulty=5, expected_behavior="Complex quine")
        easy_result = plugin.run(easy)
        hard_result = plugin.run(hard)
        assert easy_result.details["comprehension_score"] >= hard_result.details["comprehension_score"]

    def test_prompt_template(self):
        plugin = AIPlugin(prompt_template="Explain:\n{source}")
        assert "Explain:" in plugin.prompt_template


class TestTestResult:
    """Tests for TestResult aggregation."""

    def test_success_rate_all_success(self):
        prog = _make_program()
        results = [
            PluginResult("test", "parser", PluginStatus.SUCCESS),
            PluginResult("test", "linter", PluginStatus.SUCCESS),
        ]
        tr = TestResult(program=prog, plugin_results=results)
        assert tr.success_rate() == 1.0

    def test_success_rate_half(self):
        prog = _make_program()
        results = [
            PluginResult("test", "parser", PluginStatus.SUCCESS),
            PluginResult("test", "linter", PluginStatus.FAILURE),
        ]
        tr = TestResult(program=prog, plugin_results=results)
        assert tr.success_rate() == 0.5

    def test_success_rate_empty(self):
        prog = _make_program()
        tr = TestResult(program=prog)
        assert tr.success_rate() == 0.0

    def test_crash_count(self):
        prog = _make_program()
        results = [
            PluginResult("test", "parser", PluginStatus.SUCCESS),
            PluginResult("test", "linter", PluginStatus.CRASH),
            PluginResult("test", "ai", PluginStatus.CRASH),
        ]
        tr = TestResult(program=prog, plugin_results=results)
        assert tr.crash_count() == 2

    def test_timeout_count(self):
        prog = _make_program()
        results = [
            PluginResult("test", "parser", PluginStatus.TIMEOUT),
            PluginResult("test", "linter", PluginStatus.SUCCESS),
        ]
        tr = TestResult(program=prog, plugin_results=results)
        assert tr.timeout_count() == 1


class TestTestSuiteResult:
    """Tests for TestSuiteResult."""

    def _make_suite(self, n_programs=3, statuses=None):
        """Create a test suite with sample results."""
        if statuses is None:
            statuses = [PluginStatus.SUCCESS] * 4  # 4 plugins per program

        results = []
        for i in range(n_programs):
            prog = _make_program(name=f"Program {i}")
            plugin_results = []
            plugin_names = ["parser", "linter", "formatter", "ai"]
            for j, (pname, status) in enumerate(zip(plugin_names, statuses)):
                plugin_results.append(
                    PluginResult(prog.name, pname, status)
                )
            results.append(TestResult(program=prog, plugin_results=plugin_results))
        return TestSuiteResult(results=results, total_time_seconds=1.0)

    def test_parse_rate(self):
        suite = self._make_suite()
        assert suite.parse_rate() == 1.0

    def test_parse_rate_with_failures(self):
        # Create 2 programs, one with parser success, one with parser failure
        prog1 = _make_program(name="Prog 0")
        prog2 = _make_program(name="Prog 1")
        r1 = TestResult(program=prog1, plugin_results=[
            PluginResult("Prog 0", "parser", PluginStatus.SUCCESS),
            PluginResult("Prog 0", "linter", PluginStatus.SUCCESS),
            PluginResult("Prog 0", "formatter", PluginStatus.SUCCESS),
            PluginResult("Prog 0", "ai", PluginStatus.SUCCESS),
        ])
        r2 = TestResult(program=prog2, plugin_results=[
            PluginResult("Prog 1", "parser", PluginStatus.FAILURE),
            PluginResult("Prog 1", "linter", PluginStatus.SUCCESS),
            PluginResult("Prog 1", "formatter", PluginStatus.SUCCESS),
            PluginResult("Prog 1", "ai", PluginStatus.SUCCESS),
        ])
        suite = TestSuiteResult(results=[r1, r2], total_time_seconds=1.0)
        # 1 success out of 2 parser runs
        assert suite.parse_rate() == 0.5

    def test_crash_resistance(self):
        suite = self._make_suite()
        assert suite.crash_resistance() == 1.0

    def test_crash_resistance_with_crashes(self):
        suite = self._make_suite(n_programs=1, statuses=[
            PluginStatus.SUCCESS, PluginStatus.CRASH,
            PluginStatus.SUCCESS, PluginStatus.SUCCESS,
        ])
        assert suite.crash_resistance() == 0.75

    def test_analysis_accuracy(self):
        suite = self._make_suite()
        # analysis_accuracy = 0.6 * parse_rate + 0.4 * ai_rate
        expected = 0.6 * 1.0 + 0.4 * 1.0
        assert abs(suite.analysis_accuracy() - expected) < 0.001

    def test_memory_efficiency(self):
        suite = self._make_suite()
        # Simulated plugins use very little memory
        assert suite.memory_efficiency() >= 0.9

    def test_by_language(self):
        suite = self._make_suite()
        filtered = suite.by_language("Brainfuck")
        assert len(filtered.results) == 3

    def test_by_language_no_match(self):
        suite = self._make_suite()
        filtered = suite.by_language("Nonexistent")
        assert len(filtered.results) == 0

    def test_summary(self):
        suite = self._make_suite()
        s = suite.summary()
        assert "total_programs" in s
        assert "parse_rate" in s
        assert "crash_resistance" in s

    def test_to_json_and_back(self):
        suite = self._make_suite()
        json_str = suite.to_json()
        data = json.loads(json_str)
        restored = TestSuiteResult.from_dict(data)
        assert len(restored.results) == len(suite.results)

    def test_save_and_load(self, tmp_path):
        suite = self._make_suite()
        path = tmp_path / "results.json"
        suite.save(path)
        assert path.exists()
        loaded = TestSuiteResult.load(path)
        assert len(loaded.results) == len(suite.results)


class TestHarnessRunner:
    """Tests for HarnessRunner."""

    def test_run_default_corpus(self):
        runner = HarnessRunner(timeout=5.0)
        result = runner.run()
        assert len(result.results) >= 10
        assert result.total_time_seconds > 0

    def test_run_with_language_filter(self):
        runner = HarnessRunner(timeout=5.0)
        result = runner.run(languages=["Brainfuck"])
        for tr in result.results:
            assert tr.program.language == "Brainfuck"

    def test_run_with_difficulty_filter(self):
        runner = HarnessRunner(timeout=5.0)
        result = runner.run(min_difficulty=4, max_difficulty=5)
        for tr in result.results:
            assert 4 <= tr.program.difficulty <= 5

    def test_run_with_category_filter(self):
        runner = HarnessRunner(timeout=5.0)
        result = runner.run(categories=[StressCategory.WHITESPACE])
        for tr in result.results:
            assert StressCategory.WHITESPACE in tr.program.categories

    def test_run_with_custom_plugins(self):
        plugin = ParserPlugin()
        runner = HarnessRunner(plugins=[plugin], timeout=5.0)
        result = runner.run(languages=["Brainfuck"])
        # Only parser results
        for tr in result.results:
            assert len(tr.plugin_results) == 1
            assert tr.plugin_results[0].plugin_name == "parser"

    def test_run_empty_results(self):
        runner = HarnessRunner(timeout=5.0)
        result = runner.run(languages=["NonexistentLang"])
        assert len(result.results) == 0
