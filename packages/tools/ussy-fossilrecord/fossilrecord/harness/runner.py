"""Harness runner: orchestrates plugin execution across the corpus."""
from __future__ import annotations

import concurrent.futures
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fossilrecord.corpus.loader import CorpusLoader, EsolangProgram, StressCategory
from fossilrecord.harness.plugins import (
    PluginBase,
    PluginResult,
    PluginStatus,
    ParserPlugin,
    LinterPlugin,
    FormatterPlugin,
    AIPlugin,
)


@dataclass
class TestResult:
    """Aggregated result for a single program across all plugins."""
    program: EsolangProgram
    plugin_results: list[PluginResult] = field(default_factory=list)

    def success_rate(self) -> float:
        """Fraction of plugins that succeeded."""
        if not self.plugin_results:
            return 0.0
        successes = sum(1 for r in self.plugin_results if r.is_success)
        return successes / len(self.plugin_results)

    def crash_count(self) -> int:
        return sum(1 for r in self.plugin_results if r.status == PluginStatus.CRASH)

    def timeout_count(self) -> int:
        return sum(1 for r in self.plugin_results if r.status == PluginStatus.TIMEOUT)

    def avg_time(self) -> float:
        if not self.plugin_results:
            return 0.0
        return sum(r.time_seconds for r in self.plugin_results) / len(self.plugin_results)

    def peak_memory_kb(self) -> float:
        if not self.plugin_results:
            return 0.0
        return max(r.memory_peak_kb for r in self.plugin_results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_name": self.program.name,
            "language": self.program.language,
            "success_rate": self.success_rate(),
            "crash_count": self.crash_count(),
            "timeout_count": self.timeout_count(),
            "avg_time_seconds": self.avg_time(),
            "peak_memory_kb": self.peak_memory_kb(),
            "plugin_results": [r.to_dict() for r in self.plugin_results],
        }


@dataclass
class TestSuiteResult:
    """Aggregated result for the entire test suite."""
    results: list[TestResult] = field(default_factory=list)
    total_time_seconds: float = 0.0

    def parse_rate(self) -> float:
        """Fraction of programs where the parser plugin succeeded."""
        return self._rate_for_plugin("parser")

    def linter_rate(self) -> float:
        return self._rate_for_plugin("linter")

    def formatter_rate(self) -> float:
        return self._rate_for_plugin("formatter")

    def ai_rate(self) -> float:
        return self._rate_for_plugin("ai")

    def crash_resistance(self) -> float:
        """Fraction of all plugin runs that did NOT crash."""
        total = 0
        crashes = 0
        for tr in self.results:
            for pr in tr.plugin_results:
                total += 1
                if pr.status == PluginStatus.CRASH:
                    crashes += 1
        if total == 0:
            return 1.0
        return 1.0 - (crashes / total)

    def analysis_accuracy(self) -> float:
        """How well the tools analyzed the code — combines parse and AI rates."""
        parse_r = self.parse_rate()
        ai_r = self.ai_rate()
        # Weighted: parse is base accuracy, AI adds depth
        return 0.6 * parse_r + 0.4 * ai_r

    def memory_efficiency(self) -> float:
        """Score based on memory usage — lower memory = higher score."""
        if not self.results:
            return 1.0
        all_peaks = [tr.peak_memory_kb() for tr in self.results]
        avg_peak = sum(all_peaks) / len(all_peaks)
        # Heuristic: under 1MB is perfect, over 100MB is terrible
        if avg_peak <= 1024:
            return 1.0
        elif avg_peak >= 102400:
            return 0.0
        else:
            return 1.0 - (avg_peak - 1024) / (102400 - 1024)

    def by_category(self, category: StressCategory) -> TestSuiteResult:
        """Filter results by stress category."""
        filtered = TestSuiteResult(total_time_seconds=self.total_time_seconds)
        for tr in self.results:
            if category in tr.program.categories:
                filtered.results.append(tr)
        return filtered

    def by_language(self, language: str) -> TestSuiteResult:
        """Filter results by language."""
        filtered = TestSuiteResult(total_time_seconds=self.total_time_seconds)
        for tr in self.results:
            if tr.program.language.lower() == language.lower():
                filtered.results.append(tr)
        return filtered

    def _rate_for_plugin(self, plugin_name: str) -> float:
        """Success rate for a specific plugin across all programs."""
        total = 0
        successes = 0
        for tr in self.results:
            for pr in tr.plugin_results:
                if pr.plugin_name == plugin_name:
                    total += 1
                    if pr.is_success:
                        successes += 1
        if total == 0:
            return 0.0
        return successes / total

    def summary(self) -> dict[str, Any]:
        return {
            "total_programs": len(self.results),
            "parse_rate": round(self.parse_rate(), 3),
            "analysis_accuracy": round(self.analysis_accuracy(), 3),
            "crash_resistance": round(self.crash_resistance(), 3),
            "memory_efficiency": round(self.memory_efficiency(), 3),
            "ai_rate": round(self.ai_rate(), 3),
            "total_time_seconds": round(self.total_time_seconds, 3),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: Path | str) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TestSuiteResult:
        results = []
        for r_data in data.get("results", []):
            # Reconstruct EsolangProgram minimally
            prog = EsolangProgram(
                name=r_data.get("program_name", ""),
                language=r_data.get("language", ""),
                source="",
                expected_behavior="",
                categories=[],
                difficulty=1,
            )
            plugin_results = [
                PluginResult.from_dict(pr) for pr in r_data.get("plugin_results", [])
            ]
            results.append(TestResult(program=prog, plugin_results=plugin_results))
        return cls(
            results=results,
            total_time_seconds=data.get("summary", {}).get("total_time_seconds", 0.0),
        )

    @classmethod
    def load(cls, path: Path | str) -> TestSuiteResult:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)


