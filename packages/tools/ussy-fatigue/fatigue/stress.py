"""Stress intensity calculation — models the forces acting on each crack.

K = (coupling × churn_rate × complexity) / (test_coverage + 0.1)
"""

from __future__ import annotations

import subprocess
import os
from pathlib import Path
from typing import Optional

from .models import ModuleMetrics, StressIntensity


def compute_stress_intensity(
    metrics: ModuleMetrics,
    prev_K: Optional[float] = None,
) -> StressIntensity:
    """Compute the stress intensity factor K for a module.

    K = (coupling × churn_rate × complexity) / (test_coverage + 0.1)

    Args:
        metrics: Module metrics containing coupling, churn, complexity, coverage.
        prev_K: Previous stress intensity value (for computing delta_K).

    Returns:
        StressIntensity with the computed K and its components.
    """
    coupling = max(metrics.coupling, 0.1)
    churn = max(metrics.churn_rate, 0.1)
    complexity = max(metrics.complexity, 0.1)
    coverage_denom = metrics.test_coverage + 0.1

    K = (coupling * churn * complexity) / coverage_denom

    coupling_comp = coupling
    churn_comp = churn
    complexity_comp = complexity
    coverage_comp = coverage_denom

    delta_K = 0.0
    if prev_K is not None:
        delta_K = K - prev_K

    return StressIntensity(
        file_path=metrics.file_path,
        K=round(K, 2),
        delta_K=round(delta_K, 2),
        coupling_component=round(coupling_comp, 2),
        churn_component=round(churn_comp, 2),
        complexity_component=round(complexity_comp, 2),
        coverage_component=round(coverage_comp, 2),
    )


def compute_coupling(
    file_path: str,
    directory: str,
    import_graph: Optional[dict[str, set[str]]] = None,
) -> float:
    """Compute coupling metric for a module.

    Coupling = fan_in + fan_out, weighted by dependency depth.

    Args:
        file_path: Path to the module file.
        directory: Root directory of the project.
        import_graph: Pre-built import graph (optional).

    Returns:
        Coupling value (float).
    """
    dir_path = Path(directory)
    rel = Path(file_path)
    try:
        rel = rel.relative_to(dir_path)
    except ValueError:
        rel = Path(file_path)

    module_name = str(rel.with_suffix("")).replace(os.sep, ".")

    fan_in = 0
    fan_out = 0

    if import_graph:
        # fan_out: how many modules this one depends on
        fan_out = len(import_graph.get(module_name, set()))

        # fan_in: how many modules depend on this one
        for mod, deps in import_graph.items():
            if module_name in deps:
                fan_in += 1

    # Weight by dependency depth
    depth_weight = 1.0
    if import_graph and module_name in import_graph:
        depth_weight = 1.0 + _compute_depth(module_name, import_graph) * 0.1

    return (fan_in + fan_out) * depth_weight


def _compute_depth(
    module: str,
    import_graph: dict[str, set[str]],
    visited: Optional[set[str]] = None,
) -> int:
    """Compute the maximum dependency depth from a module."""
    if visited is None:
        visited = set()

    if module in visited:
        return 0
    visited.add(module)

    max_depth = 0
    for dep in import_graph.get(module, set()):
        depth = 1 + _compute_depth(dep, import_graph, visited)
        max_depth = max(max_depth, depth)

    return max_depth


def compute_churn_rate(
    file_path: str,
    weeks: int = 12,
) -> float:
    """Compute churn rate (commits per week) for a file using git log.

    Args:
        file_path: Path to the file.
        weeks: Number of weeks to look back.

    Returns:
        Commits per week touching this file.
    """
    try:
        result = subprocess.run(
            [
                "git", "log",
                f"--since={weeks} weeks ago",
                "--format=%H",
                "--", file_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return 0.5  # Default modest churn if git not available

        commits = [line for line in result.stdout.strip().splitlines() if line]
        return len(commits) / max(weeks, 1)

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return 0.5  # Default modest churn


def compute_churn_rate_vicinity(
    file_path: str,
    import_graph: dict[str, set[str]],
    weeks: int = 12,
) -> float:
    """Compute churn rate for a file's vicinity (2-hop dependency graph).

    Counts commits touching the file and files within 2 hops.

    Args:
        file_path: Path to the file.
        import_graph: Import dependency graph.
        weeks: Number of weeks to look back.

    Returns:
        Commits per week in the file's vicinity.
    """
    # Find modules within 2 hops
    dir_path = Path(file_path)
    module_name = str(dir_path.with_suffix("")).replace(os.sep, ".")

    vicinity_files: set[str] = {file_path}
    visited: set[str] = {module_name}

    # 1-hop
    for dep in import_graph.get(module_name, set()):
        visited.add(dep)
        dep_path = dep.replace(".", os.sep) + ".py"
        vicinity_files.add(dep_path)

        # 2-hop
        for dep2 in import_graph.get(dep, set()):
            if dep2 not in visited:
                visited.add(dep2)
                dep2_path = dep2.replace(".", os.sep) + ".py"
                vicinity_files.add(dep2_path)

    # Also find who depends on this module (reverse deps)
    for mod, deps in import_graph.items():
        if module_name in deps:
            visited.add(mod)
            mod_path = mod.replace(".", os.sep) + ".py"
            vicinity_files.add(mod_path)

    # Sum churn across vicinity
    total_churn = 0.0
    for f in vicinity_files:
        total_churn += compute_churn_rate(f, weeks)

    return total_churn


def estimate_test_coverage(file_path: str) -> float:
    """Estimate test coverage ratio for a file by looking for test files.

    This is a heuristic: checks if corresponding test files exist and
    counts test functions vs source functions.

    Args:
        file_path: Path to the source file.

    Returns:
        Estimated test coverage ratio (0-1).
    """
    import ast as ast_module

    # Look for test file
    path = Path(file_path)
    parent = path.parent
    name = path.stem

    test_paths = [
        parent / f"test_{name}.py",
        parent / "tests" / f"test_{name}.py",
        parent.parent / "tests" / f"test_{name}.py",
        parent.parent / "test" / f"test_{name}.py",
    ]

    # Also check for test directories
    for test_dir_name in ("tests", "test"):
        test_dir = parent / test_dir_name
        if test_dir.is_dir():
            test_paths.append(test_dir / f"test_{name}.py")

    source_functions: set[str] = set()
    test_functions: set[str] = set()

    # Parse source file for function names
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast_module.parse(source, filename=file_path)
        for node in ast_module.walk(tree):
            if isinstance(node, (ast_module.FunctionDef, ast_module.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    source_functions.add(node.name)
    except (OSError, SyntaxError):
        pass

    if not source_functions:
        return 0.0

    # Parse test files
    for test_path in test_paths:
        if test_path.exists():
            try:
                with open(test_path, "r", encoding="utf-8", errors="replace") as f:
                    test_source = f.read()
                test_tree = ast_module.parse(test_source, filename=str(test_path))
                for node in ast_module.walk(test_tree):
                    if isinstance(node, (ast_module.FunctionDef, ast_module.AsyncFunctionDef)):
                        test_functions.add(node.name)
                        # Check if test function references a source function
            except (OSError, SyntaxError):
                continue

    # Match test functions to source functions
    covered = 0
    for func_name in source_functions:
        for test_func in test_functions:
            if func_name in test_func:
                covered += 1
                break

    return covered / len(source_functions) if source_functions else 0.0
