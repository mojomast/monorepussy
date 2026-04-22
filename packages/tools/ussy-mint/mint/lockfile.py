"""Lockfile parsing for package dependency analysis.

Supports package-lock.json (npm) format. Parses the lockfile into
a dependency graph suitable for hoard analysis.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class LockedPackage:
    """A package entry from a lockfile."""
    name: str
    version: str
    resolved: str = ""
    integrity: str = ""
    dependencies: dict = field(default_factory=dict)  # name -> version_spec
    dev: bool = False
    optional: bool = False


def parse_package_lock_json(filepath: str | Path) -> list[LockedPackage]:
    """Parse an npm package-lock.json file.

    Supports both lockfileVersion 1 and 2+ formats.

    Args:
        filepath: Path to package-lock.json

    Returns:
        List of LockedPackage objects
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Lockfile not found: {filepath}")

    with open(path, "r") as f:
        data = json.load(f)

    packages: list[LockedPackage] = []

    # Lockfile v2+ uses "packages" key with full paths
    if "packages" in data:
        for pkg_path, pkg_data in data["packages"].items():
            if not pkg_path:  # Root package
                continue
            # Extract name from path like "node_modules/lodash"
            name = pkg_path.split("node_modules/")[-1]
            if not name:
                continue

            packages.append(LockedPackage(
                name=name,
                version=pkg_data.get("version", ""),
                resolved=pkg_data.get("resolved", ""),
                integrity=pkg_data.get("integrity", ""),
                dependencies=pkg_data.get("dependencies", {}),
                dev=pkg_data.get("dev", False),
                optional=pkg_data.get("optional", False),
            ))

    # Lockfile v1 uses "dependencies" key with nested structure
    elif "dependencies" in data:
        _parse_v1_dependencies(data["dependencies"], packages)

    return packages


def _parse_v1_dependencies(
    deps: dict,
    packages: list[LockedPackage],
    prefix: str = "",
) -> None:
    """Recursively parse lockfile v1 dependencies.

    Args:
        deps: Dict of dependency entries
        packages: List to append packages to
        prefix: Prefix for nested package names
    """
    for name, info in deps.items():
        full_name = f"{prefix}{name}" if not prefix else f"{prefix}/{name}"
        # For v1, just use the base name
        pkg_name = name

        packages.append(LockedPackage(
            name=pkg_name,
            version=info.get("version", ""),
            resolved=info.get("resolved", ""),
            integrity=info.get("integrity", ""),
            dependencies=info.get("requires", {}),
            dev=info.get("dev", False),
        ))

        # Recurse into nested dependencies
        if "dependencies" in info:
            _parse_v1_dependencies(info["dependencies"], packages, prefix=pkg_name)


def parse_package_json(filepath: str | Path) -> dict:
    """Parse a package.json file to extract direct dependencies.

    Args:
        filepath: Path to package.json

    Returns:
        Dict with 'dependencies', 'devDependencies', 'name', 'version' keys
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"package.json not found: {filepath}")

    with open(path, "r") as f:
        data = json.load(f)

    return {
        "name": data.get("name", ""),
        "version": data.get("version", ""),
        "dependencies": data.get("dependencies", {}),
        "devDependencies": data.get("devDependencies", {}),
    }


def build_dependency_graph(packages: list[LockedPackage]) -> dict[str, list[str]]:
    """Build a dependency graph from locked packages.

    Args:
        packages: List of LockedPackage objects

    Returns:
        Dict mapping package name to list of dependency names
    """
    graph: dict[str, list[str]] = {}
    pkg_names = {p.name for p in packages}

    for pkg in packages:
        deps = []
        for dep_name in pkg.dependencies:
            # Only include deps that are in the lockfile
            if dep_name in pkg_names:
                deps.append(dep_name)
        graph[pkg.name] = deps

    return graph


def extract_package_names(packages: list[LockedPackage]) -> list[str]:
    """Extract just the package names from a list of locked packages.

    Args:
        packages: List of LockedPackage objects

    Returns:
        Sorted list of package names
    """
    return sorted(p.name for p in packages)


def get_registry_from_resolved(resolved: str) -> str:
    """Extract registry name from a resolved URL.

    Args:
        resolved: The resolved URL from the lockfile

    Returns:
        Registry identifier string
    """
    if not resolved:
        return "unknown"
    if "registry.npmjs.org" in resolved:
        return "npm"
    if "pypi.org" in resolved or "pypi.python.org" in resolved:
        return "pypi"
    if "github.com" in resolved:
        return "github"
    return "private-mirror"
