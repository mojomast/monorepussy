"""Homoglyph Detector.

Scans identifiers and string literals for mixed-script characters that look
identical but have different Unicode codepoints. Covers:

- Cyrillic/Latin confusables (e.g., Cyrillic а vs Latin a)
- Greek/Latin confusables (e.g., Greek ο vs Latin o)
- Lookalike digits (0/O, 1/l/I)
- Full-width variants
- Custom developer-relevant pairs

Includes 50+ known homoglyph pairs.
"""

import unicodedata
from stenography.models import Finding, Severity, Context, SEVERITY_MAP
from stenography.context import classify_context

# Comprehensive homoglyph mapping: confusable -> canonical Latin equivalent
# Each entry is a (confusable_char, latin_equivalent, script_name) tuple
HOMOGLYPH_MAP = {
    # Cyrillic а-я that look like Latin
    "\u0430": ("a", "Cyrillic"),   # Cyrillic а -> Latin a
    "\u0435": ("e", "Cyrillic"),   # Cyrillic е -> Latin e
    "\u043E": ("o", "Cyrillic"),   # Cyrillic о -> Latin o
    "\u0440": ("p", "Cyrillic"),   # Cyrillic р -> Latin p
    "\u0441": ("c", "Cyrillic"),   # Cyrillic с -> Latin c
    "\u0443": ("y", "Cyrillic"),   # Cyrillic у -> Latin y
    "\u0445": ("x", "Cyrillic"),   # Cyrillic х -> Latin x
    "\u0410": ("A", "Cyrillic"),   # Cyrillic А -> Latin A
    "\u0412": ("B", "Cyrillic"),   # Cyrillic В -> Latin B
    "\u0415": ("E", "Cyrillic"),   # Cyrillic Е -> Latin E
    "\u041A": ("K", "Cyrillic"),   # Cyrillic К -> Latin K
    "\u041C": ("M", "Cyrillic"),   # Cyrillic М -> Latin M
    "\u041D": ("H", "Cyrillic"),   # Cyrillic Н -> Latin H
    "\u041E": ("O", "Cyrillic"),   # Cyrillic О -> Latin O
    "\u0420": ("P", "Cyrillic"),   # Cyrillic Р -> Latin P
    "\u0421": ("C", "Cyrillic"),   # Cyrillic С -> Latin C
    "\u0422": ("T", "Cyrillic"),   # Cyrillic Т -> Latin T
    "\u0423": ("Y", "Cyrillic"),   # Cyrillic У -> Latin Y (uppercase)
    "\u0425": ("X", "Cyrillic"),   # Cyrillic Х -> Latin X
    "\u0401": ("Ё", "Cyrillic"),   # Cyrillic Ё
    "\u0462": ("Ѣ", "Cyrillic"),   # Cyrillic Yat
    "\u0456": ("i", "Cyrillic"),   # Cyrillic і -> Latin i
    # Greek confusables
    "\u03B1": ("a", "Greek"),      # Greek α -> Latin a (approximate)
    "\u03B9": ("i", "Greek"),      # Greek ι -> Latin i
    "\u03BF": ("o", "Greek"),      # Greek ο -> Latin o
    "\u03C1": ("p", "Greek"),      # Greek ρ -> Latin p
    "\u03C5": ("v", "Greek"),      # Greek υ -> Latin v (approximate)
    "\u03C7": ("x", "Greek"),      # Greek χ -> Latin x
    "\u0391": ("A", "Greek"),      # Greek Α -> Latin A
    "\u0392": ("B", "Greek"),      # Greek Β -> Latin B
    "\u0395": ("E", "Greek"),      # Greek Ε -> Latin E
    "\u0396": ("Z", "Greek"),      # Greek Ζ -> Latin Z
    "\u0397": ("H", "Greek"),      # Greek Η -> Latin H
    "\u0399": ("I", "Greek"),      # Greek Ι -> Latin I
    "\u039A": ("K", "Greek"),      # Greek Κ -> Latin K
    "\u039C": ("M", "Greek"),      # Greek Μ -> Latin M
    "\u039D": ("N", "Greek"),      # Greek Ν -> Latin N
    "\u039F": ("O", "Greek"),      # Greek Ο -> Latin O
    "\u03A1": ("P", "Greek"),      # Greek Ρ -> Latin P
    "\u03A4": ("T", "Greek"),      # Greek Τ -> Latin T
    "\u03A5": ("Y", "Greek"),      # Greek Υ -> Latin Y
    "\u03A7": ("X", "Greek"),      # Greek Χ -> Latin X
    # Lookalike digits
    "\u0417": ("3", "Cyrillic"),   # Cyrillic З -> digit 3
    "\u0474": ("V", "Cyrillic"),   # Cyrillic Ѵ -> Latin V
    "\u0269": ("i", "Latin-Ext"),  # Latin small letter iota -> i
    "\u029F": ("l", "Latin-Ext"),  # Latin small letter l with mid-height hook -> l
    "\u0501": ("d", "Cyrillic"),   # Cyrillic dje -> d (approximate)
    # Full-width variants
    "\uFF41": ("a", "Fullwidth"),  # Fullwidth a
    "\uFF21": ("A", "Fullwidth"),  # Fullwidth A
    "\uFF4F": ("o", "Fullwidth"),  # Fullwidth o
    "\uFF2F": ("O", "Fullwidth"),  # Fullwidth O
    "\uFF49": ("i", "Fullwidth"),  # Fullwidth i
    "\uFF29": ("I", "Fullwidth"),  # Fullwidth I
    "\uFF4C": ("l", "Fullwidth"),  # Fullwidth l
    "\uFF2C": ("L", "Fullwidth"),  # Fullwidth L
    "\uFF50": ("p", "Fullwidth"),  # Fullwidth p
    "\uFF30": ("P", "Fullwidth"),  # Fullwidth P
    "\uFF43": ("c", "Fullwidth"),  # Fullwidth c
    "\uFF23": ("C", "Fullwidth"),  # Fullwidth C
    # Additional lookalikes
    "\u0131": ("i", "Latin-Ext"),  # dotless i
    "\u026A": ("I", "Latin-Ext"),  # small capital I
    "\u0272": ("n", "Latin-Ext"),  # small n with left hook
    "\u01C0": ("l", "Latin-Ext"),  # dental click -> l lookalike
    "\u00D0": ("D", "Latin-Ext"),  # Eth -> D lookalike
    "\u00D8": ("O", "Latin-Ext"),  # O with stroke
    "\u00F0": ("d", "Latin-Ext"),  # small eth -> d lookalike
    "\u0126": ("H", "Latin-Ext"),  # H with stroke
    "\u0127": ("h", "Latin-Ext"),  # h with stroke
    "\u0141": ("L", "Latin-Ext"),  # L with stroke
    "\u0142": ("l", "Latin-Ext"),  # l with stroke
    "\u0166": ("T", "Latin-Ext"),  # T with stroke
    "\u01A0": ("O", "Latin-Ext"),  # O with horn
}

