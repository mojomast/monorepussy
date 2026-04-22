"""Test harness: plugin architecture for running tool stress tests."""
from __future__ import annotations

from fossilrecord.harness.runner import HarnessRunner
from fossilrecord.harness.plugins import (
    PluginBase,
    ParserPlugin,
    LinterPlugin,
    FormatterPlugin,
    AIPlugin,
    PluginResult,
    PluginStatus,
)
from fossilrecord.harness.result import TestResult, TestSuiteResult

__all__ = [
    "HarnessRunner",
    "PluginBase",
    "ParserPlugin",
    "LinterPlugin",
    "FormatterPlugin",
    "AIPlugin",
    "PluginResult",
    "PluginStatus",
    "TestResult",
    "TestSuiteResult",
]
