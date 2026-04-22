"""Enhancer Scanner — discovers cross-reference connections between modules."""

from __future__ import annotations

import math
from typing import Any

from ussy_operon.models import Codebase, Enhancer, Gene, Operon


class EnhancerScanner:
    """Identifies documentation enhancers: distant connections that boost understanding."""

    def __init__(self, max_depth: int = 4, min_distance: int = 2) -> None:
        self.max_depth = max_depth
        self.min_distance = min_distance

    def _build_import_graph(self, genes: list[Gene]) -> dict[str, set[str]]:
        """Build an import graph from genes."""
        graph: dict[str, set[str]] = {g.path: set() for g in genes}
        path_map = {g.path: g for g in genes}

        for g in genes:
            for other in genes:
                if g.path == other.path:
                    continue
                other_module = other.path.replace("/", ".").replace("\\", ".").replace(".py", "")
                for imp in g.imports:
                    if imp.startswith(other_module) or other_module.endswith(imp.split(".")[-1]):
                        graph[g.path].add(other.path)
                        break
        return graph

    def _transitive_relationships(
        self, gene: Gene, graph: dict[str, set[str]], genes: list[Gene]
    ) -> list[tuple[str, int]]:
        """Find transitive relationships up to max_depth."""
        visited: dict[str, int] = {gene.path: 0}
        queue = [gene.path]
        relationships: list[tuple[str, int]] = []

        while queue:
            current = queue.pop(0)
            current_depth = visited[current]
            if current_depth >= self.max_depth:
                continue
            for neighbor in graph.get(current, set()):
                if neighbor not in visited:
                    visited[neighbor] = current_depth + 1
                    queue.append(neighbor)
                    if current_depth + 1 >= self.min_distance:
                        relationships.append((neighbor, current_depth + 1))

        return relationships

    def _calculate_semantic_similarity(self, g1: Gene, g2: Gene) -> float:
        """Calculate semantic similarity between two genes based on exports and docstrings."""
        # Jaccard similarity on exports
        if g1.exports and g2.exports:
            shared_exports = set(g1.exports) & set(g2.exports)
            union_exports = set(g1.exports) | set(g2.exports)
            export_sim = len(shared_exports) / len(union_exports) if union_exports else 0.0
        else:
            export_sim = 0.0

        # Simple text similarity on docstrings
        if g1.docstring and g2.docstring:
            words1 = set(g1.docstring.lower().split())
            words2 = set(g2.docstring.lower().split())
            shared_words = words1 & words2
            union_words = words1 | words2
            doc_sim = len(shared_words) / len(union_words) if union_words else 0.0
        else:
            doc_sim = 0.0

        # Name similarity
        name1 = g1.name.lower()
        name2 = g2.name.lower()
        common_prefix_len = 0
        for a, b in zip(name1, name2):
            if a == b:
                common_prefix_len += 1
            else:
                break
        name_sim = common_prefix_len / max(len(name1), len(name2)) if max(len(name1), len(name2)) > 0 else 0.0

        return 0.4 * export_sim + 0.3 * doc_sim + 0.3 * name_sim

    def _is_similar_flow(self, g1: Gene, g2: Gene) -> bool:
        """Determine if two genes have a similar data flow (forward vs reverse)."""
        # Simple heuristic: if g1 imports g2, it's forward
        g2_module = g2.path.replace("/", ".").replace("\\", ".").replace(".py", "")
        for imp in g1.imports:
            if imp.startswith(g2_module) or g2_module.endswith(imp.split(".")[-1]):
                return True
        return False

    def _find_bridge_concepts(self, g1: Gene, g2: Gene) -> list[str]:
        """Find shared concepts that bridge two genes."""
        shared_imports = set(g1.imports) & set(g2.imports)
        shared_exports = set(g1.exports) & set(g2.exports)
        return sorted(list(shared_imports)[:3] + list(shared_exports)[:3])

    def _find_usage_contexts(self, g1: Gene, g2: Gene) -> list[str]:
        """Find usage contexts for two genes."""
        contexts = []
        if g1.is_public and g2.is_public:
            contexts.append("public_api")
        if g1.is_internal or g2.is_internal:
            contexts.append("internal")
        if g1.is_deprecated or g2.is_deprecated:
            contexts.append("deprecated")
        if "test" in g1.path.lower() or "test" in g2.path.lower():
            contexts.append("testing")
        all_imports = g1.imports + g2.imports
        if any("http" in imp.lower() or "web" in imp.lower() or "server" in imp.lower() for imp in all_imports):
            contexts.append("web")
        return contexts

    def find_enhancers(self, codebase: Codebase) -> list[Enhancer]:
        """Find enhancers for the codebase."""
        genes = codebase.genes
        if not genes:
            return []

        graph = self._build_import_graph(genes)
        path_to_gene = {g.path: g for g in genes}
        operon_map: dict[str, str] = {}
        for operon in codebase.operons:
            for g in operon.genes:
                operon_map[g.path] = operon.operon_id

        enhancers: list[Enhancer] = []

        for gene in genes:
            distant_connections = self._transitive_relationships(gene, graph, genes)

            for connection_path, distance in distant_connections:
                if connection_path not in path_to_gene:
                    continue
                connection = path_to_gene[connection_path]

                strength = self._calculate_semantic_similarity(gene, connection)
                # Enhancers work at distance but strength decays
                if distance >= self.min_distance and strength > 0.5:
                    distance_kb = distance * max(gene.lines_of_code, connection.lines_of_code) / 1000.0
                    enhancer = Enhancer(
                        enhancer_id=f"enh_{gene.name}_{connection.name}",
                        source_gene=gene.path,
                        target_gene=connection.path,
                        target_operon=operon_map.get(connection.path, "unknown"),
                        distance_kb=round(distance_kb, 3),
                        orientation="forward" if self._is_similar_flow(gene, connection) else "reverse",
                        enhancer_strength=round(strength / math.sqrt(distance), 3),
                        transcription_factors_required=self._find_bridge_concepts(gene, connection),
                        tissue_specificity=self._find_usage_contexts(gene, connection),
                    )
                    enhancers.append(enhancer)

        return enhancers

    def get_top_enhancers(self, enhancers: list[Enhancer], n: int = 10) -> list[Enhancer]:
        """Get the top N enhancers by strength."""
        return sorted(enhancers, key=lambda e: e.enhancer_strength, reverse=True)[:n]

    def get_enhancers_for_operon(self, enhancers: list[Enhancer], operon_id: str) -> list[Enhancer]:
        """Get enhancers targeting a specific operon."""
        return [e for e in enhancers if e.target_operon == operon_id]
