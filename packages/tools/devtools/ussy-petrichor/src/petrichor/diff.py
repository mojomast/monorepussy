"""Diff computation for configuration changes."""

import difflib
from typing import List, Optional


def compute_diff(old_text: str, new_text: str, context_lines: int = 3) -> str:
    """Compute a unified diff between two text strings.

    Args:
        old_text: Previous content.
        new_text: Current content.
        context_lines: Number of context lines around changes.

    Returns:
        Unified diff string.
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile="previous", tofile="current",
        n=context_lines,
    )
    return "".join(diff)


def diff_stats(diff_text: str) -> dict:
    """Parse a unified diff and return statistics.

    Args:
        diff_text: Unified diff string.

    Returns:
        Dict with 'added', 'removed', 'changed_files' counts.
    """
    added = 0
    removed = 0
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    return {"added": added, "removed": removed}


def extract_changed_keys(old_text: str, new_text: str) -> List[str]:
    """Extract the keys/parameters that changed between two config texts.

    Simple heuristic: compare non-matching lines and extract the key
    portion (everything before '=' or ':').

    Args:
        old_text: Previous content.
        new_text: Current content.

    Returns:
        List of changed key strings.
    """
    old_lines = {l.strip() for l in old_text.splitlines() if l.strip() and not l.strip().startswith("#")}
    new_lines = {l.strip() for l in new_text.splitlines() if l.strip() and not l.strip().startswith("#")}

    added = new_lines - old_lines
    removed = old_lines - new_lines
    changed = added | removed

    keys = []
    for line in changed:
        for sep in ("=", ":"):
            if sep in line:
                key = line.split(sep, 1)[0].strip()
                if key and key not in keys:
                    keys.append(key)
                break
    return keys


def lines_changed(old_text: str, new_text: str) -> Optional[int]:
    """Return the number of lines that changed between two texts.

    Args:
        old_text: Previous content.
        new_text: Current content.

    Returns:
        Number of changed lines, or None if both are empty.
    """
    if not old_text and not new_text:
        return None
    matcher = difflib.SequenceMatcher(None, old_text.splitlines(), new_text.splitlines())
    changes = sum(1 for op in matcher.get_opcodes() if op[0] != "equal")
    return changes
