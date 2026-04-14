"""Comment Steganography Scanner.

Checks comments and string literals for hidden data using Unicode steganography:

- Variation selectors (U+FE00-U+FE0F, U+E0100-U+E01EF) — can encode ~240 bits
- Combining characters that stack invisibly
- Modifier letters and superscript/subscript characters
- Unicode tag characters (U+E0000-U+E007F)
- Invisible characters in comments that could carry payloads
"""

from stenography.models import Finding, Severity, Context, SEVERITY_MAP
from stenography.context import classify_context

# Variation selectors — can be used to encode data in text
_VARIATION_SELECTORS = set(chr(c) for c in range(0xFE00, 0xFE0F + 1))
_VARIATION_SELECTORS_SUPPL = set(chr(c) for c in range(0xE0100, 0xE01EF + 1))

# Combining characters that could hide data
_COMBINING_MARKS = set()
for cp in range(0x0300, 0x036F + 1):  # Combining Diacritical Marks
    _COMBINING_MARKS.add(chr(cp))
for cp in range(0x1AB0, 0x1AFF + 1):  # Combining Diacritical Marks Extended
    _COMBINING_MARKS.add(chr(cp))
for cp in range(0x1DC0, 0x1DFF + 1):  # Combining Diacritical Marks Supplement
    _COMBINING_MARKS.add(chr(cp))
for cp in range(0x20D0, 0x20FF + 1):  # Combining Diacritical Marks for Symbols
    _COMBINING_MARKS.add(chr(cp))

# Modifier letters
_MODIFIER_LETTERS = set()
for cp in range(0x02B0, 0x02FF + 1):  # Spacing Modifier Letters
    _MODIFIER_LETTERS.add(chr(cp))
for cp in range(0xA700, 0xA71F + 1):  # Modifier Tone Letters
    _MODIFIER_LETTERS.add(chr(cp))

# Superscript/subscript characters that might hide in comments
_SUPERSCRIPT_SUBSCRIPT = set()
for cp in range(0x2070, 0x209F + 1):
    _SUPERSCRIPT_SUBSCRIPT.add(chr(cp))

# Tag characters — invisible, can encode arbitrary text
_TAG_CHARS = set()
for cp in range(0xE0000, 0xE007F + 1):
    try:
        _TAG_CHARS.add(chr(cp))
    except (ValueError, OverflowError):
        pass

# Characters that are suspicious in comments specifically
_COMMENT_SUSPICIOUS = _VARIATION_SELECTORS | _COMBINING_MARKS | _MODIFIER_LETTERS | _SUPERSCRIPT_SUBSCRIPT | _TAG_CHARS


class CommentScanner:
    """Scans comments and strings for Unicode steganography."""

    name = "comment"
    rule_id = "STEN005"

    def scan_line(self, file_path: str, line_num: int, line: str) -> list:
        """Scan a single line for comment steganography."""
        findings = []

        for col, ch in enumerate(line):
            # Check variation selectors
            if ch in _VARIATION_SELECTORS:
                ctx = classify_context(line, col)
                severity = SEVERITY_MAP.get(ctx, Severity.MEDIUM)
                findings.append(Finding(
                    scanner=self.name,
                    file=file_path,
                    line=line_num,
                    column=col + 1,
                    severity=severity,
                    context=ctx,
                    message=(
                        f"Variation selector in text: U+{ord(ch):04X} — "
                        f"can encode hidden data in visible text"
                    ),
                    char_code=f"U+{ord(ch):04X}",
                    character=ch,
                    context_text=self._extract_context(line, col),
                    rule_id="STEN005a",
                ))
                continue

            # Check combining marks
            if ch in _COMBINING_MARKS:
                ctx = classify_context(line, col)
                severity = SEVERITY_MAP.get(ctx, Severity.MEDIUM)
                # Check if this is an unusual number of combining marks
                count = self._count_consecutive_combining(line, col)
                if count >= 3:
                    severity = Severity.HIGH
                findings.append(Finding(
                    scanner=self.name,
                    file=file_path,
                    line=line_num,
                    column=col + 1,
                    severity=severity,
                    context=ctx,
                    message=(
                        f"Combining character in text: U+{ord(ch):04X} "
                        f"({count} consecutive) — can stack invisible data"
                    ),
                    char_code=f"U+{ord(ch):04X}",
                    character=ch,
                    context_text=self._extract_context(line, col),
                    rule_id="STEN005b",
                ))
                continue

            # Check modifier letters
            if ch in _MODIFIER_LETTERS:
                ctx = classify_context(line, col)
                severity = SEVERITY_MAP.get(ctx, Severity.MEDIUM)
                findings.append(Finding(
                    scanner=self.name,
                    file=file_path,
                    line=line_num,
                    column=col + 1,
                    severity=severity,
                    context=ctx,
                    message=(
                        f"Modifier letter in text: U+{ord(ch):04X} — "
                        f"may encode hidden data"
                    ),
                    char_code=f"U+{ord(ch):04X}",
                    character=ch,
                    context_text=self._extract_context(line, col),
                    rule_id="STEN005c",
                ))
                continue

            # Check tag characters
            if ch in _TAG_CHARS:
                ctx = classify_context(line, col)
                severity = Severity.CRITICAL  # Tag chars are very suspicious
                findings.append(Finding(
                    scanner=self.name,
                    file=file_path,
                    line=line_num,
                    column=col + 1,
                    severity=severity,
                    context=ctx,
                    message=(
                        f"Unicode tag character: U+{ord(ch):04X} — "
                        f"completely invisible, can encode arbitrary text"
                    ),
                    char_code=f"U+{ord(ch):04X}",
                    character=ch,
                    context_text=self._extract_context(line, col),
                    rule_id="STEN005d",
                ))
                continue

            # Check superscript/subscript
            if ch in _SUPERSCRIPT_SUBSCRIPT:
                ctx = classify_context(line, col)
                severity = SEVERITY_MAP.get(ctx, Severity.LOW)
                if ctx == Context.COMMENT:
                    severity = Severity.MEDIUM
                findings.append(Finding(
                    scanner=self.name,
                    file=file_path,
                    line=line_num,
                    column=col + 1,
                    severity=severity,
                    context=ctx,
                    message=(
                        f"Superscript/subscript character: U+{ord(ch):04X} — "
                        f"may be used to hide data in comments"
                    ),
                    char_code=f"U+{ord(ch):04X}",
                    character=ch,
                    context_text=self._extract_context(line, col),
                    rule_id="STEN005e",
                ))

        return findings

    def _count_consecutive_combining(self, line: str, start_col: int) -> int:
        """Count consecutive combining characters starting from position."""
        count = 0
        col = start_col
        while col < len(line) and line[col] in _COMBINING_MARKS:
            count += 1
            col += 1
        return count

    def _extract_context(self, line: str, col: int, window: int = 20) -> str:
        start = max(0, col - window)
        end = min(len(line), col + window + 1)
        return line[start:end]
