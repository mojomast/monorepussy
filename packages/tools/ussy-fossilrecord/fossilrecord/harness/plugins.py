"""Plugin base classes and built-in plugin implementations."""
from __future__ import annotations

import enum
import time
import tracemalloc
import subprocess
import signal
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from fossilrecord.corpus.loader import EsolangProgram


class PluginStatus(enum.Enum):
    """Result status for a single plugin test."""
    SUCCESS = "success"
    FAILURE = "failure"
    CRASH = "crash"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class PluginResult:
    """Result from running a single plugin against a single program."""
    program_name: str
    plugin_name: str
    status: PluginStatus
    time_seconds: float = 0.0
    memory_peak_kb: float = 0.0
    error_message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == PluginStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_name": self.program_name,
            "plugin_name": self.plugin_name,
            "status": self.status.value,
            "time_seconds": self.time_seconds,
            "memory_peak_kb": self.memory_peak_kb,
            "error_message": self.error_message,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginResult:
        return cls(
            program_name=data["program_name"],
            plugin_name=data["plugin_name"],
            status=PluginStatus(data["status"]),
            time_seconds=data.get("time_seconds", 0.0),
            memory_peak_kb=data.get("memory_peak_kb", 0.0),
            error_message=data.get("error_message", ""),
            details=data.get("details", {}),
        )


class PluginBase(ABC):
    """Abstract base class for tool stress-test plugins."""

    name: str = "base"

    def __init__(self, timeout: float = 10.0, **kwargs: Any):
        self.timeout = timeout
        self.config = kwargs

    @abstractmethod
    def run(self, program: EsolangProgram) -> PluginResult:
        """Run this plugin against an esolang program. Must be implemented by subclasses."""
        ...

    def _safe_run(self, program: EsolangProgram) -> PluginResult:
        """Run with timeout and memory tracking wrapper."""
        result = PluginResult(
            program_name=program.name,
            plugin_name=self.name,
            status=PluginStatus.ERROR,
        )

        tracemalloc.start()
        start_time = time.monotonic()
        try:
            result = self.run(program)
        except subprocess.TimeoutExpired:
            result.status = PluginStatus.TIMEOUT
            result.error_message = f"Plugin timed out after {self.timeout}s"
        except Exception as exc:
            result.status = PluginStatus.CRASH
            result.error_message = str(exc)
        finally:
            result.time_seconds = time.monotonic() - start_time
            _, peak = tracemalloc.get_traced_memory()
            result.memory_peak_kb = peak / 1024.0
            tracemalloc.stop()

        return result


