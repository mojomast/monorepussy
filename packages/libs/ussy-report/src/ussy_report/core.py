"""Core utilities for report formatting (JSON, SARIF, tables, HTML, Markdown)."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from typing import Any, Sequence


def terminal_width(default: int = 80) -> int:
    """Return the terminal width, falling back to *default*.

    Args:
        default: Fallback width when terminal size cannot be determined.
    """
    size = shutil.get_terminal_size()
    return size.columns or default


def render_ascii_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    max_width: int | None = None,
) -> str:
    """Render an ASCII table with optional width truncation.

    Args:
        headers: Column headers.
        rows: Table rows.
        max_width: Maximum total width (defaults to terminal width).

    Returns:
        Rendered ASCII table string.
    """
    if max_width is None:
        max_width = terminal_width()

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))

    # Truncate columns proportionally if too wide
    total = sum(col_widths) + 3 * (len(headers) - 1)
    if total > max_width and len(col_widths) > 0:
        excess = total - max_width
        per_col = excess // len(col_widths)
        col_widths = [max(3, w - per_col) for w in col_widths]

    def fmt(cells: Sequence[str]) -> str:
        return " | ".join(
            str(cell)[: col_widths[i]].ljust(col_widths[i])
            for i, cell in enumerate(cells)
        )

    sep = "-" * (sum(col_widths) + 3 * (len(headers) - 1))
    lines = [fmt(headers), sep]
    lines.extend(fmt(row) for row in rows)
    return "\n".join(lines)


def render_unicode_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    max_width: int | None = None,
) -> str:
    """Render a Unicode box-drawing table.

    Args:
        headers: Column headers.
        rows: Table rows.
        max_width: Maximum total width (defaults to terminal width).

    Returns:
        Rendered Unicode table string.
    """
    if max_width is None:
        max_width = terminal_width()

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))

    total = sum(col_widths) + 3 * (len(headers) - 1)
    if total > max_width and len(col_widths) > 0:
        excess = total - max_width
        per_col = excess // len(col_widths)
        col_widths = [max(3, w - per_col) for w in col_widths]

    def hline(left: str, mid: str, right: str, fill: str) -> str:
        parts = [fill * (w + 2) for w in col_widths]
        return left + mid.join(parts) + right

    def rowline(cells: Sequence[str]) -> str:
        return (
            "│ "
            + " │ ".join(
                str(cell)[: col_widths[i]].ljust(col_widths[i])
                for i, cell in enumerate(cells)
            )
            + " │"
        )

    top = hline("┌", "┬", "┐", "─")
    header = rowline(headers)
    mid = hline("├", "┼", "┤", "─")
    body = "\n".join(rowline(row) for row in rows)
    bottom = hline("└", "┴", "┘", "─")
    return "\n".join([top, header, mid, body, bottom])


class JsonOutput:
    """Standardized JSON output builder."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = data or {}

    def set(self, key: str, value: Any) -> JsonOutput:
        """Set a top-level key."""
        self._data[key] = value
        return self

    def add_result(self, result: dict[str, Any]) -> JsonOutput:
        """Append a result to the ``results`` list."""
        self._data.setdefault("results", []).append(result)
        return self

    def to_json(self, indent: int | None = 2) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self._data, indent=indent, ensure_ascii=False, default=str)

    def to_dict(self) -> dict[str, Any]:
        """Return the underlying dictionary."""
        return self._data.copy()


class SarifBuilder:
    """Build SARIF 2.1.0 output as a dictionary (no external JSON schema deps)."""

    def __init__(self, tool_name: str, tool_version: str = "0.1.0") -> None:
        self._tool = {"driver": {"name": tool_name, "version": tool_version}}
        self._runs: list[dict[str, Any]] = []
        self._results: list[dict[str, Any]] = []
        self._rules: list[dict[str, Any]] = []

    def add_rule(
        self, rule_id: str, name: str, short_desc: str, full_desc: str = ""
    ) -> SarifBuilder:
        """Register a rule definition."""
        self._rules.append(
            {
                "id": rule_id,
                "name": name,
                "shortDescription": {"text": short_desc},
                "fullDescription": {"text": full_desc or short_desc},
            }
        )
        return self

    def add_result(
        self,
        rule_id: str,
        message: str,
        level: str = "warning",
        uri: str = "",
        start_line: int = 1,
        start_col: int = 1,
    ) -> SarifBuilder:
        """Append a SARIF result."""
        location: dict[str, Any] = {
            "physicalLocation": {
                "artifactLocation": {"uri": uri},
                "region": {
                    "startLine": start_line,
                    "startColumn": start_col,
                },
            }
        }
        self._results.append(
            {
                "ruleId": rule_id,
                "level": level,
                "message": {"text": message},
                "locations": [location],
            }
        )
        return self

    def build(self) -> dict[str, Any]:
        """Return the complete SARIF log dictionary."""
        run: dict[str, Any] = {
            "tool": self._tool,
            "results": self._results,
        }
        if self._rules:
            run["tool"]["driver"]["rules"] = self._rules
        return {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [run],
        }

    def to_json(self, indent: int | None = 2) -> str:
        """Serialize SARIF log to JSON."""
        return json.dumps(self.build(), indent=indent, ensure_ascii=False)


class MarkdownReport:
    """Basic Markdown report generator."""

    def __init__(self, title: str = "Report") -> None:
        self._lines: list[str] = [f"# {title}", ""]

    def heading(self, text: str, level: int = 2) -> MarkdownReport:
        self._lines.append(f"{'#' * level} {text}")
        self._lines.append("")
        return self

    def paragraph(self, text: str) -> MarkdownReport:
        self._lines.append(text)
        self._lines.append("")
        return self

    def table(
        self, headers: Sequence[str], rows: Sequence[Sequence[str]]
    ) -> MarkdownReport:
        self._lines.append("| " + " | ".join(headers) + " |")
        self._lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in rows:
            self._lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
        self._lines.append("")
        return self

    def code_block(self, code: str, language: str = "") -> MarkdownReport:
        self._lines.append(f"```{language}")
        self._lines.append(code)
        self._lines.append("```")
        self._lines.append("")
        return self

    def to_markdown(self) -> str:
        return "\n".join(self._lines)
