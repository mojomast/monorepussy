"""Fast mode detectors — lightweight scanners from the original stenography package.

These detectors provide quick checks for common steganographic attacks
without the full context-aware analysis. Used by the --fast CLI flag.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Optional

from ussy_steno.models import Finding, Severity, Context


# ── Zero-Width Detector (fast) ───────────────────────────────────────────────

ZERO_WIDTH = {
    "\u200b": "ZERO WIDTH SPACE",
    "\ufeff": "ZERO WIDTH NO-BREAK SPACE",
    "\u200c": "ZERO WIDTH NON-JOINER",
    "\u200d": "ZERO WIDTH JOINER",
    "\u2060": "WORD JOINER",
    "\u180e": "MONGOLIAN VOWEL SEPARATOR",
}


def detect_zero_width(text: str, path: str) -> list[Finding]:
    """Fast zero-width character detection."""
    findings: list[Finding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for column, ch in enumerate(line, start=1):
            if ch in ZERO_WIDTH:
                findings.append(
                    Finding(
                        scanner="zerowidth",
                        file=path,
                        line=line_no,
                        column=column,
                        severity=Severity.HIGH,
                        context=Context.OTHER,
                        message=f"Zero-width character {ZERO_WIDTH[ch]} detected",
                        char_code=f"U+{ord(ch):04X}",
                        character=ch,
                    )
                )
    return findings


# ── BiDi / RTL Detector (fast) ───────────────────────────────────────────────

BIDI = {
    "\u202a": "LEFT-TO-RIGHT EMBEDDING",
    "\u202b": "RIGHT-TO-LEFT EMBEDDING",
    "\u202c": "POP DIRECTIONAL FORMATTING",
    "\u202d": "LEFT-TO-RIGHT OVERRIDE",
    "\u202e": "RIGHT-TO-LEFT OVERRIDE",
    "\u2066": "LEFT-TO-RIGHT ISOLATE",
    "\u2067": "RIGHT-TO-LEFT ISOLATE",
    "\u2068": "FIRST STRONG ISOLATE",
    "\u2069": "POP DIRECTIONAL ISOLATE",
    "\u200e": "LEFT-TO-RIGHT MARK",
    "\u200f": "RIGHT-TO-LEFT MARK",
}


def detect_bidi(text: str, path: str) -> list[Finding]:
    """Fast BiDi control character detection."""
    findings: list[Finding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for column, ch in enumerate(line, start=1):
            if ch in BIDI:
                findings.append(
                    Finding(
                        scanner="bidi",
                        file=path,
                        line=line_no,
                        column=column,
                        severity=Severity.CRITICAL,
                        context=Context.OTHER,
                        message=f"BiDi control character {BIDI[ch]} detected",
                        char_code=f"U+{ord(ch):04X}",
                        character=ch,
                    )
                )
    return findings


# ── Homoglyph Detector (fast) ────────────────────────────────────────────────

IDENTIFIER_RE = re.compile(r"(?:[^\\W\\d]|_)(?:\\w*)", re.UNICODE)

CONFUSABLES = {
    # Cyrillic
    "а": "a",
    "о": "o",
    "е": "e",
    "с": "c",
    "р": "p",
    "х": "x",
    "і": "i",
    "у": "y",
    "к": "k",
    "м": "m",
    "н": "h",
    "в": "b",
    # Greek
    "α": "a",
    "ο": "o",
    "е": "e",
    "ρ": "p",
    "ν": "v",
    "μ": "m",
    "χ": "x",
    "ι": "i",
    "κ": "k",
    # Latin lookalikes
    "ℓ": "l",
    "ꞵ": "b",
}


def _skeleton(identifier: str) -> str:
    normalized = unicodedata.normalize("NFKC", identifier)
    return "".join(CONFUSABLES.get(ch, ch) for ch in normalized)


def detect_homoglyphs(text: str, path: str) -> list[Finding]:
    """Fast homoglyph detection in identifiers."""
    findings: list[Finding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in IDENTIFIER_RE.finditer(line):
            identifier = match.group(0)
            skeleton = _skeleton(identifier)
            if identifier != skeleton and any(ch in CONFUSABLES for ch in identifier):
                chars = sorted(
                    {f"{ch}->{CONFUSABLES[ch]}" for ch in identifier if ch in CONFUSABLES}
                )
                findings.append(
                    Finding(
                        scanner="homoglyph",
                        file=path,
                        line=line_no,
                        column=match.start() + 1,
                        severity=Severity.MEDIUM,
                        context=Context.IDENTIFIER,
                        message=f"Homoglyph characters detected in identifier '{identifier}' ({', '.join(chars)})",
                        character=identifier,
                        char_code=None,
                    )
                )
    return findings


# ── Confusable Identifier Detector (fast) ────────────────────────────────────


def detect_confusables(text: str, path: str) -> list[Finding]:
    """Detect confusable identifiers that share the same skeleton."""
    from collections import defaultdict

    occurrences: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in IDENTIFIER_RE.finditer(line):
            identifier = match.group(0)
            skeleton = _skeleton(identifier)
            occurrences[skeleton].append((identifier, line_no, match.start() + 1))

    findings: list[Finding] = []
    for skeleton, items in occurrences.items():
        unique = {ident for ident, _, _ in items}
        if len(unique) < 2:
            continue
        related = tuple(sorted(unique))
        message = f"Confusable identifiers share skeleton '{skeleton}': {', '.join(related)}"
        for identifier, line_no, column in items:
            findings.append(
                Finding(
                    scanner="confusable",
                    file=path,
                    line=line_no,
                    column=column,
                    severity=Severity.HIGH,
                    context=Context.IDENTIFIER,
                    message=message,
                    character=identifier,
                    char_code=None,
                )
            )
    return findings


# ── Fast Scanner Engine ──────────────────────────────────────────────────────


class FastScanner:
    """Lightweight scanner using only fast detectors."""

    def __init__(self):
        self.detectors = [
            detect_zero_width,
            detect_bidi,
            detect_homoglyphs,
            detect_confusables,
        ]

    def scan_text(self, text: str, path: str = "<str>") -> list[Finding]:
        """Scan text with all fast detectors."""
        findings: list[Finding] = []
        for detector in self.detectors:
            findings.extend(detector(text, path))
        return findings

    def scan_file(self, file_path: Path) -> list[Finding]:
        """Scan a single file."""
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return self.scan_text(text, str(file_path))
