"""Ussyverse report formatting (JSON, SARIF, tables, HTML, Markdown)."""

__version__ = "0.1.0"

from ussy_report.core import (
    JsonOutput,
    MarkdownReport,
    SarifBuilder,
    render_ascii_table,
    render_unicode_table,
    terminal_width,
)

__all__ = [
    "__version__",
    "JsonOutput",
    "MarkdownReport",
    "SarifBuilder",
    "render_ascii_table",
    "render_unicode_table",
    "terminal_width",
]
