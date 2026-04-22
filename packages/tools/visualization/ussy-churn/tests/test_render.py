from __future__ import annotations

import networkx as nx

from ussy_churn.communities import ModuleSummary, TerritorySummary
from ussy_churn.layout import LayoutResult, TerritoryRegion
from ussy_churn.render import render_ascii, render_map, render_svg


def test_render_ascii_contains_panel() -> None:
    layout = LayoutResult(
        width=4,
        height=2,
        territories=[
            TerritoryRegion(0, "Core", [(0, 0), (1, 0), (1, 1)], (0.5, 0.5), "Core", "Cor")
        ],
        grid=[[0, 0, 0, 0], [0, 0, 0, 0]],
        conflict_edges=set(),
        edges=[],
    )
    territories = [TerritorySummary(0, "Core", ("core",), 1, 1, 1, 1.0)]
    modules = {"core": ModuleSummary("core", 1, 1, 1, 1.0, "hot")}
    rendered = render_ascii(layout, territories, modules, no_color=True)
    assert "ChurnMap" in rendered


def test_render_svg_writes_file(tmp_path) -> None:
    layout = LayoutResult(
        width=4,
        height=2,
        territories=[
            TerritoryRegion(0, "Core", [(0, 0), (1, 0), (1, 1)], (0.5, 0.5), "Core", "Cor")
        ],
        grid=[[0, 0, 0, 0], [0, 0, 0, 0]],
        conflict_edges=set(),
        edges=[],
    )
    territories = [TerritorySummary(0, "Core", ("core",), 1, 1, 1, 1.0)]
    modules = {"core": ModuleSummary("core", 1, 1, 1, 1.0, "hot")}
    path = render_svg(layout, territories, modules, tmp_path / "map.svg")
    assert path.exists()
