"""Stemma builder — reconstruct the family tree from shared errors."""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from .alignment import pairwise_distance
from .collation import CollationResult, collate_path
from .models import (
    StemmaNode,
    StemmaTree,
    VariationUnit,
    Witness,
    WitnessRole,
)


def build_variant_matrix(
    collation: CollationResult,
) -> dict[str, list[str]]:
    """Build variant matrix: witness_label -> [reading at each variation unit].

    Only includes positions where there is actual variation.
    """
    matrix: dict[str, list[str]] = {
        w.label: [] for w in collation.witnesses
    }

    for unit in collation.variation_units:
        if not unit.is_variant:
            continue
        for reading in unit.readings:
            for wit_label in reading.witnesses:
                matrix[wit_label].append(reading.text)

    return matrix


def shared_errors(
    collation: CollationResult,
) -> dict[tuple[str, str], int]:
    """Count shared non-majority readings between pairs of witnesses.

    Witnesses sharing many non-majority readings likely descend from
    a common intermediate that introduced those readings.
    """
    witnesses = collation.witnesses
    labels = [w.label for w in witnesses]

    # For each variant position, find which witnesses share minority readings
    minority_groups: list[set[str]] = []

    for unit in collation.variation_units:
        if not unit.is_variant:
            continue
        for reading in unit.minority_readings:
            minority_groups.append(set(reading.witnesses))

    # Count shared errors for each pair
    shared: dict[tuple[str, str], int] = defaultdict(int)

    for group in minority_groups:
        members = sorted(group)
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                pair = (members[i], members[j])
                shared[pair] += 1

    return dict(shared)


def compute_distance_matrix(
    witnesses: list[Witness],
) -> dict[tuple[str, str], float]:
    """Compute pairwise distances between all witnesses."""
    distances: dict[tuple[str, str], float] = {}
    for i, a in enumerate(witnesses):
        for j, b in enumerate(witnesses):
            if i < j:
                d = pairwise_distance(a, b)
                distances[(a.label, b.label)] = d
                distances[(b.label, a.label)] = d
    return distances


def upgma_cluster(
    witnesses: list[Witness],
    distances: dict[tuple[str, str], float],
    shared_errs: dict[tuple[str, str], int],
) -> StemmaTree:
    """Build a stemma tree using UPGMA-like clustering.

    Uses shared errors as primary grouping criterion, with distances
    as tiebreaker.
    """
    if not witnesses:
        return StemmaTree()

    labels = [w.label for w in witnesses]

    # Create leaf nodes
    nodes: dict[str, StemmaNode] = {}
    for w in witnesses:
        node = StemmaNode(
            label=w.label,
            role=WitnessRole.TERMINAL,
            readings={},
        )
        nodes[w.label] = node

    # Track clusters: cluster_id -> set of labels
    clusters: dict[str, set[str]] = {label: {label} for label in labels}
    cluster_heights: dict[str, float] = {label: 0.0 for label in labels}
    hyparchetype_counter = 0

    while len(clusters) > 1:
        # Find the pair with most shared errors, then least distance
        best_pair: Optional[tuple[str, str]] = None
        best_shared = -1
        best_dist = float("inf")

        cluster_ids = list(clusters.keys())
        for i in range(len(cluster_ids)):
            for j in range(i + 1, len(cluster_ids)):
                ci, cj = cluster_ids[i], cluster_ids[j]
                # Compute average shared errors between clusters
                total_shared = 0
                count = 0
                total_dist = 0.0
                for li in clusters[ci]:
                    for lj in clusters[cj]:
                        key = (min(li, lj), max(li, lj))
                        total_shared += shared_errs.get(key, 0)
                        total_dist += distances.get(key, 1.0)
                        count += 1
                avg_shared = total_shared / count if count > 0 else 0
                avg_dist = total_dist / count if count > 0 else 1.0

                if avg_shared > best_shared or (
                    avg_shared == best_shared and avg_dist < best_dist
                ):
                    best_shared = avg_shared
                    best_dist = avg_dist
                    best_pair = (ci, cj)

        if best_pair is None:
            # Fallback: merge by smallest distance
            for i in range(len(cluster_ids)):
                for j in range(i + 1, len(cluster_ids)):
                    ci, cj = cluster_ids[i], cluster_ids[j]
                    total_dist = 0.0
                    count = 0
                    for li in clusters[ci]:
                        for lj in clusters[cj]:
                            total_dist += distances.get((li, lj), 1.0)
                            count += 1
                    avg_dist = total_dist / count if count > 0 else 1.0
                    if avg_dist < best_dist:
                        best_dist = avg_dist
                        best_pair = (ci, cj)

        if best_pair is None:
            break

        ci, cj = best_pair

        # Create hyparchetype node
        hyparchetype_counter += 1
        if len(clusters) == 2:
            # This is the root — archetype
            hlabel = "α"
            role = WitnessRole.ARCHETYPE
        else:
            greek = "αβγδεζηθικλμνξοπρστυφχψω"
            hlabel = greek[hyparchetype_counter - 1] if hyparchetype_counter <= len(greek) else f"H{hyparchetype_counter}"
            role = WitnessRole.HYPERARCHETYPE

        hnode = StemmaNode(label=hlabel, role=role)

        # Add children
        if ci in nodes:
            hnode.add_child(nodes[ci])
        if cj in nodes:
            hnode.add_child(nodes[cj])

        # Merge clusters
        new_cluster = clusters[ci] | clusters[cj]
        new_height = (cluster_heights.get(ci, 0) + cluster_heights.get(cj, 0)) / 2 + avg_dist / 2 if 'avg_dist' in dir() else 0.5

        del clusters[ci]
        del clusters[cj]
        del cluster_heights[ci]
        del cluster_heights[cj]

        clusters[hlabel] = new_cluster
        cluster_heights[hlabel] = new_height
        nodes[hlabel] = hnode

    # Build tree
    root = None
    all_nodes: list[StemmaNode] = []

    for label, node in nodes.items():
        all_nodes.append(node)
        if node.role == WitnessRole.ARCHETYPE:
            root = node

    # If no archetype found, last merged is root
    if root is None and all_nodes:
        root = all_nodes[-1]
        root.role = WitnessRole.ARCHETYPE

    return StemmaTree(root=root, nodes=all_nodes)


def build_stemma(collation: CollationResult) -> StemmaTree:
    """Build a stemma tree from a collation result."""
    if not collation.witnesses:
        return StemmaTree()

    if len(collation.witnesses) == 1:
        node = StemmaNode(
            label=collation.witnesses[0].label,
            role=WitnessRole.ARCHETYPE,
        )
        return StemmaTree(root=node, nodes=[node])

    # Compute distances and shared errors
    distances = compute_distance_matrix(collation.witnesses)
    shared_errs = shared_errors(collation)

    tree = upgma_cluster(collation.witnesses, distances, shared_errs)

    # Populate readings for each node
    _populate_readings(tree, collation)

    return tree


def _populate_readings(tree: StemmaTree, collation: CollationResult) -> None:
    """Populate readings dict for each terminal node in the tree."""
    witness_map = {w.label: w for w in collation.witnesses}

    for node in tree.nodes:
        if node.role == WitnessRole.TERMINAL and node.label in witness_map:
            wit = witness_map[node.label]
            for i, line in enumerate(wit.normalized_lines):
                node.readings[i + 1] = line


def build_stemma_from_path(path) -> StemmaTree:
    """Build stemma from a file/directory path."""
    from pathlib import Path
    p = Path(path)
    collation = collate_path(p)
    return build_stemma(collation)
