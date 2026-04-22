"""RTL / Formatting Exploit Scanner.

Detects right-to-left overrides, bidi controls, and invisible formatting
characters that change how code renders vs executes. This covers the
"Trojan Source" class of attacks.

Flags:
- U+202A-U+202E: Bidi embedding/override controls
- U+2066-U+2069: Bidi isolate controls
- Soft hyphens (U+00AD)
- Non-breaking spaces in source (U+00A0)
- Other dangerous formatting characters
"""

from stenography.models import Finding, Severity, Context, SEVERITY_MAP
from stenography.context import classify_context

# RTL and formatting exploit characters
RTL_FORMATTING_CHARS = {
    "\u202A": ("LRE", "Left-to-Right Embedding"),
    "\u202B": ("RLE", "Right-to-Left Embedding"),
    "\u202C": ("PDF", "Pop Directional Formatting"),
    "\u202D": ("LRO", "Left-to-Right Override"),
    "\u202E": ("RLO", "Right-to-Left Override"),
    "\u2066": ("LRI", "Left-to-Right Isolate"),
    "\u2067": ("RLI", "Right-to-Left Isolate"),
    "\u2068": ("FSI", "First Strong Isolate"),
    "\u2069": ("PDI", "Pop Directional Isolate"),
    "\u200E": ("LRM", "Left-to-Right Mark"),
    "\u200F": ("RLM", "Right-to-Left Mark"),
    "\u061C": ("ALM", "Arabic Letter Mark"),
    "\u00AD": ("SHY", "Soft Hyphen"),
    "\u00A0": ("NBSP", "Non-Breaking Space"),
    "\u2028": ("LSEP", "Line Separator"),
    "\u2029": ("PSEP", "Paragraph Separator"),
    "\u206A": ("ISS", "Inhibit Symmetric Swapping"),
    "\u206B": ("ASS", "Activate Symmetric Swapping"),
    "\u206C": ("IAFS", "Inhibit Arabic Form Shaping"),
    "\u206D": ("AAFS", "Activate Arabic Form Shaping"),
    "\u206E": ("NADS", "National Digit Shapes"),
    "\u206F": ("NODS", "Nominal Digit Shapes"),
    "\uFEFF": ("ZWNBSP", "Zero Width No-Break Space / BOM"),
}

# The most dangerous ones for Trojan Source attacks
_TROJAN_SOURCE_CHARS = {"\u202A", "\u202B", "\u202D", "\u202E", "\u2066", "\u2067", "\u2068", "\u2069"}


class RTLScanner:
    """Scans for RTL override and formatting exploit characters."""

    name = "rtl"
    rule_id = "STEN003"

    def scan_line(self, file_path: str, line_num: int, line: str) -> list:
        """Scan a single line for RTL/formatting exploits."""
        findings = []

        for col, ch in enumerate(line):
            if ch in RTL_FORMATTING_CHARS:
                short_name, full_name = RTL_FORMATTING_CHARS[ch]
                ctx = classify_context(line, col)

                # RTL overrides in identifiers are the most dangerous
                if ch in _TROJAN_SOURCE_CHARS:
                    severity = Severity.CRITICAL
                elif ch == "\u00AD":
                    severity = SEVERITY_MAP.get(ctx, Severity.MEDIUM)
                    if ctx == Context.IDENTIFIER:
                        severity = Severity.CRITICAL
                elif ch == "\u00A0":
                    severity = Severity.LOW
                    if ctx == Context.IDENTIFIER:
                        severity = Severity.HIGH
                else:
                    severity = SEVERITY_MAP.get(ctx, Severity.HIGH)

                context_text = self._extract_context(line, col)

                findings.append(Finding(
                    scanner=self.name,
                    file=file_path,
                    line=line_num,
                    column=col + 1,
                    severity=severity,
                    context=ctx,
                    message=(
                        f"RTL/formatting exploit: {full_name} "
                        f"({short_name}, U+{ord(ch):04X})"
                    ),
                    char_code=f"U+{ord(ch):04X}",
                    character=ch,
                    context_text=context_text,
                    rule_id=self.rule_id,
                ))

        return findings

    def _extract_context(self, line: str, col: int, window: int = 30) -> str:
        start = max(0, col - window)
        end = min(len(line), col + window + 1)
        context = line[start:end]
        # Make invisible chars visible
        result = []
        for ch in context:
            if ch in RTL_FORMATTING_CHARS:
                short_name = RTL_FORMATTING_CHARS[ch][0]
                result.append(f"[{short_name}]")
            elif ch == "\u00A0":
                result.append("[NBSP]")
            else:
                result.append(ch)
        return "".join(result)