class ParserPlugin(PluginBase):
    """Test whether a tool can parse esolang source code without crashing.

    By default, this tries to feed the source to a subprocess command
    and checks if it returns successfully.
    """

    name = "parser"

    def __init__(self, command: list[str] | None = None, timeout: float = 10.0, **kwargs: Any):
        super().__init__(timeout=timeout, **kwargs)
        self.command = command or []

    def run(self, program: EsolangProgram) -> PluginResult:
        result = PluginResult(
            program_name=program.name,
            plugin_name=self.name,
            status=PluginStatus.ERROR,
        )

        source = program.source
        if not source:
            result.status = PluginStatus.ERROR
            result.error_message = "Empty source code"
            return result

        if not self.command:
            # Simulated parser: just check if source is non-empty and doesn't crash
            result.status = PluginStatus.SUCCESS
            result.details["source_length"] = len(source)
            result.details["line_count"] = source.count("\n") + 1
            result.details["unique_chars"] = len(set(source))
            return result

        try:
            proc = subprocess.run(
                self.command,
                input=source,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            if proc.returncode == 0:
                result.status = PluginStatus.SUCCESS
            else:
                result.status = PluginStatus.FAILURE
                result.error_message = f"Parser returned {proc.returncode}"
                result.details["stderr"] = proc.stderr[:500] if proc.stderr else ""
        except subprocess.TimeoutExpired:
            result.status = PluginStatus.TIMEOUT
            result.error_message = f"Parser timed out after {self.timeout}s"
        except FileNotFoundError:
            result.status = PluginStatus.ERROR
            result.error_message = f"Command not found: {self.command[0]}"
        except Exception as exc:
            result.status = PluginStatus.CRASH
            result.error_message = str(exc)

        return result


class LinterPlugin(PluginBase):
    """Test whether a linter can process esolang source code without crashing."""

    name = "linter"

    def __init__(self, command: list[str] | None = None, timeout: float = 10.0, **kwargs: Any):
        super().__init__(timeout=timeout, **kwargs)
        self.command = command or []

    def run(self, program: EsolangProgram) -> PluginResult:
        result = PluginResult(
            program_name=program.name,
            plugin_name=self.name,
            status=PluginStatus.ERROR,
        )

        source = program.source
        if not self.command:
            # Simulated linter: check for common issues
            warnings = []
            if len(source) > 10000:
                warnings.append("Very long source code")
            if source.count("\n") == 0:
                warnings.append("Single line source")
            # Check for non-ASCII
            non_ascii = sum(1 for c in source if ord(c) > 127)
            if non_ascii > 0:
                warnings.append(f"Contains {non_ascii} non-ASCII characters")

            result.status = PluginStatus.SUCCESS
            result.details["warnings"] = warnings
            result.details["warning_count"] = len(warnings)
            return result

        try:
            proc = subprocess.run(
                self.command,
                input=source,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            # Linters often return non-zero for warnings — that's OK, we just check no crash
            result.status = PluginStatus.SUCCESS
            result.details["returncode"] = proc.returncode
            result.details["stderr"] = proc.stderr[:500] if proc.stderr else ""
        except subprocess.TimeoutExpired:
            result.status = PluginStatus.TIMEOUT
        except FileNotFoundError:
            result.status = PluginStatus.ERROR
            result.error_message = f"Command not found: {self.command[0]}"
        except Exception as exc:
            result.status = PluginStatus.CRASH
            result.error_message = str(exc)

        return result


class FormatterPlugin(PluginBase):
    """Test whether a formatter can process esolang source code without crashing."""

    name = "formatter"

    def __init__(self, command: list[str] | None = None, timeout: float = 10.0, **kwargs: Any):
        super().__init__(timeout=timeout, **kwargs)
        self.command = command or []

    def run(self, program: EsolangProgram) -> PluginResult:
        result = PluginResult(
            program_name=program.name,
            plugin_name=self.name,
            status=PluginStatus.ERROR,
        )

        source = program.source
        if not self.command:
            # Simulated formatter: check if source has consistent formatting
            result.status = PluginStatus.SUCCESS
            result.details["original_length"] = len(source)
            result.details["has_trailing_newline"] = source.endswith("\n")
            result.details["indent_type"] = "tabs" if "\t" in source else "spaces"
            return result

        try:
            proc = subprocess.run(
                self.command,
                input=source,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            if proc.returncode == 0:
                result.status = PluginStatus.SUCCESS
                result.details["formatted_length"] = len(proc.stdout)
                result.details["changed"] = proc.stdout != source
            else:
                result.status = PluginStatus.FAILURE
                result.error_message = f"Formatter returned {proc.returncode}"
        except subprocess.TimeoutExpired:
            result.status = PluginStatus.TIMEOUT
        except FileNotFoundError:
            result.status = PluginStatus.ERROR
            result.error_message = f"Command not found: {self.command[0]}"
        except Exception as exc:
            result.status = PluginStatus.CRASH
            result.error_message = str(exc)

        return result


class AIPlugin(PluginBase):
    """Test whether an AI tool can correctly explain esolang code.

    For simulated mode, checks if the program's expected_behavior
    can be matched against simple heuristics.
    """

    name = "ai"

    def __init__(
        self,
        command: list[str] | None = None,
        timeout: float = 30.0,
        prompt_template: str = "Explain what this code does:\n{source}",
        **kwargs: Any,
    ):
        super().__init__(timeout=timeout, **kwargs)
        self.command = command or []
        self.prompt_template = prompt_template

    def run(self, program: EsolangProgram) -> PluginResult:
        result = PluginResult(
            program_name=program.name,
            plugin_name=self.name,
            status=PluginStatus.ERROR,
        )

        source = program.source
        if not self.command:
            # Simulated AI comprehension: heuristic check
            # A real AI plugin would send the source to an AI endpoint
            # and compare the response with expected_behavior
            comprehension_score = self._simulate_comprehension(program)
            result.status = PluginStatus.SUCCESS
            result.details["comprehension_score"] = comprehension_score
            result.details["expected_behavior"] = program.expected_behavior
            return result

        prompt = self.prompt_template.format(source=source)
        try:
            proc = subprocess.run(
                self.command,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            if proc.returncode == 0:
                result.status = PluginStatus.SUCCESS
                result.details["response"] = proc.stdout[:1000]
            else:
                result.status = PluginStatus.FAILURE
                result.error_message = f"AI tool returned {proc.returncode}"
        except subprocess.TimeoutExpired:
            result.status = PluginStatus.TIMEOUT
        except FileNotFoundError:
            result.status = PluginStatus.ERROR
            result.error_message = f"Command not found: {self.command[0]}"
        except Exception as exc:
            result.status = PluginStatus.CRASH
            result.error_message = str(exc)

        return result

    def _simulate_comprehension(self, program: EsolangProgram) -> float:
        """Simulate AI comprehension scoring.

        Returns a score between 0.0 and 1.0 based on heuristics:
        - Programs with clear expected behavior descriptions score higher
        - Well-known programs (Hello World) score higher
        - More difficult programs score lower
        """
        score = 1.0

        # Difficulty penalty
        score -= (program.difficulty - 1) * 0.1

        # Well-known patterns
        source_lower = program.source.lower()
        if "hello" in program.expected_behavior.lower():
            score += 0.1  # Hello World is well-known

        # Language familiarity bonus (simpler languages are more "understandable")
        simple_langs = {"Brainfuck", "GolfScript", "APL"}
        if program.language in simple_langs:
            score += 0.05

        # Source complexity penalty
        if len(program.source) > 500:
            score -= 0.1

        return max(0.0, min(1.0, score))
