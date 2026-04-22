"""Zero-Width Character Scanner.

Detects all zero-width Unicode characters in source files including:
- ZWJ (U+200D)
- ZWNJ (U+200C)
- ZWSP (U+200B)
- Word Joiner (U+2060)
- Zero Width No-Break Space (U+FEFF)
- Left-to-Right Mark (U+200E)
- Right-to-Left Mark (U+200F)
- Function Application (U+2061)
- Invisible Plus (U+2064)
- Invisible Separator (U+2063)
- Invisible Times (U+2062)
- Interlinear Annotation Anchor (U+FFF9)
- Interlinear Annotation Separator (U+FFFA)
- Interlinear Annotation Terminator (U+FFFB)
- Object Replacement Character (U+FFFC)
- And more...
"""

from stenography.models import Finding, Severity, Context, SEVERITY_MAP
from stenography.context import classify_context

# Comprehensive zero-width / invisible character database
ZERO_WIDTH_CHARS = {
    "\u200B": ("ZWSP", "Zero Width Space"),
    "\u200C": ("ZWNJ", "Zero Width Non-Joiner"),
    "\u200D": ("ZWJ", "Zero Width Joiner"),
    "\u200E": ("LRM", "Left-to-Right Mark"),
    "\u200F": ("RLM", "Right-to-Left Mark"),
    "\u2060": ("WJ", "Word Joiner"),
    "\u2061": ("FA", "Function Application"),
    "\u2062": ("IT", "Invisible Times"),
    "\u2063": ("IS", "Invisible Separator"),
    "\u2064": ("IP", "Invisible Plus"),
    "\uFEFF": ("ZWNBSP", "Zero Width No-Break Space / BOM"),
    "\uFFF9": ("IAA", "Interlinear Annotation Anchor"),
    "\uFFFA": ("IAS", "Interlinear Annotation Separator"),
    "\uFFFB": ("IAT", "Interlinear Annotation Terminator"),
    "\uFFFC": ("ORC", "Object Replacement Character"),
    "\u00AD": ("SHY", "Soft Hyphen"),
    "\u034F": ("CGJ", "Combining Grapheme Joiner"),
    "\u061C": ("ALM", "Arabic Letter Mark"),
    "\u180E": ("MVS", "Mongolian Vowel Separator"),
    "\u202A": ("LRE", "Left-to-Right Embedding"),
    "\u202B": ("RLE", "Right-to-Left Embedding"),
    "\u202C": ("PDF", "Pop Directional Formatting"),
    "\u202D": ("LRO", "Left-to-Right Override"),
    "\u202E": ("RLO", "Right-to-Left Override"),
    "\u2066": ("LRI", "Left-to-Right Isolate"),
    "\u2067": ("RLI", "Right-to-Left Isolate"),
    "\u2068": ("FSI", "First Strong Isolate"),
    "\u2069": ("PDI", "Pop Directional Isolate"),
    "\u206A": ("ISS", "Inhibit Symmetric Swapping"),
    "\u206B": ("ASS", "Activate Symmetric Swapping"),
    "\u206C": ("IAFS", "Inhibit Arabic Form Shaping"),
    "\u206D": ("AAFS", "Activate Arabic Form Shaping"),
    "\u206E": ("NADS", "National Digit Shapes"),
    "\u206F": ("NODS", "Nominal Digit Shapes"),
    "\uFE00": ("VS1", "Variation Selector 1"),
    "\uFE01": ("VS2", "Variation Selector 2"),
    "\uFE02": ("VS3", "Variation Selector 3"),
    "\uFE03": ("VS4", "Variation Selector 4"),
    "\uFE04": ("VS5", "Variation Selector 5"),
    "\uFE05": ("VS6", "Variation Selector 6"),
    "\uFE06": ("VS7", "Variation Selector 7"),
    "\uFE07": ("VS8", "Variation Selector 8"),
    "\uFE08": ("VS9", "Variation Selector 9"),
    "\uFE09": ("VS10", "Variation Selector 10"),
    "\uFE0A": ("VS11", "Variation Selector 11"),
    "\uFE0B": ("VS12", "Variation Selector 12"),
    "\uFE0C": ("VS13", "Variation Selector 13"),
    "\uFE0D": ("VS14", "Variation Selector 14"),
    "\uFE0E": ("VS15", "Variation Selector 15 — Text Presentation"),
    "\uFE0F": ("VS16", "Variation Selector 16 — Emoji Presentation"),
    "\uE0000": ("VS17", "Variation Selector 17"),
    "\uE0001": ("VS18", "Variation Selector 18"),
    "\uE0020": ("TAG SPACE", "Tag Space Character"),
    "\uE007F": ("TAG_CANCEL", "Tag Cancel Character"),
}

# Shortcuts for the most critical ones
_CRITICAL_ZW = {"\u200B", "\u200C", "\u200D", "\uFEFF", "\u200E", "\u200F"}


class ZeroWidthScanner:
    """Scans for zero-width and invisible Unicode characters."""

    name = "zero_width"
    rule_id = "STEN001"

    def scan_line(self, file_path: str, line_num: int, line: str) -> list:
        """Scan a single line for zero-width characters."""
        findings = []
        for col, ch in enumerate(line):
            if ch in ZERO_WIDTH_CHARS:
                short_name, full_name = ZERO_WIDTH_CHARS[ch]
                ctx = classify_context(line, col)
                severity = SEVERITY_MAP.get(ctx, Severity.INFO)

                # Escalate if in critical set
                if ch in _CRITICAL_ZW and severity == Severity.INFO:
                    severity = Severity.MEDIUM

                context_text = self._extract_context(line, col)

                findings.append(Finding(
                    scanner=self.name,
                    file=file_path,
                    line=line_num,
                    column=col + 1,
                    severity=severity,
                    context=ctx,
                    message=f"Zero-width character detected: {full_name} (U+{ord(ch):04X})",
                    char_code=f"U+{ord(ch):04X}",
                    character=ch,
                    context_text=context_text,
                    rule_id=self.rule_id,
                ))
        return findings

    def _extract_context(self, line: str, col: int, window: int = 20) -> str:
        """Extract a window of visible context around the finding."""
        start = max(0, col - window)
        end = min(len(line), col + window + 1)
        context = line[start:end]
        # Replace invisible chars with visible markers for display
        result = []
        for i, ch in enumerate(context):
            if ch in ZERO_WIDTH_CHARS:
                result.append(f"[ZW:{ord(ch):04X}]")
            else:
                result.append(ch)
        return "".join(result)
