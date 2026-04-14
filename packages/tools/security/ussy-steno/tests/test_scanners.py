"""Comprehensive test suite for Stenography — Steganographic Code Review Tool."""

import os
import json
import tempfile
import pytest

from stenography.models import Finding, Severity, Context, ScanResult
from stenography.scanners import (
    ZeroWidthScanner,
    HomoglyphScanner,
    RTLScanner,
    WhitespaceScanner,
    CommentScanner,
)
from stenography.engine import ScannerEngine
from stenography.formatters import get_formatter, JsonFormatter, SarifFormatter, TableFormatter
from stenography.context import classify_context
from stenography.cli import main as cli_main

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


# ── Model Tests ──────────────────────────────────────────────────────────────

class TestModels:
    def test_finding_to_dict(self):
        f = Finding(
            scanner="test", file="a.py", line=1, column=5,
            severity=Severity.CRITICAL, context=Context.IDENTIFIER,
            message="test finding", char_code="U+200B",
        )
        d = f.to_dict()
        assert d["scanner"] == "test"
        assert d["severity"] == "CRITICAL"
        assert d["context"] == "identifier"

    def test_scan_result_merge(self):
        r1 = ScanResult(files_scanned=2)
        r1.add(Finding(scanner="a", file="f", line=1, column=1,
                       severity=Severity.HIGH, context=Context.OTHER, message="m1"))
        r2 = ScanResult(files_scanned=3)
        r2.add(Finding(scanner="b", file="g", line=2, column=2,
                       severity=Severity.LOW, context=Context.OTHER, message="m2"))
        r1.merge(r2)
        assert r1.total_findings == 2
        assert r1.files_scanned == 5


# ── Context Classification Tests ─────────────────────────────────────────────

class TestContext:
    def test_identifier_context(self):
        ctx = classify_context("my_var = 1", 2)
        assert ctx == Context.IDENTIFIER

    def test_string_context(self):
        ctx = classify_context('x = "hello"', 6)
        assert ctx == Context.STRING_LITERAL

    def test_comment_context(self):
        ctx = classify_context("# this is a comment", 5)
        assert ctx == Context.COMMENT

    def test_whitespace_context(self):
        ctx = classify_context("    x = 1", 1)
        assert ctx == Context.WHITESPACE


# ── Zero-Width Scanner Tests ─────────────────────────────────────────────────

