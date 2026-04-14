"""Whitespace Steganography Detector.

Analyzes whitespace patterns for encoded data. Detects:

- Tab/space binary encoding (spaces=0, tabs=1) — a classic steganographic technique
- Trailing whitespace patterns that could encode data
- Unusual indentation anomalies (mixed tabs/spaces in same indent level)
- Entropy analysis to detect non-random vs random whitespace patterns

Uses Shannon entropy to determine if whitespace patterns are likely
encoding hidden data.
"""

import math
from collections import Counter
from stenography.models import Finding, Severity, Context
from stenography.context import classify_context


def _shannon_entropy(data: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not data:
        return 0.0
    counter = Counter(data)
    length = len(data)
    entropy = 0.0
    for count in counter.values():
        p = count / length
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def _decode_space_tab_binary(line: str) -> str:
    """Attempt to decode trailing whitespace as binary (space=0, tab=1)."""
    # Find trailing whitespace
    stripped = line.rstrip("\n\r")
    trailing_start = len(stripped.rstrip())
    if trailing_start >= len(stripped):
        return ""
    trailing = stripped[trailing_start:]

    if not trailing:
        return ""

    bits = []
    for ch in trailing:
        if ch == " ":
            bits.append("0")
        elif ch == "\t":
            bits.append("1")
        else:
            return ""  # Not pure space/tab

    # Try to decode as 8-bit ASCII
    if len(bits) >= 8:
        try:
            chars = []
            for i in range(0, len(bits) - 7, 8):
                byte = "".join(bits[i:i+8])
                val = int(byte, 2)
                if 32 <= val <= 126:
                    chars.append(chr(val))
                else:
                    chars.append("?")
            return "".join(chars) if chars else ""
        except (ValueError, IndexError):
            return ""
    return ""


class WhitespaceScanner:
    """Scans for whitespace steganography patterns."""

    name = "whitespace"
    rule_id = "STEN004"

    def __init__(self, entropy_threshold: float = 0.8):
        """Initialize with configurable entropy threshold.

        Args:
            entropy_threshold: Minimum Shannon entropy (0-1 range) to flag
                whitespace as potentially steganographic. Default 0.8.
        """
        self.entropy_threshold = entropy_threshold

    def scan_line(self, file_path: str, line_num: int, line: str) -> list:
        """Scan a single line for whitespace steganography."""
        findings = []

        # 1. Check trailing whitespace for binary encoding
        findings.extend(self._check_trailing_binary(file_path, line_num, line))

        # 2. Check for unusual trailing whitespace length
        findings.extend(self._check_trailing_length(file_path, line_num, line))

        # 3. Check for mixed tabs/spaces in indentation
        findings.extend(self._check_mixed_indent(file_path, line_num, line))

        # 4. Entropy analysis of whitespace patterns
        findings.extend(self._check_whitespace_entropy(file_path, line_num, line))

        return findings

    def _check_trailing_binary(self, file_path: str, line_num: int, line: str) -> list:
        """Check if trailing whitespace encodes binary data."""
        findings = []
        decoded = _decode_space_tab_binary(line)
        if decoded and len(decoded) >= 2:
            findings.append(Finding(
                scanner=self.name,
                file=file_path,
                line=line_num,
                column=len(line.rstrip("\n\r").rstrip()) + 1,
                severity=Severity.HIGH,
                context=Context.WHITESPACE,
                message=(
                    f"Trailing whitespace encodes binary data: "
                    f"decoded='{decoded}'"
                ),
                char_code=None,
                character=None,
                context_text=f"trailing: {repr(line.rstrip('\n\r')[len(line.rstrip('\n\r').rstrip()):])}",
                rule_id="STEN004a",
            ))
        return findings

    def _check_trailing_length(self, file_path: str, line_num: int, line: str) -> list:
        """Flag unusually long trailing whitespace."""
        findings = []
        stripped = line.rstrip("\n\r")
        trailing_len = len(stripped) - len(stripped.rstrip())
        if trailing_len >= 4:
            findings.append(Finding(
                scanner=self.name,
                file=file_path,
                line=line_num,
                column=len(stripped.rstrip()) + 1,
                severity=Severity.LOW,
                context=Context.WHITESPACE,
                message=f"Unusual trailing whitespace: {trailing_len} characters",
                char_code=None,
                character=None,
                context_text=f"length={trailing_len}",
                rule_id="STEN004b",
            ))
        return findings

    def _check_mixed_indent(self, file_path: str, line_num: int, line: str) -> list:
        """Check for mixed tab/space indentation — could encode data."""
        findings = []
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]

        if not indent:
            return findings

        has_spaces = " " in indent
        has_tabs = "\t" in indent

        if has_spaces and has_tabs:
            # Calculate entropy of the indentation
            entropy = _shannon_entropy(indent)
            # Normalize by max possible entropy
            max_entropy = math.log2(len(set(indent))) if len(set(indent)) > 1 else 1
            norm_entropy = entropy / max_entropy if max_entropy > 0 else 0

            severity = Severity.MEDIUM
            if norm_entropy > self.entropy_threshold:
                severity = Severity.HIGH

            findings.append(Finding(
                scanner=self.name,
                file=file_path,
                line=line_num,
                column=1,
                severity=severity,
                context=Context.WHITESPACE,
                message=(
                    f"Mixed tab/space indentation (entropy={entropy:.2f}, "
                    f"normalized={norm_entropy:.2f}): potential steganographic encoding"
                ),
                char_code=None,
                character=None,
                context_text=f"indent: {repr(indent)}",
                rule_id="STEN004c",
            ))
        return findings

    def _check_whitespace_entropy(self, file_path: str, line_num: int, line: str) -> list:
        """Analyze overall whitespace entropy for anomalous patterns."""
        findings = []
        # Extract all whitespace from the line
        ws_chars = "".join(ch for ch in line if ch in " \t")
        if len(ws_chars) < 8:
            return findings

        entropy = _shannon_entropy(ws_chars)
        # Max entropy for space/tab is 1.0
        # If we have high entropy in whitespace, it could be encoding data
        if entropy > self.entropy_threshold:
            findings.append(Finding(
                scanner=self.name,
                file=file_path,
                line=line_num,
                column=1,
                severity=Severity.MEDIUM,
                context=Context.WHITESPACE,
                message=(
                    f"High whitespace entropy ({entropy:.3f}): "
                    f"whitespace patterns may encode hidden data"
                ),
                char_code=None,
                character=None,
                context_text=f"entropy={entropy:.3f}, ws_len={len(ws_chars)}",
                rule_id="STEN004d",
            ))
        return findings
