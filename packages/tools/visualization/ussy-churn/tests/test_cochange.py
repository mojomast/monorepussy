from __future__ import annotations

from datetime import datetime

from churnmap.cochange import build_cochange_graph
from churnmap.mining import MinedCommit


def test_build_cochange_graph_counts_pairs() -> None:
    commits = [
        MinedCommit("a", datetime.now(), ("core", "ui"), ("a.py", "b.py"), "alice"),
        MinedCommit("b", datetime.now(), ("core", "ui"), ("a.py", "b.py"), "alice"),
        MinedCommit("c", datetime.now(), ("core",), ("a.py",), "bob"),
    ]
    graph = build_cochange_graph(commits, min_cochanges=2)
    assert graph.has_edge("core", "ui")
    assert graph["core"]["ui"]["cochanges"] == 2
