from __future__ import annotations

import networkx as nx

from churnmap.communities import detect_communities, summarize_communities


def test_detect_and_summarize_communities() -> None:
    graph = nx.Graph()
    graph.add_node(
        "core",
        commit_count=3,
        commit_hashes={"a", "b"},
        files={"a.py"},
        authors={"alice"},
    )
    graph.add_node(
        "ui", commit_count=1, commit_hashes={"c"}, files={"b.py"}, authors={"bob"}
    )
    graph.add_edge("core", "ui", weight=0.4)
    communities = detect_communities(graph)
    territory_summaries, module_summaries = summarize_communities(graph, communities)
    assert territory_summaries
    assert module_summaries["core"].label in {"hot", "warm", "stable", "dead"}
