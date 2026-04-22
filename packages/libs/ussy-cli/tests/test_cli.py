"""Tests for ussy_cli."""

from __future__ import annotations

import argparse

import pytest

from ussy_cli import (
    ColorFormatter,
    SimpleProgress,
    StandardFlags,
    SubcommandDispatcher,
    render_table,
)


class TestColorFormatter:
    def test_no_color_returns_plain(self) -> None:
        fmt = ColorFormatter(no_color=True)
        assert fmt.red("hello") == "hello"
        assert fmt.bold("world") == "world"

    def test_color_wraps(self) -> None:
        # Force color by overriding env and isatty before constructing formatter
        import os
        import sys

        old_no_color = os.environ.pop("NO_COLOR", None)
        original = sys.stdout.isatty
        sys.stdout.isatty = lambda: True  # type: ignore[method-assign]
        try:
            fmt = ColorFormatter(no_color=False)
            assert "\033[31m" in fmt.red("hello")
            assert "\033[0m" in fmt.red("hello")
        finally:
            sys.stdout.isatty = original  # type: ignore[method-assign]
            if old_no_color is not None:
                os.environ["NO_COLOR"] = old_no_color


class TestStandardFlags:
    def test_adds_flags(self) -> None:
        parser = argparse.ArgumentParser()
        StandardFlags.add_to(parser)
        args = parser.parse_args(["--json", "--verbose", "--no-color"])
        assert args.json is True
        assert args.verbose is True
        assert args.no_color is True


class TestSubcommandDispatcher:
    def test_dispatch(self) -> None:
        def handler(args: argparse.Namespace) -> int:
            return 42

        disp = SubcommandDispatcher("test")
        sub = disp.add_command("run", handler, help_text="run it")
        sub.add_argument("--value", type=int, default=0)
        assert disp.run(["run", "--value", "7"]) == 42

    def test_no_command_prints_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        disp = SubcommandDispatcher("test")
        disp.add_command("run", lambda a: 0)
        code = disp.run([])
        assert code == 2
        captured = capsys.readouterr()
        assert "usage:" in captured.out


class TestSimpleProgress:
    def test_iterates(self) -> None:
        items = [1, 2, 3]
        with SimpleProgress(items, desc="test") as prog:
            result = list(prog)
        assert result == items

    def test_update(self) -> None:
        with SimpleProgress(total=10, desc="test") as prog:
            prog.update(3)
            assert prog._count == 3


class TestRenderTable:
    def test_ascii_fallback(self) -> None:
        headers = ["A", "B"]
        rows = [["1", "2"], ["3", "4"]]
        text = render_table(headers, rows, use_rich=False)
        assert "A | B" in text
        assert "1 | 2" in text

    def test_rich_if_available(self) -> None:
        headers = ["X"]
        rows = [["y"]]
        text = render_table(headers, rows, use_rich=True)
        assert "X" in text
        assert "y" in text
