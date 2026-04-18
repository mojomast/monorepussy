"""Parse package.json dependency manifests."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from gridiron.models import DependencyEdge, PackageInfo


def parse_package_json(path: str) -> Tuple[Dict[str, PackageInfo], List[DependencyEdge]]:
    """Parse a package.json file into packages and edges.

    Returns (packages_dict, edges_list).
    """
    with open(path, "r") as f:
        data = json.load(f)

    project_name = data.get("name", os.path.basename(os.path.dirname(os.path.abspath(path))))
    project_version = data.get("version", "0.0.0")

    packages: Dict[str, PackageInfo] = {}
    edges: List[DependencyEdge] = []

    # Add the project itself
    packages[project_name] = PackageInfo(
        name=project_name,
        version=project_version,
        is_direct=False,
    )

    dep_sections = [
        ("dependencies", False),
        ("devDependencies", True),
        ("peerDependencies", False),
        ("optionalDependencies", False),
    ]

    for section, is_dev in dep_sections:
        deps = data.get(section, {})
        for dep_name, version_range in deps.items():
            version_str = _extract_version(str(version_range))
            rigidity = _compute_rigidity(str(version_range))

            if dep_name not in packages:
                packages[dep_name] = PackageInfo(
                    name=dep_name,
                    version=version_str,
                    is_direct=True,
                    version_rigidity=rigidity,
                )

            edges.append(DependencyEdge(
                source=project_name,
                target=dep_name,
                version_constraint=str(version_range),
                is_dev=is_dev,
            ))

    return packages, edges


def _extract_version(version_range: str) -> str:
    """Extract a concrete version from a semver range string."""
    # Remove common range operators
    v = version_range.strip()
    for prefix in (">=", "<=", ">", "<", "~", "^", "="):
        v = v.lstrip(prefix)
    # Take first version from range (e.g., "1.0.0 - 2.0.0")
    v = v.split(" - ")[0].strip()
    # Handle x-ranges
    parts = v.split(".")
    normalized = []
    for p in parts[:3]:
        if p in ("x", "X", "*"):
            normalized.append("0")
        else:
            normalized.append(p)
    while len(normalized) < 3:
        normalized.append("0")
    return ".".join(normalized)


def _compute_rigidity(version_range: str) -> float:
    """Compute version rigidity from a semver range.

    Pinned (e.g., "1.2.3") = 1.0 (most rigid)
    Caret (^1.2.3) = 0.4
    Tilde (~1.2.3) = 0.6
    Wide range (>=1.0.0) = 0.2
    Any (*) = 0.1
    """
    v = version_range.strip()
    if v == "*" or v == "latest":
        return 0.1
    if v.startswith(">="):
        return 0.2
    if v.startswith("^"):
        return 0.4
    if v.startswith("~"):
        return 0.6
    if v.startswith("=") or (v[0].isdigit() and " - " not in v and all(
        p.isdigit() for p in v.split(".") if p
    )):
        return 1.0
    return 0.5
