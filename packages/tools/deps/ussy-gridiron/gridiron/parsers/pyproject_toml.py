"""Parse pyproject.toml dependency manifests."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple

from gridiron.models import DependencyEdge, PackageInfo


def parse_pyproject_toml(path: str) -> Tuple[Dict[str, PackageInfo], List[DependencyEdge]]:
    """Parse a pyproject.toml file into packages and edges.

    Uses a simple TOML parser (stdlib only, no tomllib for < 3.11 compat).
    Returns (packages_dict, edges_list).
    """
    with open(path, "r") as f:
        content = f.read()

    data = _parse_toml(content)

    project_name = "root-project"
    project_version = "0.0.0"

    # Extract project name and version
    project_section = data.get("project", {})
    if not project_section:
        project_section = data.get("tool", {}).get("poetry", {})
        project_name = project_section.get("name", os.path.basename(
            os.path.dirname(os.path.abspath(path))))
        project_version = project_section.get("version", "0.0.0")
    else:
        project_name = project_section.get("name", os.path.basename(
            os.path.dirname(os.path.abspath(path))))
        project_version = project_section.get("version", "0.0.0")

    packages: Dict[str, PackageInfo] = {}
    edges: List[DependencyEdge] = []

    packages[project_name] = PackageInfo(
        name=project_name,
        version=project_version,
        is_direct=False,
    )

    # PEP 621 dependencies
    deps = project_section.get("dependencies", [])
    _process_deps(deps, project_name, packages, edges, is_dev=False)

    # Optional dependency groups
    optional_deps = project_section.get("optional-dependencies", {})
    for group_name, group_deps in optional_deps.items():
        _process_deps(group_deps, project_name, packages, edges, is_dev=True)

    # Poetry-style dependencies
    poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    if isinstance(poetry_deps, dict):
        for dep_name, dep_spec in poetry_deps.items():
            if dep_name.lower() == "python":
                continue
            version_spec = _poetry_version_spec(dep_spec)
            version_str = _extract_version(version_spec)
            rigidity = _compute_rigidity(version_spec)

            pkg_name = dep_name.lower().replace("-", "_")
            if pkg_name not in packages:
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

    poetry_dev = data.get("tool", {}).get("poetry", {}).get("group", {})
    if isinstance(poetry_dev, dict):
        for group_name, group_data in poetry_dev.items():
            if isinstance(group_data, dict):
                gdeps = group_data.get("dependencies", {})
                if isinstance(gdeps, dict):
                    for dep_name, dep_spec in gdeps.items():
                        if dep_name.lower() == "python":
                            continue
                        version_spec = _poetry_version_spec(dep_spec)
                        version_str = _extract_version(version_spec)
                        rigidity = _compute_rigidity(version_spec)
                        pkg_name = dep_name.lower().replace("-", "_")
                        if pkg_name not in packages:
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
                            is_dev=True,
                        ))

    return packages, edges


def _process_deps(
    deps: list,
    project_name: str,
    packages: Dict[str, PackageInfo],
    edges: List[DependencyEdge],
    is_dev: bool = False,
) -> None:
    """Process a PEP 621 dependency list."""
    for dep in deps:
        if not isinstance(dep, str):
            continue
        # Parse "package>=1.0,<2.0" style
        match = re.match(r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)\s*(.*)", dep)
        if match:
            pkg_name = match.group(1).lower().replace("-", "_")
            version_spec = match.group(3).strip() or "*"
            version_str = _extract_version(version_spec)
            rigidity = _compute_rigidity(version_spec)

            if pkg_name not in packages:
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
                is_dev=is_dev,
            ))


def _poetry_version_spec(dep_spec) -> str:
    """Extract version spec from poetry dependency format."""
    if isinstance(dep_spec, str):
        return dep_spec
    if isinstance(dep_spec, dict):
        return dep_spec.get("version", "*")
    return "*"


def _extract_version(spec: str) -> str:
    """Extract a concrete version from version specifiers."""
    eq_match = re.search(r"==\s*([0-9][0-9.]*)", spec)
    if eq_match:
        return eq_match.group(1)
    ge_match = re.search(r">=\s*([0-9][0-9.]*)", spec)
    if ge_match:
        return ge_match.group(1)
    caret_match = re.search(r"\^\s*([0-9][0-9.]*)", spec)
    if caret_match:
        return caret_match.group(1)
    tilde_match = re.search(r"~\s*([0-9][0-9.]*)", spec)
    if tilde_match:
        return tilde_match.group(1)
    v_match = re.search(r"([0-9]+\.[0-9]+\.[0-9]+)", spec)
    if v_match:
        return v_match.group(1)
    v2_match = re.search(r"([0-9]+\.[0-9]+)", spec)
    if v2_match:
        return v2_match.group(1) + ".0"
    return "0.0.0"


def _compute_rigidity(spec: str) -> float:
    """Compute version rigidity from version specifiers."""
    if not spec or spec == "*":
        return 0.1
    if "==" in spec:
        return 1.0
    if "~=" in spec or spec.startswith("~"):
        return 0.6
    if spec.startswith("^"):
        return 0.4
    if ">=" in spec:
        return 0.2
    if "<" in spec or ">" in spec:
        return 0.3
    return 0.5


# ---------------------------------------------------------------------------
# Minimal TOML parser (no external deps)
# ---------------------------------------------------------------------------

def _parse_toml(content: str) -> dict:
    """Parse TOML content into a dict. Handles the subset we need."""
    result: dict = {}
    current_section = result
    current_path: list = []

    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1

        if not line or line.startswith("#"):
            continue

        # Section header
        sec_match = re.match(r"^\[([^\]]+)\]", line)
        if sec_match:
            path_str = sec_match.group(1)
            current_path = path_str.split(".")
            current_section = result
            for key in current_path:
                key = key.strip().strip('"')
                if key not in current_section:
                    current_section[key] = {}
                current_section = current_section[key]
            continue

        # Key-value pair
        kv_match = re.match(r'^([A-Za-z0-9_-]+)\s*=\s*(.*)', line)
        if kv_match:
            key = kv_match.group(1).strip()
            value_str = kv_match.group(2).strip()

            # Handle multi-line arrays: value starts with [ but doesn't end with ]
            if value_str.startswith("[") and not value_str.rstrip().endswith("]"):
                # Collect lines until closing bracket
                array_lines = [value_str]
                while i < len(lines):
                    next_line = lines[i].strip()
                    array_lines.append(next_line)
                    i += 1
                    if "]" in next_line:
                        break
                value_str = " ".join(array_lines)

            current_section[key] = _parse_toml_value(value_str)

    return result


def _parse_toml_value(value_str: str) -> object:
    """Parse a TOML value string."""
    value_str = value_str.strip()
    # Remove inline comments
    if " #" in value_str:
        value_str = value_str[:value_str.index(" #")].strip()

    if value_str.startswith('"""') or value_str.startswith("'''"):
        return value_str[3:]
    if value_str.startswith('"'):
        return value_str.strip('"')
    if value_str.startswith("'"):
        return value_str.strip("'")

    if value_str.startswith("["):
        return _parse_toml_array(value_str)

    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False

    try:
        if "." in value_str:
            return float(value_str)
        return int(value_str)
    except ValueError:
        return value_str


def _parse_toml_array(value_str: str) -> list:
    """Parse a TOML inline array."""
    # Strip outer brackets
    inner = value_str.strip()
    if inner.startswith("["):
        inner = inner[1:]
    if inner.endswith("]"):
        inner = inner[:-1]

    result = []
    # Simple splitting — doesn't handle nested arrays well, but sufficient for deps
    for item in inner.split(","):
        item = item.strip()
        if not item:
            continue
        if item.startswith('"') and item.endswith('"'):
            result.append(item[1:-1])
        elif item.startswith("'") and item.endswith("'"):
            result.append(item[1:-1])
        else:
            parsed = _parse_toml_value(item)
            result.append(parsed)

    return result
