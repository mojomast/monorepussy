"""Parse requirements.txt dependency manifests."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple

from ussy_gridiron.models import DependencyEdge, PackageInfo


# Match: package_name[extras]==1.2.3 or >=1.0,<2.0 etc.
_REQ_PATTERN = re.compile(
    r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)"  # package name
    r"(\[[^\]]*\])?"  # optional extras
    r"\s*(.*)$"  # version specifiers
)


def parse_requirements_txt(path: str) -> Tuple[Dict[str, PackageInfo], List[DependencyEdge]]:
    """Parse a requirements.txt file into packages and edges.

    Returns (packages_dict, edges_list).
    """
    project_name = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if not project_name or project_name == ".":
        project_name = "root-project"

    packages: Dict[str, PackageInfo] = {}
    edges: List[DependencyEdge] = []

    # Add the project itself
    packages[project_name] = PackageInfo(
        name=project_name,
        version="0.0.0",
        is_direct=False,
    )

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines, comments, and options
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # Skip line continuations and file references
            if line.startswith("-r ") or line.startswith("-e ") or line.startswith("--"):
                continue

            match = _REQ_PATTERN.match(line)
            if match:
                pkg_name = match.group(1).lower().replace("-", "_")
                version_spec = match.group(4).strip() if match.group(4) else "*"

                version_str = _extract_version(version_spec)
                rigidity = _compute_rigidity(version_spec)

                packages[pkg_name] = PackageInfo(
                    name=pkg_name,
                    version=version_str,
                    is_direct=True,
                    version_rigidity=rigidity,
                )
                edges.append(DependencyEdge(
                    source=project_name,
                    target=pkg_name,
                    version_constraint=version_spec,
                ))

    return packages, edges


def _extract_version(spec: str) -> str:
    """Extract a concrete version from pip version specifiers."""
    # Look for == operator first
    eq_match = re.search(r"==\s*([0-9][0-9.]*)", spec)
    if eq_match:
        return eq_match.group(1)

    # Look for >= operator
    ge_match = re.search(r">=\s*([0-9][0-9.]*)", spec)
    if ge_match:
        return ge_match.group(1)

    # Look for any version number
    v_match = re.search(r"([0-9]+\.[0-9]+\.[0-9]+)", spec)
    if v_match:
        return v_match.group(1)

    return "0.0.0"


def _compute_rigidity(spec: str) -> float:
    """Compute version rigidity from pip version specifiers."""
    if not spec or spec == "*":
        return 0.1
    if "==" in spec:
        return 1.0
    if "~=" in spec:
        return 0.6
    if ">=" in spec:
        return 0.2
    if "<" in spec or ">" in spec:
        return 0.3
    return 0.5
