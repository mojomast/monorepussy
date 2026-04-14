"""Context analyzer — determines whether a position is in an identifier, string, comment, or whitespace."""

import re
from stenography.models import Context


# Simple patterns for common languages (Python, JS, C-family, etc.)
_COMMENT_PATTERNS = [
    re.compile(r"//[^\n]*"),          # C++/Java/JS single-line
    re.compile(r"#(?![!\[])[^\n]*"),  # Python/Ruby/shell single-line (avoid shebang)
    re.compile(r"--[^\n]*"),          # SQL/Lua/Haskell
]
_MULTILINE_COMMENT = [
    (re.compile(r"/\*"), re.compile(r"\*/")),  # C-style block
    (re.compile(r'"""'), re.compile(r'"""')),   # Python triple-quote
    (re.compile(r"'''"), re.compile(r"'''")),   # Python triple-quote
]
_STRING_PATTERNS = [
    re.compile(r'"(?:[^"\\]|\\.)*"'),
    re.compile(r"'(?:[^'\\]|\\.)*'"),
    re.compile(r"`(?:[^`\\]|\\.)*`"),
]
_IDENTIFIER_PATTERN = re.compile(r"[a-zA-Z_\u0080-\uffff][a-zA-Z0-9_\u0080-\uffff]*")


def classify_context(line: str, column: int) -> Context:
    """Classify what kind of source context a column position falls in.

    Uses a simple heuristic approach:
    1. Check if in a comment region
    2. Check if in a string literal
    3. Check if part of an identifier
    4. Check if whitespace
    5. Default to OTHER
    """
    if column >= len(line):
        return Context.OTHER

    # Check if the position is whitespace
    if line[column].isspace():
        return Context.WHITESPACE

    # Check if we're in a comment — look for comment markers before our position
    text_before = line[:column]
    for pat in _COMMENT_PATTERNS:
        m = pat.search(line)
        if m and m.start() < column:
            return Context.COMMENT

    # Check if we're in a string literal
    in_string = False
    i = 0
    while i < column:
        ch = line[i]
        if ch in ('"', "'", "`"):
            quote = ch
            i += 1
            while i < len(line) and i <= column:
                if line[i] == "\\" and i + 1 < len(line):
                    i += 2
                    continue
                if line[i] == quote:
                    break
                i += 1
            else:
                # Still in string at column
                return Context.STRING_LITERAL
            if i < column:
                in_string = False
            else:
                return Context.STRING_LITERAL
        else:
            i += 1

    # Re-check string context with a simpler approach
    for pat in _STRING_PATTERNS:
        for m in pat.finditer(line):
            if m.start() <= column < m.end():
                return Context.STRING_LITERAL

    # Check if in a comment
    for pat in _COMMENT_PATTERNS:
        for m in pat.finditer(line):
            if m.start() <= column < m.end():
                return Context.COMMENT

    # Check if part of an identifier
    for m in _IDENTIFIER_PATTERN.finditer(line):
        if m.start() <= column < m.end():
            return Context.IDENTIFIER

    return Context.OTHER
