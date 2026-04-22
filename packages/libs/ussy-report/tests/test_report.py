"""Tests for ussy_report."""

from __future__ import annotations

from ussy_report import (
    JsonOutput,
    MarkdownReport,
    SarifBuilder,
    render_ascii_table,
    render_unicode_table,
    terminal_width,
)


class TestTerminalWidth:
    def test_returns_positive(self) -> None:
        w = terminal_width()
        assert isinstance(w, int)
        assert w > 0


class TestRenderAsciiTable:
    def test_basic(self) -> None:
        text = render_ascii_table(["A", "B"], [["1", "2"]])
        assert "A | B" in text
        assert "1 | 2" in text

    def test_truncate(self) -> None:
        text = render_ascii_table(["A", "B"], [["verylong", "value"]], max_width=10)
        assert "A" in text


class TestRenderUnicodeTable:
    def test_basic(self) -> None:
        text = render_unicode_table(["X"], [["y"]])
        assert "X" in text
        assert "y" in text
        assert "┌" in text


class TestJsonOutput:
    def test_set_and_json(self) -> None:
        out = JsonOutput()
        out.set("tool", "test").add_result({"file": "a.py"})
        data = out.to_dict()
        assert data["tool"] == "test"
        assert data["results"] == [{"file": "a.py"}]


class TestSarifBuilder:
    def test_build(self) -> None:
        sarif = (
            SarifBuilder("test-tool", "1.0.0")
            .add_rule("R1", "rule-one", "Short desc")
            .add_result("R1", "Found issue", uri="file.py", start_line=5)
            .build()
        )
        assert sarif["version"] == "2.1.0"
        assert len(sarif["runs"]) == 1
        run = sarif["runs"][0]
        assert run["tool"]["driver"]["name"] == "test-tool"
        assert len(run["results"]) == 1
        assert run["results"][0]["ruleId"] == "R1"


class TestMarkdownReport:
    def test_output(self) -> None:
        md = MarkdownReport("My Report")
        md.heading("Details").paragraph("Something happened.").table(
            ["A", "B"], [["1", "2"]]
        )
        text = md.to_markdown()
        assert "# My Report" in text
        assert "## Details" in text
        assert "Something happened." in text
        assert "| A | B |" in text