# Clean up any placeholder entries
HOMOGLYPH_MAP = {k: v for k, v in HOMOGLYPH_MAP.items() if len(k) == 1}

# Build reverse lookup: for a given identifier, extract the "canonical" Latin form
def _get_script(char: str) -> str:
    """Get the Unicode script name for a character."""
    try:
        name = unicodedata.name(char, "")
        if name.startswith("CYRILLIC"):
            return "Cyrillic"
        elif name.startswith("GREEK"):
            return "Greek"
        elif name.startswith("LATIN") or name.startswith("DIGIT"):
            return "Latin"
        elif name.startswith("FULLWIDTH"):
            return "Fullwidth"
        else:
            return "Other"
    except ValueError:
        return "Unknown"


class HomoglyphScanner:
    """Scans for homoglyph substitutions in identifiers and strings."""

    name = "homoglyph"
    rule_id = "STEN002"

    def scan_line(self, file_path: str, line_num: int, line: str) -> list:
        """Scan a line for homoglyph characters."""
        findings = []
        seen_positions = set()

        for col, ch in enumerate(line):
            if col in seen_positions:
                continue
            if ch in HOMOGLYPH_MAP:
                latin_equiv, script = HOMOGLYPH_MAP[ch]
                ctx = classify_context(line, col)
                severity = SEVERITY_MAP.get(ctx, Severity.INFO)

                # Escalate identifier context
                if ctx == Context.IDENTIFIER:
                    severity = Severity.CRITICAL

                context_text = self._extract_context(line, col)

                findings.append(Finding(
                    scanner=self.name,
                    file=file_path,
                    line=line_num,
                    column=col + 1,
                    severity=severity,
                    context=ctx,
                    message=(
                        f"Homoglyph detected: '{ch}' (U+{ord(ch):04X}, {script}) "
                        f"looks like '{latin_equiv}' (U+{ord(latin_equiv):04X}, Latin)"
                    ),
                    char_code=f"U+{ord(ch):04X}",
                    character=ch,
                    context_text=context_text,
                    rule_id=self.rule_id,
                ))
                seen_positions.add(col)

        # Check for mixed-script identifiers
        findings.extend(self._check_mixed_script_identifiers(file_path, line_num, line))
        return findings

    def _check_mixed_script_identifiers(self, file_path: str, line_num: int, line: str) -> list:
        """Check for identifiers that mix scripts (e.g., part Latin, part Cyrillic)."""
        import re
        findings = []
        identifier_pat = re.compile(r"[a-zA-Z_\u0080-\uffff][a-zA-Z0-9_\u0080-\uffff]*")

        for m in identifier_pat.finditer(line):
            ident = m.group()
            scripts = set()
            for ch in ident:
                s = _get_script(ch)
                if s not in ("Latin", "Other", "Unknown", "Fullwidth"):
                    scripts.add(s)

            if len(scripts) > 0:
                # Has non-Latin scripts — already caught by individual char check
                # But check for mixed scripts within same identifier
                char_scripts = [_get_script(ch) for ch in ident]
                unique_scripts = set(char_scripts) - {"Other", "Unknown"}
                if len(unique_scripts) > 1:
                    # Mixed scripts in one identifier — extremely suspicious
                    findings.append(Finding(
                        scanner=self.name,
                        file=file_path,
                        line=line_num,
                        column=m.start() + 1,
                        severity=Severity.CRITICAL,
                        context=Context.IDENTIFIER,
                        message=(
                            f"Mixed-script identifier '{ident}': "
                            f"scripts={', '.join(sorted(unique_scripts))}"
                        ),
                        char_code=None,
                        character=ident,
                        context_text=ident,
                        rule_id="STEN002b",
                    ))
        return findings

    def _extract_context(self, line: str, col: int, window: int = 20) -> str:
        start = max(0, col - window)
        end = min(len(line), col + window + 1)
        return line[start:end]
