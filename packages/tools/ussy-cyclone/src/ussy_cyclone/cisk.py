"""CISK — Conditional Instability of the Second Kind detection.

Detects positive feedback loops in retry/reprocessing chains using the
same framework meteorologists use to predict hurricane intensification.

CISK condition:
1. Convergence triggers small-scale reprocessing (cumulus retry)
2. Reprocessing releases latent heat (error messages trigger retries elsewhere)
3. Latent heat drives more convergence (more messages pile up)
4. Positive feedback → cyclone intensifies

Algorithm:
- Build a directed graph: pipeline_stage → (retry/error triggers) → downstream_stages
- Find strongly connected components (cycles) using Tarjan's algorithm
- For each cycle, compute gain = Π(error_amplification_per_edge)
- Gain > 1 → CISK condition met (self-reinforcing loop)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from ussy_cyclone.models import PipelineTopology


def find_strongly_connected_components(
    nodes: List[str],
    edges: List[Tuple[str, str, float]],
) -> List[List[str]]:
    """Find strongly connected components using Tarjan's algorithm.

    Args:
        nodes: List of node names (pipeline stages).
        edges: List of (source, target, weight) tuples.

    Returns:
        List of SCCs, each a list of node names forming a cycle.
    """
    # Build adjacency list
    adj: Dict[str, List[str]] = {n: [] for n in nodes}
    for src, dst, _ in edges:
        if src in adj and dst in nodes:
            adj[src].append(dst)

    index_counter = [0]
    stack: List[str] = []
    on_stack: Set[str] = set()
    index: Dict[str, int] = {}
    lowlink: Dict[str, int] = {}
    sccs: List[List[str]] = []

    def strongconnect(v: str) -> None:
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)

        for w in adj.get(v, []):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            scc: List[str] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                scc.append(w)
                if w == v:
                    break
            if len(scc) > 1:
                sccs.append(scc)

    for node in nodes:
        if node not in index:
            strongconnect(node)

    return sccs


def compute_cycle_gain(
    cycle: List[str],
    edges: List[Tuple[str, str, float]],
) -> float:
    """Compute the gain of a cycle — product of error amplification along edges.

    Gain > 1 means CISK condition is met: each iteration produces more retries.

    Args:
        cycle: List of stage names forming a cycle.
        edges: All edges in the retry/error graph.

    Returns:
        The product of error amplifications along the cycle edges.
    """
    # Build edge lookup
    edge_map: Dict[Tuple[str, str], float] = {}
    for src, dst, gain in edges:
        edge_map[(src, dst)] = gain

    # Build cycle edges
    total_gain = 1.0
    for i in range(len(cycle)):
        src = cycle[i]
        dst = cycle[(i + 1) % len(cycle)]
        gain = edge_map.get((src, dst), 1.0)
        total_gain *= gain

    return total_gain


def detect_cisk(
    topology: PipelineTopology,
) -> Tuple[List[List[str]], Dict[Tuple[str, ...], float]]:
    """Detect CISK conditions in the pipeline.

    Returns:
        - List of cycles (each a list of stage names)
        - Mapping from cycle tuple to its gain
    """
    if not topology.retry_edges:
        # Try to infer retry edges from pipeline stages
        edges = _infer_retry_edges(topology)
    else:
        edges = topology.retry_edges

    if not edges:
        return [], {}

    nodes = list(topology.stages.keys())
    sccs = find_strongly_connected_components(nodes, edges)

    cycles: List[List[str]] = []
    gains: Dict[Tuple[str, ...], float] = {}

    for scc in sccs:
        gain = compute_cycle_gain(scc, edges)
        cycles.append(scc)
        gains[tuple(scc)] = gain

    return cycles, gains


def _infer_retry_edges(topology: PipelineTopology) -> List[Tuple[str, str, float]]:
    """Infer retry/error edges from pipeline topology when not explicitly provided.

    If a stage has errors, assume some retry back to itself and downstream.
    """
    edges: List[Tuple[str, str, float]] = []

    for name, stage in topology.stages.items():
        if stage.error_rate > 0:
            # Self-retry (common: failed messages retried to same stage)
            amplification = 1.0 + (stage.error_rate / max(stage.forward_rate, 1.0))
            edges.append((name, name, amplification))

        # If reprocessing rate is significant, errors may cascade downstream
        if stage.reprocessing_rate > 0:
            downstream = topology.downstream.get(name, [])
            for ds in downstream:
                if ds in topology.stages:
                    ds_stage = topology.stages[ds]
                    gain = stage.reprocessing_rate / max(ds_stage.forward_rate, 1.0)
                    # Errors flowing back upstream create CISK
                    edges.append((ds, name, max(gain, 1.0)))

    return edges


def is_cisk_active(cycle_gain: float) -> bool:
    """Check if a CISK condition is active (gain > 1)."""
    return cycle_gain > 1.0


def format_cisk(
    cycles: List[List[str]],
    gains: Dict[Tuple[str, ...], float],
) -> str:
    """Format CISK analysis results as a human-readable string."""
    lines: List[str] = []

    lines.append("🔄 CISK Analysis — Positive Feedback Loop Detection")
    lines.append("=" * 55)

    if not cycles:
        lines.append("")
        lines.append("No positive feedback loops detected. Pipeline is stable.")
        return "\n".join(lines)

    for i, cycle in enumerate(cycles, 1):
        cycle_key = tuple(cycle)
        gain = gains.get(cycle_key, 1.0)
        status = "⚠ ACTIVE (gain > 1)" if gain > 1.0 else "  Inactive (gain ≤ 1)"

        lines.append("")
        lines.append(f"  Cycle {i}: {' → '.join(cycle)} → {cycle[0]}")
        lines.append(f"  Gain: {gain:.2f}x  {status}")
        if gain > 1.0:
            lines.append(f"  ⚠ Each loop produces {gain:.2f}x more retries — CISK condition met!")

    lines.append("")
    lines.append("=" * 55)
    return "\n".join(lines)
