"""Color helpers for ChurnMap."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ColorScheme:
    """Terminal and SVG colors for a module class."""

    ansi: str
    svg: str
    char: str


HOT = ColorScheme("red", "#e45757", "█")
WARM = ColorScheme("yellow", "#e3c84d", "▓")
STABLE = ColorScheme("blue", "#5f8ff7", "▒")
DEAD = ColorScheme("grey70", "#9aa0a6", "░")
NEUTRAL = ColorScheme("white", "#d0d0d0", "·")


def module_color(label: str) -> ColorScheme:
    """Return the color scheme for a module frequency label."""

    mapping = {
        "hot": HOT,
        "warm": WARM,
        "stable": STABLE,
        "dead": DEAD,
    }
    return mapping.get(label, NEUTRAL)
