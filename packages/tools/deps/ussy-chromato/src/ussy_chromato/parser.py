"""Dependency graph parser — reads multiple dependency file formats.

Supported: requirements.txt, package.json, Cargo.toml, go.mod, pom.xml, *.gemspec
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ussy_chromato.models import Dependency, DependencyGraph


def parse_dependency_file(path: str) -> DependencyGraph:
    """Parse a dependency file and return a DependencyGraph.

    Supports directories (auto-detects dependency files) and individual files.
    """
    p = Path(path)
    if p.is_dir():
        return _parse_directory(p)
    if not p.exists():
        raise FileNotFoundError(f"Dependency file not found: {path}")
    return _parse_single_file(p)


def _parse_directory(directory: Path) -> DependencyGraph:
    """Auto-detect and parse dependency files in a directory."""
    graph = DependencyGraph()
    candidates = [
        "requirements.txt",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
    ]
    # Also check for gemspec files
    for child in sorted(directory.iterdir()):
        if child.name in candidates or child.suffix == ".gemspec":
            sub_graph = _parse_single_file(child)
            graph.dependencies.extend(sub_graph.dependencies)
            graph.edges.extend(sub_graph.edges)
    return graph


def _parse_single_file(filepath: Path) -> DependencyGraph:
    """Parse a single dependency file based on its extension/name."""
    name = filepath.name.lower()
    if name == "requirements.txt" or name.endswith(".txt"):
        return _parse_requirements_txt(filepath)
    elif name == "package.json":
        return _parse_package_json(filepath)
    elif name == "cargo.toml":
        return _parse_cargo_toml(filepath)
    elif name == "go.mod":
        return _parse_go_mod(filepath)
    elif name == "pom.xml":
        return _parse_pom_xml(filepath)
    elif name.endswith(".gemspec"):
        return _parse_gemspec(filepath)
    else:
        # Try requirements.txt format as fallback
        return _parse_requirements_txt(filepath)


def _parse_requirements_txt(filepath: Path) -> DependencyGraph:
    """Parse a requirements.txt file."""
    deps: list[Dependency] = []
    edges: list[tuple[str, str]] = []
    content = filepath.read_text(encoding="utf-8", errors="replace")

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Handle version specifiers: package>=1.0,<2.0
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*([><=!~].*)?$", line)
        if match:
            pkg_name = match.group(1).strip()
            version_spec = match.group(2) or ""
            # Extract a clean version number if possible
            ver_match = re.search(r"(\d+\.\d+(?:\.\d+)?)", version_spec)
            version = ver_match.group(1) if ver_match else "0.0.0"
            dep = Dependency(name=pkg_name, version=version)
            deps.append(dep)

    return DependencyGraph(dependencies=deps, edges=edges)


def _parse_package_json(filepath: Path) -> DependencyGraph:
    """Parse a package.json file."""
    deps: list[Dependency] = []
    edges: list[tuple[str, str]] = []

    try:
        data = json.loads(filepath.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return DependencyGraph()

    for section_key, is_dev in [("dependencies", False), ("devDependencies", True)]:
        section = data.get(section_key, {})
        for pkg_name, version_spec in section.items():
            ver_match = re.search(r"(\d+\.\d+(?:\.\d+)?)", str(version_spec))
            version = ver_match.group(1) if ver_match else "0.0.0"
            dep = Dependency(name=pkg_name, version=version, is_dev=is_dev)
            deps.append(dep)

    return DependencyGraph(dependencies=deps, edges=edges)


def _parse_cargo_toml(filepath: Path) -> DependencyGraph:
    """Parse a Cargo.toml file (basic TOML parsing without external lib)."""
    deps: list[Dependency] = []
    edges: list[tuple[str, str]] = []
    content = filepath.read_text(encoding="utf-8", errors="replace")

    in_deps = False
    in_dev_deps = False

    for line in content.splitlines():
        stripped = line.strip()

        # Section headers
        if stripped == "[dependencies]":
            in_deps = True
            in_dev_deps = False
            continue
        elif stripped == "[dev-dependencies]":
            in_deps = False
            in_dev_deps = True
            continue
        elif stripped.startswith("["):
            in_deps = False
            in_dev_deps = False
            continue

        if not (in_deps or in_dev_deps):
            continue

        # Parse: name = "version" or name = { version = "1.0", ... }
        match = re.match(r'^([a-zA-Z0-9_-]+)\s*=\s*"([^"]*)"', stripped)
        if match:
            pkg_name = match.group(1)
            version = match.group(2)
            dep = Dependency(
                name=pkg_name,
                version=version,
                is_dev=in_dev_deps,
            )
            deps.append(dep)
            continue

        # Parse table form: name = { version = "1.0" }
        match = re.match(r'^([a-zA-Z0-9_-]+)\s*=\s*\{.*version\s*=\s*"([^"]*)"', stripped)
        if match:
            pkg_name = match.group(1)
            version = match.group(2)
            dep = Dependency(
                name=pkg_name,
                version=version,
                is_dev=in_dev_deps,
            )
            deps.append(dep)

    return DependencyGraph(dependencies=deps, edges=edges)


def _parse_go_mod(filepath: Path) -> DependencyGraph:
    """Parse a go.mod file."""
    deps: list[Dependency] = []
    edges: list[tuple[str, str]] = []
    content = filepath.read_text(encoding="utf-8", errors="replace")

    in_require = False

    for line in content.splitlines():
        stripped = line.strip()

        if stripped.startswith("require ("):
            in_require = True
            continue
        elif stripped == ")":
            in_require = False
            continue

        if in_require or stripped.startswith("require "):
            # Parse: module_path v1.2.3
            if stripped.startswith("require "):
                stripped = stripped[len("require "):]
            parts = stripped.split()
            if len(parts) >= 2:
                mod_path = parts[0]
                version = parts[1]
                # Extract short name from module path
                name = mod_path.split("/")[-1] if "/" in mod_path else mod_path
                dep = Dependency(name=name, version=version)
                deps.append(dep)

    return DependencyGraph(dependencies=deps, edges=edges)


def _parse_pom_xml(filepath: Path) -> DependencyGraph:
    """Parse a pom.xml file (basic XML parsing without external lib)."""
    deps: list[Dependency] = []
    edges: list[tuple[str, str]] = []

    content = filepath.read_text(encoding="utf-8", errors="replace")

    # Extract groupId:artifactId:version blocks
    # Simple regex-based approach for pom.xml
    dep_pattern = re.compile(
        r"<dependency>\s*(.*?)\s*</dependency>",
        re.DOTALL,
    )
    for match in dep_pattern.finditer(content):
        block = match.group(1)
        group_id = _extract_xml_tag(block, "groupId")
        artifact_id = _extract_xml_tag(block, "artifactId")
        version = _extract_xml_tag(block, "version")
        scope = _extract_xml_tag(block, "scope")

        if artifact_id:
            name = f"{group_id}:{artifact_id}" if group_id else artifact_id
            dep = Dependency(
                name=name,
                version=version or "0.0.0",
                is_dev=scope in ("test", "provided"),
            )
            deps.append(dep)

    return DependencyGraph(dependencies=deps, edges=edges)


def _parse_gemspec(filepath: Path) -> DependencyGraph:
    """Parse a .gemspec file (Ruby)."""
    deps: list[Dependency] = []
    edges: list[tuple[str, str]] = []

    content = filepath.read_text(encoding="utf-8", errors="replace")

    # Parse: spec.add_dependency "name", "~> 1.0"
    # Parse: spec.add_development_dependency "name", "~> 1.0"
    dep_pattern = re.compile(
        r'add_(?:development_)?dependency\s+["\']([^"\']+)["\'](?:\s*,\s*["\']([^"\']*)["\'])?'
    )
    for match in dep_pattern.finditer(content):
        name = match.group(1)
        version_spec = match.group(2) or ""
        ver_match = re.search(r"(\d+\.\d+(?:\.\d+)?)", version_spec)
        version = ver_match.group(1) if ver_match else "0.0.0"
        is_dev = "development_dependency" in match.group(0)
        dep = Dependency(name=name, version=version, is_dev=is_dev)
        deps.append(dep)

    return DependencyGraph(dependencies=deps, edges=edges)


def _extract_xml_tag(block: str, tag: str) -> Optional[str]:
    """Extract the content of an XML tag from a block."""
    pattern = re.compile(rf"<{tag}>\s*(.*?)\s*</{tag}>", re.DOTALL)
    match = pattern.search(block)
    if match:
        return match.group(1).strip()
    return None
