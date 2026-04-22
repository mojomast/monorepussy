"""Scanner — Full GCI assessment for a project's dependencies."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from ussy_cambium.alignment import compute_alignment
from ussy_cambium.bond import compute_bond_strength
from ussy_cambium.callus import compute_callus_dynamics, estimate_adapter_mismatches
from ussy_cambium.compatibility import compute_compatibility, compute_type_similarity
from ussy_cambium.drift import compute_drift_debt
from ussy_cambium.dwarfing import DependencyNode, analyze_dependency_chain, compute_chain_capability
from ussy_cambium.extractor import (
    InterfaceInfo,
    extract_interface,
    extract_interface_from_file,
    extract_interfaces_from_directory,
)
from ussy_cambium.gci import compute_gci
from ussy_cambium.models import (
    AlignmentScore,
    BondStrength,
    CallusDynamics,
    CompatibilityScore,
    DriftDebt,
    GCISnapshot,
)


def scan_project(path: str) -> dict[str, Any]:
    """Full GCI assessment for all dependencies in a project.

    Scans the project directory for Python files, extracts interfaces,
    and computes compatibility metrics between all pairs.
    """
    path = os.path.abspath(path)

    # Handle both files and directories
    if os.path.isfile(path):
        if path.endswith(".py"):
            interfaces = {os.path.basename(path).replace(".py", ""): extract_interface_from_file(path)}
        elif path.endswith("requirements.txt") or path.endswith(".toml") or path.endswith(".cfg"):
            interfaces = {}
        else:
            interfaces = {}
    elif os.path.isdir(path):
        interfaces = extract_interfaces_from_directory(path)
    else:
        interfaces = {}

    # Also try to parse requirements/dependencies
    dependencies = _parse_dependencies(path)

    # Compute pairwise compatibility
    pair_results: list[dict[str, Any]] = []
    names = list(interfaces.keys())

    for i, name_a in enumerate(names):
        for name_b in names[i + 1:]:
            info_a = interfaces[name_a]
            info_b = interfaces[name_b]

            compat = compute_compatibility(info_a, info_b)
            align = compute_alignment(info_a, info_b)

            consumer_methods = info_a.exported_types | info_a.exported_functions
            provider_methods = info_b.exported_types | info_b.exported_functions
            mismatches = estimate_adapter_mismatches(consumer_methods, provider_methods)
            callus = compute_callus_dynamics(
                total_mismatches=max(mismatches, 1),
                initially_resolved=max(mismatches // 3, 1),
                generation_rate=0.3,
                test_pass_rate=0.7,
            )

            drift = compute_drift_debt(
                delta_behavior=0.02,
                delta_contract=0.01,
                delta_environment=0.005,
            )

            bond = compute_bond_strength(
                b_max=0.9,
                k_b=0.25,
                t50=4.0,
            )

            snapshot = compute_gci(compat, align, callus, drift, bond, system_vigor=0.9, time_months=0)

            pair_results.append({
                "consumer": name_a,
                "provider": name_b,
                "gci": round(snapshot.gci, 4),
                "compatibility": round(compat.composite, 4),
                "alignment": round(align.composite, 4),
            })

    # Build dependency tree for dwarfing analysis
    dep_tree = _build_dependency_tree(dependencies)

    return {
        "project_path": path,
        "modules_scanned": len(interfaces),
        "module_names": list(interfaces.keys()),
        "dependencies_found": len(dependencies),
        "dependencies": dependencies,
        "pair_analysis": pair_results,
        "dwarfing_analysis": analyze_dependency_chain(dep_tree) if dependencies else [],
        "chain_capability": compute_chain_capability(dep_tree),
    }


def _parse_dependencies(path: str) -> list[dict[str, str]]:
    """Parse dependencies from requirements.txt, pyproject.toml, or setup.cfg."""
    deps: list[dict[str, str]] = []

    # Try requirements.txt
    req_path = os.path.join(path, "requirements.txt") if os.path.isdir(path) else ""
    if req_path and os.path.exists(req_path):
        with open(req_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    match = re.match(r"^([a-zA-Z0-9_-]+)\s*([><=!~]+\s*[\d.]+)?", line)
                    if match:
                        deps.append({
                            "name": match.group(1),
                            "version_spec": match.group(2) or "",
                        })

    # Try pyproject.toml
    pyproject_path = os.path.join(path, "pyproject.toml") if os.path.isdir(path) else ""
    if pyproject_path and os.path.exists(pyproject_path):
        try:
            with open(pyproject_path) as f:
                content = f.read()
            # Simple regex-based parsing for dependencies
            in_deps = False
            for line in content.split("\n"):
                stripped = line.strip()
                if "dependencies" in stripped and "=" in stripped:
                    in_deps = True
                    continue
                if in_deps:
                    if stripped.startswith("]") or stripped.startswith("["):
                        in_deps = False
                        continue
                    match = re.match(r'^"([a-zA-Z0-9_-]+)([><=!~]+[\d.]+)?"', stripped)
                    if match:
                        deps.append({
                            "name": match.group(1),
                            "version_spec": match.group(2) or "",
                        })
        except Exception:
            pass

    return deps


def _build_dependency_tree(dependencies: list[dict[str, str]]) -> DependencyNode:
    """Build a simple dependency tree for dwarfing analysis."""
    root = DependencyNode(name="project", capability=1.0)
    for dep in dependencies:
        # Assign a heuristic capability based on whether it's a known async-compatible library
        name = dep["name"].lower()
        if any(kw in name for kw in ("async", "aio", "uvicorn", "uvloop")):
            cap = 0.95
        elif any(kw in name for kw in ("sync", "blocking", "legacy")):
            cap = 0.4
        else:
            cap = 0.85
        child = DependencyNode(name=dep["name"], capability=cap)
        root.children.append(child)
    return root


def format_scan_report(results: dict[str, Any]) -> str:
    """Format scan results as a readable report."""
    lines: list[str] = []
    lines.append("Cambium Project Scan Report")
    lines.append("═" * 50)
    lines.append(f"  Path: {results['project_path']}")
    lines.append(f"  Modules scanned: {results['modules_scanned']}")
    lines.append(f"  Dependencies found: {results['dependencies_found']}")
    lines.append("")

    if results["module_names"]:
        lines.append("  Modules:")
        for name in results["module_names"]:
            lines.append(f"    - {name}")
        lines.append("")

    if results["pair_analysis"]:
        lines.append("  Pair Compatibility Analysis:")
        for pair in results["pair_analysis"]:
            lines.append(
                f"    {pair['consumer']} → {pair['provider']}: "
                f"GCI={pair['gci']:.3f}, C={pair['compatibility']:.3f}, A={pair['alignment']:.3f}"
            )
        lines.append("")

    if results["dwarfing_analysis"]:
        lines.append("  Dependency Capability Analysis:")
        for entry in results["dwarfing_analysis"]:
            warning = " ⚠️ DWARFING" if entry["is_dwarfing"] else ""
            lines.append(
                f"    {entry['name']:<25} cap={entry['capability']:.2f}  "
                f"ratio={entry['dwarf_ratio']:.2f}{warning}"
            )

    return "\n".join(lines)
