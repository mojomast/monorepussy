"""Terminal renderer for TimeLoom."""

from __future__ import annotations

from ..color import commit_type_color, darken, hex_to_rgb
from ..weave_engine import WeaveDraft


RESET = "\x1b[0m"


def _ansi(hex_color: str) -> str:
    r, g, b = hex_to_rgb(hex_color)
    return f"\x1b[38;2;{r};{g};{b}m"


def render_terminal(draft: WeaveDraft, commit_types: list[str]) -> str:
    """Render a weave draft as ANSI-colored Unicode blocks."""

    lines: list[str] = []
    blocks = {1: "█", 0: "░"}
    for row_idx, row in enumerate(draft.cells):
        color = _ansi(commit_type_color(commit_types[row_idx]))
        pieces = [color + ("▓" if cell else blocks[cell]) for cell in row]
        lines.append("".join(pieces) + RESET)
    return "\n".join(lines)
