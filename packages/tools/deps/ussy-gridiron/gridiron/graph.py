"""Dependency graph construction and analysis utilities."""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from gridiron.models import DependencyEdge, PackageInfo, SystemState


class DependencyGraph:
    """Directed dependency graph with adjacency operations."""

    def __init__(self) -> None:
        self.packages: Dict[str, PackageInfo] = {}
        self.edges: List[DependencyEdge] = []
        # Adjacency: consumer -> set of consumed packages
        self._adj: Dict[str, Set[str]] = {}
        # Reverse adjacency: consumed -> set of consumers
        self._rev_adj: Dict[str, Set[str]] = {}

    def add_package(self, pkg: PackageInfo) -> None:
        self.packages[pkg.name] = pkg
        if pkg.name not in self._adj:
            self._adj[pkg.name] = set()
        if pkg.name not in self._rev_adj:
            self._rev_adj[pkg.name] = set()

    def add_edge(self, edge: DependencyEdge) -> None:
        # Ensure both nodes exist
        if edge.source not in self.packages:
            self.add_package(PackageInfo(name=edge.source))
        if edge.target not in self.packages:
            self.add_package(PackageInfo(name=edge.target))

        self.edges.append(edge)
        self._adj.setdefault(edge.source, set()).add(edge.target)
        self._rev_adj.setdefault(edge.target, set()).add(edge.source)

    def dependents(self, package: str) -> Set[str]:
        """Return all packages that directly depend on `package`."""
        return self._rev_adj.get(package, set())

    def dependencies(self, package: str) -> Set[str]:
        """Return all packages that `package` directly depends on."""
        return self._adj.get(package, set())

    def transitive_dependents(self, package: str) -> Set[str]:
        """Return all packages that transitively depend on `package`."""
        visited: Set[str] = set()
        stack = list(self.dependents(package))
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            stack.extend(self.dependents(node))
        return visited

    def transitive_dependencies(self, package: str) -> Set[str]:
        """Return all packages that `package` transitively depends on."""
        visited: Set[str] = set()
        stack = list(self.dependencies(package))
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            stack.extend(self.dependencies(node))
        return visited

    def remove_package(self, package: str) -> "DependencyGraph":
        """Create a new graph with the given package removed."""
        new_graph = DependencyGraph()
        for name, pkg in self.packages.items():
            if name != package:
                new_graph.add_package(pkg)
        for edge in self.edges:
            if edge.source != package and edge.target != package:
                new_graph.add_edge(edge)
        return new_graph

    def assess_state_without(self, package: str) -> SystemState:
        """Assess system state after removing a package.

        A package is a SPOF if its removal leaves any direct dependent
        with no alternative (no backup path and no remaining dependencies).
        """
        dependents = self.dependents(package)
        if not dependents:
            return SystemState.FUNCTIONAL

        has_failed = False
        has_degraded = False

        for dep_name in dependents:
            dep_pkg = self.packages.get(dep_name)
            remaining_deps = self.dependencies(dep_name) - {package}

            if not remaining_deps:
                # This dependent has no other dependencies
                has_failed = True
            else:
                # Check if any remaining dependency provides similar capability
                if dep_pkg and dep_pkg.backup_packages:
                    has_backup = any(
                        b in self.packages and b != package
                        for b in dep_pkg.backup_packages
                    )
                    if not has_backup:
                        has_degraded = True
                else:
                    has_degraded = True

        if has_failed:
            return SystemState.FAILED
        elif has_degraded:
            return SystemState.DEGRADED
        else:
            return SystemState.FUNCTIONAL

    def adjacency_matrix(self) -> Tuple[List[str], List[List[float]]]:
        """Build adjacency matrix for the graph.

        Returns (node_names, matrix) where matrix[i][j] = coupling
        strength from node i to node j.
        """
        names = sorted(self.packages.keys())
        n = len(names)
        idx = {name: i for i, name in enumerate(names)}
        matrix = [[0.0] * n for _ in range(n)]

        for edge in self.edges:
            if edge.source in idx and edge.target in idx:
                i, j = idx[edge.source], idx[edge.target]
                matrix[i][j] = edge.coupling_strength

        return names, matrix

    def susceptance_matrix(self) -> Tuple[List[str], List[List[float]]]:
        """Build susceptance matrix B for DC power flow analogy.

        B[i][j] = -coupling(i,j) for i != j
        B[i][i] = sum of coupling from i to all j
        """
        names, adj = self.adjacency_matrix()
        n = len(names)
        B = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i != j:
                    B[i][j] = -adj[i][j]
                B[i][i] += adj[i][j]

        return names, B

    def package_count(self) -> int:
        return len(self.packages)

    def edge_count(self) -> int:
        return len(self.edges)

    def direct_packages(self) -> List[str]:
        """Return names of packages marked as direct dependencies."""
        return [name for name, pkg in self.packages.items() if pkg.is_direct]

    def get_coupling(self, source: str, target: str) -> float:
        """Get coupling strength between two packages."""
        for edge in self.edges:
            if edge.source == source and edge.target == target:
                return edge.coupling_strength
        return 0.0
