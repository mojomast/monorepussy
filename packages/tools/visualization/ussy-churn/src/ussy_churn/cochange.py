"""Co-change graph construction for ChurnMap."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

import networkx as nx

from .mining import MinedCommit


@dataclass(frozen=True)
class CochangeSummary:
    """Summary of a co-change edge."""

    module_a: str
    module_b: str
    cochanges: int
    jaccard: float


def build_cochange_graph(
    commits: Iterable[MinedCommit],
    min_cochanges: int = 3,
) -> nx.Graph:
    """Build a weighted module co-change graph."""

    graph = nx.Graph()
    module_commits: dict[str, set[str]] = defaultdict(set)
    module_files: dict[str, set[str]] = defaultdict(set)
    module_authors: dict[str, set[str]] = defaultdict(set)
    pair_counts: Counter[tuple[str, str]] = Counter()

    commit_list = list(commits)
    for commit in commit_list:
        modules = sorted(set(commit.modules))
        for module in modules:
            module_commits[module].add(commit.commit_hash)
            module_files[module].update(commit.files)
            module_authors[module].add(commit.author)
        for module_a, module_b in combinations(modules, 2):
            pair_counts[(module_a, module_b)] += 1

    for module, hashes in module_commits.items():
        graph.add_node(
            module,
            commit_count=len(hashes),
            commit_hashes=set(hashes),
            files=set(module_files[module]),
            authors=set(module_authors[module]),
        )

    for (module_a, module_b), cochanges in pair_counts.items():
        if cochanges < min_cochanges:
            continue
        left = module_commits[module_a]
        right = module_commits[module_b]
        union = left | right
        jaccard = len(left & right) / len(union) if union else 0.0
        graph.add_edge(
            module_a,
            module_b,
            cochanges=cochanges,
            weight=jaccard,
            jaccard=jaccard,
        )

    return graph


def summarize_cochanges(graph: nx.Graph) -> list[CochangeSummary]:
    """Return a sorted summary of graph edges."""

    summaries = [
        CochangeSummary(a, b, data.get("cochanges", 0), data.get("jaccard", 0.0))
        for a, b, data in graph.edges(data=True)
    ]
    return sorted(
        summaries, key=lambda item: (-item.cochanges, item.module_a, item.module_b)
    )
