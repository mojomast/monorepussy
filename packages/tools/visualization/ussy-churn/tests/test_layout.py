from __future__ import annotations

import networkx as nx

from churnmap.communities import TerritorySummary
from churnmap.layout import build_layout


def test_build_layout_creates_grid() -> None:
    graph = nx.Graph()
    graph.add_node(
        "core", commit_count=3, commit_hashes={"a"}, files={"a.py"}, authors={"alice"}
    )
    graph.add_node(
        "ui", commit_count=2, commit_hashes={"b"}, files={"b.py"}, authors={"bob"}
    )
    graph.add_edge("core", "ui", cochanges=2, weight=0.5, jaccard=0.5)
    territories = [
        TerritorySummary(0, "Core", ("core",), 1, 1, 1, 0.5),
        TerritorySummary(1, "Ui", ("ui",), 1, 1, 1, 0.5),
    ]
    layout = build_layout(graph, territories, width=12, height=6)
    assert len(layout.grid) == 6
    assert len(layout.grid[0]) == 12
