"""Operon Mapper — discovers co-documented feature sets in a codebase."""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any

from ussy_operon.models import Codebase, Gene, Operon


class OperonMapper:
    """Analyzes a codebase and identifies operons (clusters of co-regulated genes/modules)."""

    def __init__(self, coupling_threshold: float = 0.7) -> None:
        self.coupling_threshold = coupling_threshold

    def _is_python_file(self, path: Path) -> bool:
        return path.suffix == ".py" and not path.name.startswith("test_") and path.name != "__init__.py"

    def _parse_gene(self, path: Path, root: Path) -> Gene | None:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            return None

        imports: list[str] = []
        exports: list[str] = []
        docstring = ast.get_docstring(tree) or ""
        is_public = not path.name.startswith("_")
        is_deprecated = "@deprecated" in source or "DEPRECATED" in source
        is_internal = "@internal" in source or "# internal" in source.lower()
        loc = len(source.splitlines())

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    exports.append(node.name)

        rel_path = str(path.relative_to(root))
        return Gene(
            name=path.stem,
            path=rel_path,
            imports=imports,
            exports=exports,
            docstring=docstring,
            is_public=is_public,
            is_deprecated=is_deprecated,
            is_internal=is_internal,
            lines_of_code=loc,
        )

    def _collect_genes(self, codebase: Codebase) -> list[Gene]:
        root = Path(codebase.root_path)
        genes: list[Gene] = []
        if root.is_file() and self._is_python_file(root):
            gene = self._parse_gene(root, root.parent)
            if gene:
                genes.append(gene)
        elif root.is_dir():
            for path in root.rglob("*.py"):
                if self._is_python_file(path):
                    gene = self._parse_gene(path, root)
                    if gene:
                        genes.append(gene)
        return genes

    def _structural_coupling(self, genes: list[Gene]) -> dict[tuple[str, str], float]:
        """Coupling based on shared imports."""
        coupling: dict[tuple[str, str], float] = {}
        for i, g1 in enumerate(genes):
            for j in range(i + 1, len(genes)):
                g2 = genes[j]
                if not g1.imports or not g2.imports:
                    continue
                shared = set(g1.imports) & set(g2.imports)
                union = set(g1.imports) | set(g2.imports)
                if union:
                    score = len(shared) / len(union)
                    coupling[(g1.path, g2.path)] = score
        return coupling

    def _temporal_coupling(self, genes: list[Gene]) -> dict[tuple[str, str], float]:
        """Approximate temporal coupling using file metadata (mtime)."""
        coupling: dict[tuple[str, str], float] = {}
        for i, g1 in enumerate(genes):
            for j in range(i + 1, len(genes)):
                g2 = genes[j]
                # Simple heuristic: similar names or shared prefixes suggest temporal coupling
                name1 = Path(g1.path).stem
                name2 = Path(g2.path).stem
                if name1 == name2:
                    continue
                common_prefix = os.path.commonprefix([name1, name2])
                score = len(common_prefix) / max(len(name1), len(name2)) if max(len(name1), len(name2)) > 0 else 0
                if score > 0.3:
                    coupling[(g1.path, g2.path)] = score
        return coupling

    def _call_coupling(self, genes: list[Gene]) -> dict[tuple[str, str], float]:
        """Coupling based on one module importing from another."""
        coupling: dict[tuple[str, str], float] = {}
        for g1 in genes:
            for g2 in genes:
                if g1.path == g2.path:
                    continue
                # Check if g1 imports from g2
                g2_module = g2.path.replace("/", ".").replace("\\", ".").replace(".py", "")
                for imp in g1.imports:
                    if imp.startswith(g2_module) or g2_module.endswith(imp.split(".")[-1]):
                        coupling[(g1.path, g2.path)] = 1.0
                        break
        return coupling

    def _combine_graphs(
        self,
        structural: dict[tuple[str, str], float],
        temporal: dict[tuple[str, str], float],
        call: dict[tuple[str, str], float],
    ) -> dict[tuple[str, str], float]:
        combined: dict[tuple[str, str], float] = {}
        all_pairs = set(structural.keys()) | set(temporal.keys()) | set(call.keys())
        for pair in all_pairs:
            s = structural.get(pair, 0.0)
            t = temporal.get(pair, 0.0)
            c = call.get(pair, 0.0)
            combined[pair] = 0.4 * s + 0.2 * t + 0.4 * c
        return combined

    def _detect_communities(
        self, genes: list[Gene], graph: dict[tuple[str, str], float]
    ) -> list[list[Gene]]:
        """Simple connected-components-based community detection."""
        # Build adjacency
        adjacency: dict[str, set[str]] = {g.path: set() for g in genes}
        for (a, b), score in graph.items():
            if score >= self.coupling_threshold:
                adjacency[a].add(b)
                adjacency[b].add(a)

        visited: set[str] = set()
        communities: list[list[Gene]] = []
        path_to_gene = {g.path: g for g in genes}

        def dfs(node: str, community: list[str]) -> None:
            visited.add(node)
            community.append(node)
            for neighbor in adjacency[node]:
                if neighbor not in visited:
                    dfs(neighbor, community)

        for path in adjacency:
            if path not in visited:
                community_paths: list[str] = []
                dfs(path, community_paths)
                community_genes = [path_to_gene[p] for p in community_paths if p in path_to_gene]
                if community_genes:
                    communities.append(community_genes)

        # Add singletons as their own operons
        community_paths = {g.path for c in communities for g in c}
        for g in genes:
            if g.path not in community_paths:
                communities.append([g])

        return communities

    def _find_entry_points(self, operon_genes: list[Gene]) -> list[str]:
        """Find genes with the most exports (public API entry points)."""
        if not operon_genes:
            return []
        sorted_genes = sorted(operon_genes, key=lambda g: len(g.exports), reverse=True)
        return [g.path for g in sorted_genes[:2]]

    def _find_control_points(self, operon_genes: list[Gene]) -> list[str]:
        """Find genes that import from many others in the operon."""
        if not operon_genes:
            return []
        paths = {g.path for g in operon_genes}
        control = []
        for g in operon_genes:
            internal_imports = sum(1 for imp in g.imports if any(imp.startswith(p.replace(".py", "").replace("/", ".")) for p in paths))
            if internal_imports >= 1:
                control.append(g.path)
        return control[:2]

    def _find_external_dependencies(self, operon_genes: list[Gene]) -> list[str]:
        """Find external dependencies not within the operon."""
        if not operon_genes:
            return []
        paths = {g.path for g in operon_genes}
        external: set[str] = set()
        for g in operon_genes:
            for imp in g.imports:
                if not any(imp.startswith(p.replace(".py", "").replace("/", ".")) for p in paths):
                    external.add(imp.split(".")[0])
        return sorted(external)

    def map_operons(self, codebase: Codebase) -> list[Operon]:
        """Discover operons in the codebase."""
        genes = self._collect_genes(codebase)
        codebase.genes = genes
        codebase.deprecated_features = [g for g in genes if g.is_deprecated]
        codebase.internal_apis = [g for g in genes if g.is_internal]

        if not genes:
            return []

        structural = self._structural_coupling(genes)
        temporal = self._temporal_coupling(genes)
        call = self._call_coupling(genes)
        combined = self._combine_graphs(structural, temporal, call)

        communities = self._detect_communities(genes, combined)
        operons: list[Operon] = []
        for i, community in enumerate(communities):
            # Calculate average coupling score within community
            scores = []
            for j, g1 in enumerate(community):
                for k in range(j + 1, len(community)):
                    g2 = community[k]
                    scores.append(combined.get((g1.path, g2.path), combined.get((g2.path, g1.path), 0.0)))
            avg_coupling = sum(scores) / len(scores) if scores else 0.0

            operon = Operon(
                operon_id=f"operon_{i}",
                genes=community,
                promoter_region=self._find_entry_points(community),
                operator_sites=self._find_control_points(community),
                regulatory_proteins=self._find_external_dependencies(community),
                coupling_score=round(avg_coupling, 3),
            )
            operons.append(operon)

        codebase.operons = operons
        return operons
