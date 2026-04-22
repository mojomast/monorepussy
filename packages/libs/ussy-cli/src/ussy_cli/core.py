"""Core utilities for CLI framework: argparse helpers, tables, progress, colors."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from typing import Any, Callable, Final, Iterable, Sequence

try:
    import rich.console
    import rich.table

    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

try:
    import tqdm

    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False


class ColorFormatter:
    """ANSI color/text formatter with ``--no-color`` support."""

    _COLORS: Final[dict[str, str]] = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
    }

    def __init__(self, no_color: bool = False) -> None:
        """Initialize formatter.

        Args:
            no_color: If ``True``, all color methods return plain text.
        """
        self._no_color = (
            no_color or not sys.stdout.isatty() or os.environ.get("NO_COLOR")
        )

    def _wrap(self, text: str, color: str) -> str:
        if self._no_color:
            return text
        return f"{self._COLORS[color]}{text}{self._COLORS['reset']}"

    def red(self, text: str) -> str:
        return self._wrap(text, "red")

    def green(self, text: str) -> str:
        return self._wrap(text, "green")

    def yellow(self, text: str) -> str:
        return self._wrap(text, "yellow")

    def blue(self, text: str) -> str:
        return self._wrap(text, "blue")

    def magenta(self, text: str) -> str:
        return self._wrap(text, "magenta")

    def cyan(self, text: str) -> str:
        return self._wrap(text, "cyan")

    def bold(self, text: str) -> str:
        return self._wrap(text, "bold")

    def dim(self, text: str) -> str:
        return self._wrap(text, "dim")


class StandardFlags:
    """Mixin/parser helper for standard CLI flags."""

    @staticmethod
    def add_to(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """Add ``--json``, ``--verbose``, ``--quiet``, and ``--no-color`` flags."""
        parser.add_argument(
            "--json", action="store_true", help="Output JSON instead of text"
        )
        parser.add_argument(
            "-v", "--verbose", action="store_true", help="Enable verbose output"
        )
        parser.add_argument(
            "-q", "--quiet", action="store_true", help="Suppress non-error output"
        )
        parser.add_argument(
            "--no-color", action="store_true", help="Disable colored output"
        )
        return parser

    @staticmethod
    def configure_logging(args: argparse.Namespace) -> None:
        """Set logging level based on ``--verbose`` / ``--quiet``."""
        import logging

        if args.quiet:
            logging.basicConfig(level=logging.ERROR)
        elif args.verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)


class SubcommandDispatcher:
    """Lightweight argparse subcommand dispatch helper."""

    def __init__(self, prog: str, description: str = "") -> None:
        self.parser = argparse.ArgumentParser(prog=prog, description=description)
        self.subparsers = self.parser.add_subparsers(dest="command")
        self._handlers: dict[str, Callable[[argparse.Namespace], int]] = {}

    def add_command(
        self,
        name: str,
        handler: Callable[[argparse.Namespace], int],
        help_text: str = "",
    ) -> argparse.ArgumentParser:
        """Register a subcommand and return its argument parser."""
        sub = self.subparsers.add_parser(name, help=help_text)
        self._handlers[name] = handler
        return sub

    def run(self, argv: Sequence[str] | None = None) -> int:
        """Parse arguments and dispatch to the registered handler."""
        args = self.parser.parse_args(argv)
        if args.command is None:
            self.parser.print_help()
            return 2
        handler = self._handlers[args.command]
        return handler(args)


class SimpleProgress:
    """Progress bar with tqdm fallback to a simple counter."""

    def __init__(
        self,
        iterable: Iterable[Any] | None = None,
        total: int | None = None,
        desc: str = "",
    ) -> None:
        self._iterable = iterable
        self._total = total
        self._desc = desc
        self._count = 0
        self._tqdm_obj: Any = None

    def __enter__(self) -> SimpleProgress:
        if _HAS_TQDM:
            self._tqdm_obj = tqdm.tqdm(
                iterable=self._iterable,
                total=self._total,
                desc=self._desc,
                disable=os.environ.get("CI") == "true",
            )
        else:
            if self._desc:
                print(f"{self._desc} ...", file=sys.stderr)
        return self

    def __exit__(self, *exc: Any) -> None:
        if self._tqdm_obj is not None:
            self._tqdm_obj.close()
        elif not _HAS_TQDM and self._desc:
            print(f"{self._desc} done ({self._count} items)", file=sys.stderr)

    def __iter__(self) -> Any:
        if self._tqdm_obj is not None:
            yield from self._tqdm_obj
            return
        if self._iterable is None:
            return
        for item in self._iterable:
            self._count += 1
            yield item

    def update(self, n: int = 1) -> None:
        """Manually increment progress by *n* steps."""
        if self._tqdm_obj is not None:
            self._tqdm_obj.update(n)
        else:
            self._count += n


def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    use_rich: bool = True,
    style: str = "simple",
) -> str:
    """Render a table as a string.

    Args:
        headers: Column headers.
        rows: Table rows (each row is a sequence of strings).
        use_rich: Attempt to use ``rich`` if available.
        style: Table style hint (ignored for ASCII fallback).

    Returns:
        Rendered table string.
    """
    if use_rich and _HAS_RICH:
        table = rich.table.Table(*headers, show_header=True, header_style="bold")
        for row in rows:
            table.add_row(*row)
        console = rich.console.Console(force_terminal=True)
        with console.capture() as capture:
            console.print(table)
        return capture.get()

    # ASCII fallback
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))

    def fmt(cells: Sequence[str]) -> str:
        return " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(cells))

    lines = [fmt(headers), "-" * (sum(col_widths) + 3 * (len(headers) - 1))]
    lines.extend(fmt(row) for row in rows)
    return "\n".join(lines)
