"""TUI renderer — terminal-based geological cross-section viewer.

Provides a simplified text-based rendering of the stratigraphic
cross-section using Unicode block characters and ANSI colors.
"""

from __future__ import annotations

import os
from typing import List, Optional

from ussy_strata.core import (
    GeologicalReport,
    MineralType,
    Stratum,
)


# ANSI color codes for minerals
_MINERAL_COLORS: dict[str, str] = {
    "pyrite": "\033[38;5;220m",      # gold
    "fluorite": "\033[38;5;75m",     # blue
    "topaz": "\033[38;5;214m",       # orange
    "hematite": "\033[38;5;160m",    # red
    "quartz": "\033[38;5;252m",      # light gray
    "graphite": "\033[38;5;240m",    # dark gray
    "obsidian": "\033[38;5;16m",     # near-black
    "granite": "\033[38;5;180m",     # tan
    "garnet": "\033[38;5;124m",      # dark red
    "limestone": "\033[38;5;230m",   # light beige
    "shale": "\033[38;5;59m",        # dark slate
    "calcite": "\033[38;5;158m",     # pale green
    "sandstone": "\033[38;5;173m",   # sandy
    "marble": "\033[38;5;189m",      # off-white
    "pumice": "\033[38;5;145m",      # gray
    "halite": "\033[38;5;123m",      # cyan
    "clay": "\033[38;5;137m",        # brown
}

# Block characters for different thicknesses
_THICKNESS_BLOCKS = "▁▂▃▄▅▆▇█"

# Reset ANSI
_RESET = "\033[0m"


def render_cross_section(
    strata: List[Stratum],
    width: int = 80,
    use_color: bool = True,
) -> str:
    """Render a geological cross-section view of the strata.

    Each stratum is rendered as a horizontal band with color and thickness
    based on its mineral composition and change density.

    Args:
        strata: List of Stratum objects (newest first).
        width: Terminal width for the cross-section.
        use_color: Whether to use ANSI colors.

    Returns:
        String representation of the cross-section.
    """
    if not strata:
        return "(no strata to display)"

    lines: List[str] = []

    # Header
    lines.append("┌" + "─" * (width - 2) + "┐")
    lines.append("│ STRATIGRAPHIC CROSS-SECTION" + " " * (width - 30) + "│")
    lines.append("│ (newest layers at top)" + " " * (width - 26) + "│")
    lines.append("├" + "─" * (width - 2) + "┤")

    for s in strata:
        # Determine dominant mineral for color
        if s.minerals:
            dominant = max(set(s.minerals), key=s.minerals.count)
            mineral_name = dominant.value
        else:
            mineral_name = "clay"

        # Thickness: map to block character
        thickness_idx = min(int(s.thickness), len(_THICKNESS_BLOCKS) - 1)
        block = _THICKNESS_BLOCKS[thickness_idx]

        # Build the stratum line
        color = _MINERAL_COLORS.get(mineral_name, "") if use_color else ""
        reset = _RESET if use_color else ""

        # Show commit info on the left, then fill with mineral pattern
        age_label = _format_stratum_age(s)
        left_info = f" {s.commit_hash[:8]} {age_label:6s} "

        # Fill the rest with the block character
        fill_width = width - len(left_info) - 3
        fill = (block * fill_width)[:fill_width]

        lines.append(f"│{color}{left_info}{fill}{reset}│")

    lines.append("├" + "─" * (width - 2) + "┤")
    lines.append("│ (oldest layers at bottom)" + " " * (width - 28) + "│")
    lines.append("└" + "─" * (width - 2) + "┘")

    return "\n".join(lines)


def render_stratum_detail(stratum: Stratum, use_color: bool = True) -> str:
    """Render a detailed view of a single stratum.

    Shows all geological metadata for a single commit/stratum.

    Args:
        stratum: The Stratum to render.
        use_color: Whether to use ANSI colors.

    Returns:
        Formatted string with stratum details.
    """
    lines: List[str] = []

    color = _MINERAL_COLORS.get(
        stratum.minerals[0].value if stratum.minerals else "clay",
        "",
    ) if use_color else ""
    reset = _RESET if use_color else ""

    lines.append(f"{color}━━━ STRATUM DETAIL ━━━{reset}")
    lines.append(f"  Hash:      {stratum.commit_hash}")
    lines.append(f"  Author:    {stratum.author}")
    lines.append(f"  Date:      {stratum.date.isoformat() if stratum.date else 'unknown'}")
    lines.append(f"  Message:   {stratum.message[:60]}")
    lines.append(f"  Stability: {stratum.stability_tier or 'unclassified'}")
    lines.append(f"  Density:   {stratum.density:.2f}")
    lines.append(f"  Thickness: {stratum.thickness:.2f}")
    lines.append(f"  Lines +/−: {stratum.lines_added}/{stratum.lines_deleted}")
    lines.append(f"  Files:     {len(stratum.files_changed)}")
    lines.append(f"  Is merge:  {stratum.is_merge}")

    if stratum.mineral_composition:
        lines.append(f"  Minerals:  {', '.join(stratum.mineral_composition.keys())}")

    if stratum.files_changed:
        lines.append(f"  Changed:")
        for f in stratum.files_changed[:10]:
            lines.append(f"    • {f}")
        if len(stratum.files_changed) > 10:
            lines.append(f"    ... and {len(stratum.files_changed) - 10} more")

    return "\n".join(lines)


def render_legend(use_color: bool = True) -> str:
    """Render a legend explaining the mineral color mappings."""
    lines: List[str] = []

    lines.append("MINERAL LEGEND")
    lines.append("─" * 30)

    for mineral, color in _MINERAL_COLORS.items():
        if use_color:
            lines.append(f"  {color}███{ _RESET} {mineral}")
        else:
            lines.append(f"  ■■■ {mineral}")

    lines.append("")
    lines.append("THICKNESS SCALE")
    lines.append("─" * 30)
    for i, block in enumerate(_THICKNESS_BLOCKS):
        lines.append(f"  {block} = thickness {i}")

    return "\n".join(lines)


def _format_stratum_age(s: Stratum) -> str:
    """Format the age of a stratum for display."""
    from datetime import datetime, timezone
    if not s.date:
        return "?"

    age = datetime.now(timezone.utc) - s.date
    days = age.total_seconds() / 86400.0

    if days < 1:
        return "today"
    elif days < 30:
        return f"{int(days)}d"
    elif days < 365:
        return f"{int(days/30)}mo"
    else:
        return f"{int(days/365)}y"
