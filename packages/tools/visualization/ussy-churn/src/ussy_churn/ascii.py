"""ASCII rendering for ussy-churn."""

from __future__ import annotations

import io
import math
from typing import Any

from rich.console import Console
from rich.text import Text

from .colors import module_color
from .communities import ModuleSummary, TerritorySummary
from .layout import LayoutResult


def _heat_symbol(heat: float) -> tuple[str, str]:
    if heat > 0.75:
        return "🔴", "red"
    if heat > 0.5:
        return "🟠", "dark_orange"
    if heat > 0.25:
        return "🟡", "yellow"
    if heat > 0.05:
        return "🔵", "blue"
    return "⚪", "grey70"


def _legend_lines() -> list[str]:
    return [
        "Legend: 🔴 hot  🟠 warm  🟡 active  🔵 stable  ⚪ dead",
        "Borders: ⚔ conflict  ⚡ strong  · weak",
    ]


def _build_grid(
    layout: LayoutResult,
    territories: list[TerritorySummary],
    modules: dict[str, ModuleSummary],
    show_alliances: bool,
    show_borders: bool,
) -> list[str]:
    territory_by_id = {t.territory_id: t for t in territories}
    if not territories:
        return ["No territories found"]

    cols = max(1, math.ceil(math.sqrt(len(territories))))
    rows = math.ceil(len(territories) / cols)
    box_width = 22
    lines: list[str] = []

    def cell_line(text: str = "", fill: str = " ") -> str:
        return text.ljust(box_width - 2, fill)

    for row in range(rows):
        chunk = territories[row * cols : (row + 1) * cols]
        top = "".join(f"┌{cell_line('')}┐  " for _ in chunk).rstrip()
        body1 = []
        body2 = []
        body3 = []
        body4 = []
        bottom = []
        for territory in chunk:
            icon, _ = _heat_symbol(territory.frequency)
            alliance = ""
            if show_alliances:
                alliance = f"T{territory.territory_id}"
            border_bits = []
            if show_borders and layout.conflict_edges:
                related = [
                    edge
                    for edge in layout.conflict_edges
                    if any(mod in territory.modules for mod in edge)
                ]
                if related:
                    border_bits.append("⚔")
                elif layout.edges:
                    strong = [
                        e
                        for e in layout.edges
                        if e.jaccard >= 0.3
                        and any(mod in territory.modules for mod in (e.module_a, e.module_b))
                    ]
                    if strong:
                        border_bits.append("⚡")
                    else:
                        border_bits.append("·")
            body1.append(f"│ {icon} {cell_line(territory.name)} │  ")
            body2.append(f"│ {cell_line(f'({territory.commit_count} commits)')} │  ")
            body3.append(f"│ {cell_line((alliance + ' ' + ' '.join(border_bits)).strip())} │  ")
            body4.append(f"│ {cell_line('freq ' + f'{territory.frequency:.2f}')} │  ")
            bottom.append(f"└{cell_line('')}┘  ")
        lines.extend(
            [
                top.rstrip(),
                "".join(body1).rstrip(),
                "".join(body2).rstrip(),
                "".join(body3).rstrip(),
                "".join(body4).rstrip(),
                "".join(bottom).rstrip(),
            ]
        )
    return lines


def render_territory_ascii(
    layout: LayoutResult,
    territories: list[TerritorySummary],
    modules: dict[str, ModuleSummary],
    show_alliances: bool = False,
    show_borders: bool = False,
) -> str:
    """Render an alternative ASCII territory map (ported from churnmapussy)."""
    buffer = io.StringIO()
    console = Console(width=120, file=buffer, force_terminal=False, color_system=None)
    console.print("UssyChurn")
    for line in _legend_lines():
        console.print(line)

    for line in _build_grid(layout, territories, modules, show_alliances, show_borders):
        console.print(line)

    return buffer.getvalue()