class HarnessRunner:
    """Orchestrates running plugins against the esolang corpus."""

    def __init__(
        self,
        corpus_dir: Path | None = None,
        plugins: list[PluginBase] | None = None,
        max_workers: int = 4,
        timeout: float = 10.0,
    ):
        self.corpus_loader = CorpusLoader(corpus_dir)
        self.plugins: list[PluginBase] = plugins or [
            ParserPlugin(timeout=timeout),
            LinterPlugin(timeout=timeout),
            FormatterPlugin(timeout=timeout),
            AIPlugin(timeout=timeout),
        ]
        self.max_workers = max_workers
        self.timeout = timeout

    def run(
        self,
        programs: list[EsolangProgram] | None = None,
        languages: list[str] | None = None,
        categories: list[StressCategory] | None = None,
        min_difficulty: int = 1,
        max_difficulty: int = 5,
    ) -> TestSuiteResult:
        """Run the test suite.

        Args:
            programs: Optional explicit list of programs. If None, loads from corpus.
            languages: Filter to these languages.
            categories: Filter to these stress categories.
            min_difficulty: Minimum difficulty level.
            max_difficulty: Maximum difficulty level.
        """
        if programs is None:
            programs = self.corpus_loader.programs()

        # Apply filters
        if languages:
            lang_set = {l.lower() for l in languages}
            programs = [p for p in programs if p.language.lower() in lang_set]
        if categories:
            programs = [
                p for p in programs
                if any(c in p.categories for c in categories)
            ]
        programs = [
            p for p in programs
            if min_difficulty <= p.difficulty <= max_difficulty
        ]

        suite_result = TestSuiteResult()
        start_time = time.monotonic()

        # Run each program against each plugin
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for prog in programs:
                for plugin in self.plugins:
                    future = executor.submit(self._run_single, plugin, prog)
                    futures[future] = (prog, plugin)

            # Collect results grouped by program
            program_results: dict[str, TestResult] = {}
            for future in concurrent.futures.as_completed(futures):
                prog, plugin = futures[future]
                try:
                    plugin_result = future.result(timeout=self.timeout + 5)
                except Exception as exc:
                    plugin_result = PluginResult(
                        program_name=prog.name,
                        plugin_name=plugin.name,
                        status=PluginStatus.CRASH,
                        error_message=str(exc),
                    )

                if prog.name not in program_results:
                    program_results[prog.name] = TestResult(program=prog)
                program_results[prog.name].plugin_results.append(plugin_result)

        suite_result.results = list(program_results.values())
        suite_result.total_time_seconds = time.monotonic() - start_time
        return suite_result

    def _run_single(self, plugin: PluginBase, program: EsolangProgram) -> PluginResult:
        """Run a single plugin against a single program."""
        return plugin._safe_run(program)