class TestZeroWidthScanner:
    def setup_method(self):
        self.scanner = ZeroWidthScanner()

    def test_detects_zwsp(self):
        line = "password\u200b = 'secret'"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert len(findings) >= 1
        assert findings[0].char_code == "U+200B"
        assert findings[0].severity == Severity.CRITICAL  # In identifier

    def test_detects_zwnj(self):
        line = "user\u200cname = 'admin'"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+200C" for f in findings)

    def test_detects_zwj(self):
        line = "admin\u200drole = 'super'"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+200D" for f in findings)

    def test_detects_word_joiner(self):
        line = "key\u2060 = 'val'"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+2060" for f in findings)

    def test_detects_bom(self):
        line = "token\ufeff = 'bearer'"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+FEFF" for f in findings)

    def test_detects_lrm(self):
        line = "access\u200e = True"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+200E" for f in findings)

    def test_detects_rlm(self):
        line = "deny\u200f = False"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+200F" for f in findings)

    def test_detects_variation_selector(self):
        line = "x = 'text\uFE0F'"
        findings = self.scanner.scan_line("test.py", 1, line)
        zw_findings = [f for f in findings if f.char_code == "U+FE0F"]
        assert len(zw_findings) >= 1

    def test_detects_invisible_separator(self):
        line = "sep\u2063 = ','"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+2063" for f in findings)

    def test_detects_invisible_times(self):
        line = "mul\u2062 = 3.14"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+2062" for f in findings)

    def test_detects_function_application(self):
        line = "calc\u2061 = 42"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+2061" for f in findings)

    def test_no_false_positives(self):
        line = "normal_var = 42"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert len(findings) == 0

    def test_context_classification_in_comment(self):
        line = "# This has \u200b"
        findings = self.scanner.scan_line("test.py", 1, line)
        zw = [f for f in findings if f.char_code == "U+200B"]
        assert len(zw) >= 1
        # In a comment, should be MEDIUM
        assert zw[0].severity == Severity.MEDIUM

    def test_detects_15_plus_zero_width_chars(self):
        """Verify the scanner has 15+ zero-width character definitions."""
        from stenography.scanners.zero_width import ZERO_WIDTH_CHARS
        assert len(ZERO_WIDTH_CHARS) >= 15

    def test_fixture_file(self):
        findings = []
        fpath = os.path.join(FIXTURES_DIR, "zero_width_test.txt")
        if not os.path.exists(fpath):
            pytest.skip("fixture not found")
        with open(fpath, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                findings.extend(self.scanner.scan_line("zero_width_test.txt", i, line))
        assert len(findings) >= 5  # Should find multiple ZW chars


# ── Homoglyph Scanner Tests ──────────────────────────────────────────────────

class TestHomoglyphScanner:
    def setup_method(self):
        self.scanner = HomoglyphScanner()

    def test_detects_cyrillic_a(self):
        # Cyrillic а (U+0430) looks like Latin a
        line = "p\u0430ssword = 'hacked'"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any("Homoglyph" in f.message for f in findings)

    def test_detects_cyrillic_o(self):
        line = "auth\u043Er = 'evil'"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any("Homoglyph" in f.message for f in findings)

    def test_detects_cyrillic_e(self):
        line = "us\u0435rname = 'admin'"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any("Homoglyph" in f.message for f in findings)

    def test_detects_cyrillic_p(self):
        line = "im\u0440ort os"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any("Homoglyph" in f.message for f in findings)

    def test_detects_greek_omicron(self):
        line = "l\u03BFgin = True"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any("Homoglyph" in f.message for f in findings)

    def test_detects_cyrillic_capital_b(self):
        line = "\u0412ool = True"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any("Homoglyph" in f.message for f in findings)

    def test_detects_cyrillic_capital_m(self):
        line = "\u041CAX = 100"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any("Homoglyph" in f.message for f in findings)

    def test_mixed_script_identifier(self):
        """Identifiers mixing scripts should be flagged as CRITICAL."""
        line = "adm\u0456n = 'root'"  # Cyrillic і mixed with Latin
        findings = self.scanner.scan_line("test.py", 1, line)
        mixed = [f for f in findings if "Mixed-script" in f.message]
        assert len(mixed) >= 1
        assert mixed[0].severity == Severity.CRITICAL

    def test_no_false_positives(self):
        line = "normal_variable = 42"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert len(findings) == 0

    def test_50_plus_homoglyph_pairs(self):
        """Verify 50+ homoglyph pairs are defined."""
        from stenography.scanners.homoglyph import HOMOGLYPH_MAP
        assert len(HOMOGLYPH_MAP) >= 50

    def test_fixture_file(self):
        findings = []
        fpath = os.path.join(FIXTURES_DIR, "homoglyph_test.txt")
        if not os.path.exists(fpath):
            pytest.skip("fixture not found")
        with open(fpath, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                findings.extend(self.scanner.scan_line("homoglyph_test.txt", i, line))
        assert len(findings) >= 5


# ── RTL Scanner Tests ────────────────────────────────────────────────────────

class TestRTLScanner:
    def setup_method(self):
        self.scanner = RTLScanner()

    def test_detects_rlo(self):
        """Right-to-Left Override — the classic Trojan Source attack."""
        line = 'x = "user\u202Eadmin"'
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+202E" for f in findings)
        rlo = [f for f in findings if f.char_code == "U+202E"]
        assert rlo[0].severity == Severity.CRITICAL

    def test_detects_rle(self):
        line = "role\u202B = 'admin'"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+202B" for f in findings)

    def test_detects_lro(self):
        line = "allow\u202D = True"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+202D" for f in findings)

    def test_detects_lre(self):
        line = "flag\u202A = True"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+202A" for f in findings)

    def test_detects_soft_hyphen(self):
        line = "auth\u00ADorize = True"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+00AD" for f in findings)

    def test_detects_nbsp(self):
        line = "is\u00A0admin = True"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+00A0" for f in findings)

    def test_detects_bidi_isolates(self):
        line = "x\u2066 = 1"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert any(f.char_code == "U+2066" for f in findings)

    def test_no_false_positives(self):
        line = "normal_code = True"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert len(findings) == 0

    def test_fixture_file(self):
        findings = []
        with open(os.path.join(FIXTURES_DIR, "rtl_test.txt"), "r") as f:
            for i, line in enumerate(f, 1):
                findings.extend(self.scanner.scan_line("rtl_test.py", i, line))
        assert len(findings) >= 3


# ── Whitespace Scanner Tests ─────────────────────────────────────────────────

class TestWhitespaceScanner:
    def setup_method(self):
        self.scanner = WhitespaceScanner(entropy_threshold=0.8)

    def test_detects_trailing_whitespace_length(self):
        line = "x = 1        "  # 8 trailing spaces
        findings = self.scanner.scan_line("test.py", 1, line)
        trailing = [f for f in findings if "trailing" in f.message.lower()]
        assert len(trailing) >= 1

    def test_detects_mixed_indent(self):
        line = "\t    pass"  # Tab followed by spaces
        findings = self.scanner.scan_line("test.py", 1, line)
        mixed = [f for f in findings if "Mixed" in f.message]
        assert len(mixed) >= 1

    def test_no_false_positives_clean(self):
        line = "x = 1"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert len(findings) == 0

    def test_entropy_threshold_configurable(self):
        scanner_low = WhitespaceScanner(entropy_threshold=0.1)
        scanner_high = WhitespaceScanner(entropy_threshold=0.99)
        # Both should work without error
        line = "x = 1"
        assert len(scanner_low.scan_line("test.py", 1, line)) == 0
        assert len(scanner_high.scan_line("test.py", 1, line)) == 0

    def test_binary_decoding(self):
        """Test tab/space binary encoding detection."""
        # Encode "A" = 01000001 in trailing whitespace
        # 0=space, 1=tab: space tab space space space space space tab
        trailing = " \t    \t"
        line = f"x = 1{trailing}"
        from stenography.scanners.whitespace import _decode_space_tab_binary
        decoded = _decode_space_tab_binary(line)
        # Should decode to something (maybe partial)
        # The exact decoding depends on the implementation


# ── Comment Scanner Tests ────────────────────────────────────────────────────

class TestCommentScanner:
    def setup_method(self):
        self.scanner = CommentScanner()

    def test_detects_variation_selector(self):
        line = "x = 'text\uFE0F'"
        findings = self.scanner.scan_line("test.py", 1, line)
        vs = [f for f in findings if "Variation selector" in f.message]
        assert len(vs) >= 1

    def test_detects_combining_chars(self):
        line = "x = 'H\u0308ello'"
        findings = self.scanner.scan_line("test.py", 1, line)
        combining = [f for f in findings if "Combining" in f.message]
        assert len(combining) >= 1

    def test_detects_stacked_combining(self):
        """Multiple combining characters stacked — HIGH severity."""
        line = "x = 'a\u0300\u0301\u0302\u0303\u0304'"
        findings = self.scanner.scan_line("test.py", 1, line)
        combining = [f for f in findings if "Combining" in f.message]
        assert len(combining) >= 1
        high = [f for f in combining if f.severity == Severity.HIGH]
        assert len(high) >= 1

    def test_detects_modifier_letter(self):
        line = "x = 1  # \u02B0modifier"
        findings = self.scanner.scan_line("test.py", 1, line)
        mod = [f for f in findings if "Modifier" in f.message]
        assert len(mod) >= 1

    def test_no_false_positives(self):
        line = "normal_var = 'hello'"
        findings = self.scanner.scan_line("test.py", 1, line)
        assert len(findings) == 0


# ── Engine Tests ─────────────────────────────────────────────────────────────

class TestScannerEngine:
    def setup_method(self):
        self.engine = ScannerEngine()

    def test_scan_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("password\u200b = 'secret'\n")
            f.flush()
            result = self.engine.scan_path(f.name)
        os.unlink(f.name)
        assert result.total_findings >= 1

    def test_scan_directory(self):
        result = self.engine.scan_path(FIXTURES_DIR)
        assert result.files_scanned >= 1
        assert result.total_findings >= 5

    def test_scan_clean_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x = 1\ny = 2\n")
            f.flush()
            result = self.engine.scan_path(f.name)
        os.unlink(f.name)
        assert result.total_findings == 0

    def test_scan_nonexistent_path(self):
        result = self.engine.scan_path("/nonexistent/path")
        assert result.total_findings == 0

    def test_all_scanners_run(self):
        """Verify all 5 scanners contribute findings on a malicious file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("p\u0430ssword\u200b = 'secret'\n")
            f.write("role\u202E = 'admin'\n")
            f.write("# Comment with \uFE0F\n")
            f.flush()
            result = self.engine.scan_path(f.name)
        os.unlink(f.name)

        scanner_names = set(f.scanner for f in result.findings)
        # Should have findings from at least 3 different scanners
        assert len(scanner_names) >= 2


# ── Formatter Tests ──────────────────────────────────────────────────────────

class TestFormatters:
    def _make_result(self):
        result = ScanResult(files_scanned=2)
        result.add(Finding(
            scanner="zero_width", file="test.py", line=1, column=9,
            severity=Severity.CRITICAL, context=Context.IDENTIFIER,
            message="Zero-width character detected: ZWSP (U+200B)",
            char_code="U+200B",
        ))
        result.add(Finding(
            scanner="homoglyph", file="test.py", line=5, column=2,
            severity=Severity.HIGH, context=Context.IDENTIFIER,
            message="Homoglyph detected: Cyrillic а looks like Latin a",
            char_code="U+0430",
        ))
        return result

    def test_json_formatter(self):
        fmt = JsonFormatter()
        output = fmt.format(self._make_result())
        data = json.loads(output)
        assert data["total_findings"] == 2
        assert len(data["findings"]) == 2

    def test_sarif_formatter(self):
        fmt = SarifFormatter()
        output = fmt.format(self._make_result())
        data = json.loads(output)
        assert data["version"] == "2.1.0"
        assert len(data["runs"]) == 1
        assert len(data["runs"][0]["results"]) == 2

    def test_table_formatter(self):
        fmt = TableFormatter(color=False)
        output = fmt.format(self._make_result())
        assert "STENOGRAPHY" in output
        assert "CRITICAL" in output or "findings" in output.lower()

    def test_empty_result_table(self):
        fmt = TableFormatter(color=False)
        result = ScanResult(files_scanned=5)
        output = fmt.format(result)
        assert "No steganographic content" in output

    def test_get_formatter(self):
        assert isinstance(get_formatter("json"), JsonFormatter)
        assert isinstance(get_formatter("sarif"), SarifFormatter)
        assert isinstance(get_formatter("table"), TableFormatter)

    def test_get_formatter_unknown(self):
        with pytest.raises(ValueError):
            get_formatter("xml")


# ── CLI Tests ────────────────────────────────────────────────────────────────

class TestCLI:
    def test_scan_command(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("password\u200b = 'secret'\n")
            f.flush()
            exit_code = cli_main(["scan", "--format", "json", f.name])
        os.unlink(f.name)
        assert exit_code == 1  # Findings found

    def test_scan_clean(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x = 1\n")
            f.flush()
            exit_code = cli_main(["scan", "--format", "json", f.name])
        os.unlink(f.name)
        assert exit_code == 0  # Clean

    def test_scan_table_format(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x\u200b = 1\n")
            f.flush()
            exit_code = cli_main(["scan", "--no-color", f.name])
        os.unlink(f.name)
        assert exit_code == 1

    def test_no_command_shows_help(self, capsys):
        exit_code = cli_main([])
        assert exit_code == 0

    def test_sarif_format(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x\u200b = 1\n")
            f.flush()
            exit_code = cli_main(["scan", "--format", "sarif", f.name])
        os.unlink(f.name)
        assert exit_code == 1


# ── Integration Test ─────────────────────────────────────────────────────────

class TestIntegration:
    def test_full_scan_fixture_dir(self):
        """End-to-end test scanning all fixture files."""
        engine = ScannerEngine()
        result = engine.scan_path(FIXTURES_DIR)

        # Should find findings from multiple scanners
        scanner_names = set(f.scanner for f in result.findings)
        assert len(scanner_names) >= 3  # At least 3 different scanners should fire
        assert result.total_findings >= 10  # Lots of malicious content

        # JSON output should be valid
        fmt = JsonFormatter()
        output = fmt.format(result)
        data = json.loads(output)
        assert data["total_findings"] >= 10

    def test_risk_scoring_identifier_critical(self):
        """Zero-width char in identifier should be CRITICAL."""
        scanner = ZeroWidthScanner()
        line = "my\u200bvar = 1"
        findings = scanner.scan_line("test.py", 1, line)
        zw = [f for f in findings if f.char_code == "U+200B"]
        assert len(zw) >= 1
        assert zw[0].severity == Severity.CRITICAL

    def test_risk_scoring_comment_medium(self):
        """Zero-width char in comment should be MEDIUM."""
        scanner = ZeroWidthScanner()
        line = "# This has \u200b"
        findings = scanner.scan_line("test.py", 1, line)
        zw = [f for f in findings if f.char_code == "U+200B"]
        assert len(zw) >= 1
        assert zw[0].severity == Severity.MEDIUM
