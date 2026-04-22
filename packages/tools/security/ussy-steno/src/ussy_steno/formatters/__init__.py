"""Formatter subpackage — SARIF, JSON, and Table output formatters."""

from ussy_steno.formatters.json_fmt import JsonFormatter
from ussy_steno.formatters.sarif import SarifFormatter
from ussy_steno.formatters.table import TableFormatter

__all__ = ["JsonFormatter", "SarifFormatter", "TableFormatter"]


def get_formatter(fmt: str):
    """Get a formatter instance by name."""
    formatters = {
        "json": JsonFormatter,
        "sarif": SarifFormatter,
        "table": TableFormatter,
    }
    cls = formatters.get(fmt)
    if cls is None:
        raise ValueError(f"Unknown format: {fmt}. Choose from: {', '.join(formatters.keys())}")
    return cls()
