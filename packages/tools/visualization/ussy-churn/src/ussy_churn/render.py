"""ASCII and SVG rendering for ChurnMap."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .colors import module_color
from .communities import ModuleSummary, TerritorySummary
from .layout import LayoutResult


def _border_char(
    left: int | None,
    right: int | None,
    up: int | None,
    down: int | None,
    up_left: int | None,
    up_right: int | None,
    down_left: int | None,
    down_right: int | None,
    current: str,
) -> str:
    """Choose a border character for a cell."""

    left_diff = left is not None and left != current
    right_diff = right is not None and right != current
    up_diff = up is not None and up != current
    down_diff = down is not None and down != current

    horizontal = left_diff or right_diff
    vertical = up_diff or down_diff
    if horizontal and vertical:
        if up_diff and right_diff and not left_diff and not down_diff:
            return "└"
        if up_diff and left_diff and not right_diff and not down_diff:
            return "┘"
        if down_diff and right_diff and not left_diff and not up_diff:
            return "┌"
        if down_diff and left_diff and not right_diff and not up_diff:
            return "┐"
        if left_diff and right_diff and up_diff and down_diff:
            return "┼"
        if left_diff and right_diff and up_diff:
            return "┴"
        if left_diff and right_diff and down_diff:
            return "┬"
        if up_diff and down_diff and left_diff:
            return "┤"
        if up_diff and down_diff and right_diff:
            return "├"
        return "┼"
    if horizontal:
        return "─"
    if vertical:
        return "│"
    return " "


def _territory_color(
    territory: TerritorySummary, modules: dict[str, ModuleSummary]
) -> str:
    """Choose a territory color from aggregate territory activity."""

    return territory.label or next(
        (modules[name].label for name in territory.modules if name in modules),
        "stable",
    )


def _territory_lookup(
    territories: Iterable[TerritorySummary],
) -> dict[int, TerritorySummary]:
    """Create a lookup table for territory summaries."""

    return {territory.territory_id: territory for territory in territories}


def render_ascii(
    layout: LayoutResult,
    territories: list[TerritorySummary],
    modules: dict[str, ModuleSummary],
    no_color: bool = False,
) -> str:
    """Render the territory map as ANSI-rich terminal text."""

    console = Console(
        color_system=None if no_color else "standard",
        force_terminal=not no_color,
        width=layout.width + 36,
    )
    territory_by_id = _territory_lookup(territories)
    text = Text()
    for y, row in enumerate(layout.grid):
        for x, territory_id in enumerate(row):
            territory = territory_by_id[territory_id]
            scheme = module_color(_territory_color(territory, modules))
            left = row[x - 1] if x > 0 else None
            right = row[x + 1] if x < len(row) - 1 else None
            up = layout.grid[y - 1][x] if y > 0 else None
            down = layout.grid[y + 1][x] if y < len(layout.grid) - 1 else None
            up_left = layout.grid[y - 1][x - 1] if y > 0 and x > 0 else None
            up_right = layout.grid[y - 1][x + 1] if y > 0 and x < len(row) - 1 else None
            down_left = (
                layout.grid[y + 1][x - 1]
                if y < len(layout.grid) - 1 and x > 0
                else None
            )
            down_right = (
                layout.grid[y + 1][x + 1]
                if y < len(layout.grid) - 1 and x < len(row) - 1
                else None
            )
            conflict = False
            for neighbor_id in (left, right, up, down):
                if neighbor_id is None or neighbor_id == territory_id:
                    continue
                neighbor = territory_by_id[neighbor_id]
                if any(
                    frozenset({module_a, module_b}) in layout.conflict_edges
                    for module_a in territory.modules
                    for module_b in neighbor.modules
                ):
                    conflict = True
                    break
            char = (
                "╳"
                if conflict
                else _border_char(
                    left,
                    right,
                    up,
                    down,
                    up_left,
                    up_right,
                    down_left,
                    down_right,
                    territory_id,
                )
            )
            if char == " ":
                char = scheme.char
            text.append(char, style=scheme.ansi if not no_color else None)
        text.append("\n")

    legend = Table.grid(padding=(0, 1))
    legend.add_column()
    legend.add_column()
    for label in ("hot", "warm", "stable", "dead"):
        scheme = module_color(label)
        legend.add_row(
            Text(scheme.char, style=scheme.ansi if not no_color else None),
            f"{label.title()}",
        )

    summary_table = Table.grid(padding=(0, 1))
    summary_table.add_column(justify="right")
    summary_table.add_column()
    summary_table.add_row("Territories", str(len(territories)))
    summary_table.add_row("Modules", str(len(modules)))
    summary_table.add_row("Conflicts", str(len(layout.conflict_edges)))

    with console.capture() as capture:
        console.print(
            Group(
                Panel.fit(text, title="ChurnMap"),
                Panel.fit(legend, title="Legend"),
                Panel.fit(summary_table, title="Summary"),
            )
        )
    return capture.get()


def render_svg(
    layout: LayoutResult,
    territories: list[TerritorySummary],
    modules: dict[str, ModuleSummary],
    output: str | Path,
) -> Path:
    """Render the territory map as SVG."""

    path = Path(output)
    territory_by_id = _territory_lookup(territories)
    width = layout.width * 12
    height = layout.height * 12
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        "<rect width='100%' height='100%' fill='#111'/>",
    ]
    for territory in layout.territories:
        summary = territory_by_id[territory.territory_id]
        scheme = module_color(_territory_color(summary, modules))
        points = " ".join(f"{x * 12:.2f},{y * 12:.2f}" for x, y in territory.polygon)
        parts.append(
            f'<polygon points="{points}" fill="{scheme.svg}" stroke="#1f1f1f" stroke-width="2">'
            f"<title>{summary.name}: {summary.commit_count} commits</title></polygon>"
        )
        cx, cy = territory.centroid
        parts.append(
            f'<text x="{cx * 12:.2f}" y="{cy * 12:.2f}" fill="#eee" font-size="14" text-anchor="middle" dominant-baseline="middle">'
            f"{territory.label}</text>"
        )
    legend_x = 12
    legend_y = 12
    parts.append(f'<g transform="translate({legend_x},{legend_y})">')
    parts.append(
        '<rect x="0" y="0" width="110" height="82" fill="#1a1a1a" stroke="#444"/>'
    )
    for index, label in enumerate(("hot", "warm", "stable", "dead")):
        scheme = module_color(label)
        y = 18 + index * 16
        parts.append(
            f'<rect x="10" y="{y - 10}" width="10" height="10" fill="{scheme.svg}"/>'
        )
        parts.append(
            f'<text x="26" y="{y - 1}" fill="#eee" font-size="12">{label.title()}</text>'
        )
    parts.append("</g>")
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


def render_map(
    layout: LayoutResult,
    territories: list[TerritorySummary],
    modules: dict[str, ModuleSummary],
    format: str = "ascii",
    output: str | Path | None = None,
    no_color: bool = False,
) -> str | Path:
    """Render either ASCII or SVG output."""

    if format == "svg":
        return render_svg(layout, territories, modules, output or "churnmap.svg")
    rendered = render_ascii(layout, territories, modules, no_color=no_color)
    if output is not None:
        Path(output).write_text(rendered, encoding="utf-8")
        return Path(output)
    return rendered
