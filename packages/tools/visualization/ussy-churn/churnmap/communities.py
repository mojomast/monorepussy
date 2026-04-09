"""Community detection and territory summaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import networkx as nx


@dataclass(frozen=True)
class ModuleSummary:
    """Per-module summary metrics."""

    module: str
    commit_count: int
    file_count: int
    author_count: int
    frequency: float
    label: str


@dataclass(frozen=True)
class TerritorySummary:
    """A detected territory and its aggregate stats."""

    territory_id: int
    name: str
    modules: tuple[str, ...]
    commit_count: int
    file_count: int
    author_count: int
    frequency: float
    label: str = ""


def _percentile_thresholds(values: list[float]) -> tuple[float, float, float]:
    """Compute quartile thresholds without numpy."""

    ordered = sorted(values)
    if not ordered:
        return (0.0, 0.0, 0.0)

    def pct(p: float) -> float:
        if len(ordered) == 1:
            return float(ordered[0])
        index = (len(ordered) - 1) * p
        lower = int(index)
        upper = min(lower + 1, len(ordered) - 1)
        weight = index - lower
        return ordered[lower] * (1 - weight) + ordered[upper] * weight

    return pct(0.25), pct(0.5), pct(0.75)


def _classify(value: float, thresholds: tuple[float, float, float]) -> str:
    """Classify a module by activity percentile."""

    q1, q2, q3 = thresholds
    if value <= q1:
        return "dead"
    if value <= q2:
        return "stable"
    if value <= q3:
        return "warm"
    return "hot"


def detect_communities(graph: nx.Graph) -> list[set[str]]:
    """Detect territories using Louvain communities when available."""

    if graph.number_of_nodes() == 0:
        return []

    try:
        from networkx.algorithms.community import louvain_communities

        communities = louvain_communities(graph, seed=42, weight="weight")
    except Exception:
        communities = [set(c) for c in nx.connected_components(graph)]

    if not communities:
        communities = [set(graph.nodes)]
    return [set(group) for group in communities]


def summarize_communities(
    graph: nx.Graph,
    communities: Iterable[set[str]],
) -> tuple[list[TerritorySummary], dict[str, ModuleSummary]]:
    """Create territory and module summaries from the graph."""

    communities_list = [set(group) for group in communities]
    all_commit_counts = [
        int(graph.nodes[node].get("commit_count", 0)) for node in graph.nodes
    ]
    thresholds = _percentile_thresholds(all_commit_counts)
    total_commits = sum(all_commit_counts) or 1

    module_summaries: dict[str, ModuleSummary] = {}
    territory_summaries: list[TerritorySummary] = []

    for territory_id, modules in enumerate(
        sorted(communities_list, key=lambda item: sorted(item))
    ):
        commit_hashes: set[str] = set()
        files: set[str] = set()
        authors: set[str] = set()
        top_module = None
        top_count = -1
        module_names = sorted(modules)

        for module in module_names:
            node = graph.nodes[module]
            module_commit_count = int(node.get("commit_count", 0))
            commit_hashes.update(node.get("commit_hashes", set()))
            files.update(node.get("files", set()))
            authors.update(node.get("authors", set()))
            label = _classify(module_commit_count, thresholds)
            module_summaries[module] = ModuleSummary(
                module=module,
                commit_count=module_commit_count,
                file_count=len(node.get("files", set())),
                author_count=len(node.get("authors", set())),
                frequency=module_commit_count / total_commits,
                label=label,
            )
            if module_commit_count > top_count:
                top_count = module_commit_count
                top_module = module

        territory_name = (
            (top_module or f"territory-{territory_id}").replace("/", " ").title()
        )
        territory_summaries.append(
            TerritorySummary(
                territory_id=territory_id,
                name=territory_name,
                modules=tuple(module_names),
                commit_count=len(commit_hashes),
                file_count=len(files),
                author_count=len(authors),
                frequency=len(commit_hashes) / total_commits,
            )
        )

    territory_thresholds = _percentile_thresholds(
        [summary.frequency for summary in territory_summaries]
    )
    territory_summaries = [
        TerritorySummary(
            territory_id=summary.territory_id,
            name=summary.name,
            modules=summary.modules,
            commit_count=summary.commit_count,
            file_count=summary.file_count,
            author_count=summary.author_count,
            frequency=summary.frequency,
            label=_classify(summary.frequency, territory_thresholds),
        )
        for summary in territory_summaries
    ]

    return territory_summaries, module_summaries
