"""Context analyzer — determines whether a position is in an identifier, string, comment, or whitespace."""

import re
from ussy_steno.models import Context


# Simple patterns for common languages (Python, JS, C-family, etc.)
_COMMENT_PATTERNS = [
    re.compile(r"//[^\n]*"),          # C++/Java/JS single-line
    re.compile(r"#(?![!\[])[^\n]*"),  # Python/Ruby/shell single-line (avoid shebang)
    re.compile(r"--[^\n]*"),          # SQL/Lua/Haskell
]
_MULTILINE_COMMENT_PATTERNS = [
    re.compile(r"/\*.*?\*/", re.DOTALL),   # C-style block
    re.compile(r'""".*?"""', re.DOTALL),   # Python triple-double-quote
    re.compile(r"'''.*?'''", re.DOTALL),   # Python triple-single-quote
]
_STRING_PATTERNS = [
    re.compile(r'"(?:[^"\\]|\\.)*"'),
    re.compile(r"'(?:[^'\\]|\\.)*'"),
    re.compile(r"`(?:[^`\\]|\\.)*`"),
]
_IDENTIFIER_PATTERN = re.compile(r"[a-zA-Z_\u0080-\uffff][a-zA-Z0-9_\u0080-\uffff]*")


def classify_context(line: str, column: int) -> Context:
    """Classify what kind of source context a column position falls in.

    Priority order:
    1. Whitespace
    2. Multiline comment (single-line slice)
    3. Single-line comment
    4. String literal
    5. Identifier
    6. OTHER
    """
    if column >= len(line):
        return Context.OTHER

    # 1. Whitespace
    if line[column].isspace():
        return Context.WHITESPACE

    # 2. Check single-line multiline-comment patterns (e.g. /* foo */ on one line)
    for pat in _MULTILINE_COMMENT_PATTERNS:
        for m in pat.finditer(line):
            if m.start() <= column < m.end():
                return Context.COMMENT

    # 3. Single-line comment markers — position must be within the match span
    for pat in _COMMENT_PATTERNS:
        for m in pat.finditer(line):
            if m.start() <= column < m.end():
                return Context.COMMENT

    # 4. String literal
    for pat in _STRING_PATTERNS:
        for m in pat.finditer(line):
            if m.start() <= column < m.end():
                return Context.STRING_LITERAL

    # 5. Identifier
    for m in _IDENTIFIER_PATTERN.finditer(line):
        if m.start() <= column < m.end():
            return Context.IDENTIFIER

    return Context.OTHER
