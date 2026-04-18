"""Project scanner — extracts project info from directory structure."""
from __future__ import annotations

import json
from pathlib import Path

from portmore.models import ProjectInfo


# ── License file patterns ─────────────────────────────────────────────────────

_LICENSE_FILES = [
    "LICENSE", "LICENSE.md", "LICENSE.txt", "LICENSE.rst",
    "LICENCE", "LICENCE.md", "LICENCE.txt",
    "COPYING", "COPYING.md", "COPYING.txt",
]

_LICENSE_HEADERS = {
    "MIT": ["MIT License", "mit license"],
    "Apache-2.0": ["Apache License", "Version 2.0"],
    "GPL-2.0": ["GNU GENERAL PUBLIC LICENSE", "Version 2"],
    "GPL-3.0": ["GNU GENERAL PUBLIC LICENSE", "Version 3"],
    "LGPL-2.1": ["GNU LESSER GENERAL PUBLIC LICENSE", "Version 2.1"],
    "LGPL-3.0": ["GNU LESSER GENERAL PUBLIC LICENSE", "Version 3"],
    "AGPL-3.0": ["GNU AFFERO GENERAL PUBLIC LICENSE", "Version 3"],
    "BSD-2-Clause": ["BSD 2-Clause", "Redistribution and use"],
    "BSD-3-Clause": ["BSD 3-Clause", "Redistribution and use"],
    "MPL-2.0": ["Mozilla Public License", "Version 2.0"],
    "ISC": ["ISC License", "ISC license"],
    "Unlicense": ["Unlicense", "unlicense"],
    "CC0-1.0": ["CC0", "Creative Commons Zero"],
}


def detect_license_from_text(text: str) -> str | None:
    """Detect license from LICENSE file text content."""
    text_lower = text.lower()
    for spdx_id, patterns in _LICENSE_HEADERS.items():
        if all(p.lower() in text_lower for p in patterns):
            return spdx_id
    return None


def find_license_files(project_path: Path) -> list[Path]:
    """Find license files in project directory."""
    found: list[Path] = []
    for name in _LICENSE_FILES:
        path = project_path / name
        if path.exists():
            found.append(path)
    return found


def read_package_json(project_path: Path) -> dict | None:
    """Read package.json if it exists."""
    pkg_path = project_path / "package.json"
    if pkg_path.exists():
        try:
            return json.loads(pkg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def read_pyproject_toml(project_path: Path) -> dict | None:
    """Read pyproject.toml (basic parsing) if it exists."""
    toml_path = project_path / "pyproject.toml"
    if not toml_path.exists():
        return None
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            return None

    try:
        return tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def scan_project(project_path: str) -> ProjectInfo:
    """Scan a project directory and extract license/dependency information."""
    path = Path(project_path)
    if not path.exists():
        return ProjectInfo(name=path.name, path=str(path))

    # Detect licenses
    licenses: list[str] = []
    for lic_file in find_license_files(path):
        try:
            text = lic_file.read_text(encoding="utf-8")
            detected = detect_license_from_text(text)
            if detected:
                licenses.append(detected)
        except OSError:
            pass

    # Try package.json for license + deps
    dependencies: list[str] = []
    dev_dependencies: list[str] = []

    pkg = read_package_json(path)
    if pkg:
        if "license" in pkg and pkg["license"] not in licenses:
            licenses.append(str(pkg["license"]))
        dependencies.extend(pkg.get("dependencies", {}).keys())
        dev_dependencies.extend(pkg.get("devDependencies", {}).keys())

    # Try pyproject.toml
    pyproject = read_pyproject_toml(path)
    if pyproject:
        project_section = pyproject.get("project", {})
        if "license" in project_section:
            lic_val = project_section["license"]
            if isinstance(lic_val, dict):
                lic_text = lic_val.get("text", "")
            else:
                lic_text = str(lic_val)
            if lic_text and lic_text not in licenses:
                licenses.append(lic_text)

        deps = project_section.get("dependencies", [])
        dependencies.extend(str(d).split(">=")[0].split("==")[0].split("<")[0].strip()
                           for d in deps if isinstance(d, str))
        optional_deps = project_section.get("optional-dependencies", {})
        for group in optional_deps.values():
            dev_dependencies.extend(str(d).split(">=")[0].split("==")[0].strip()
                                   for d in group if isinstance(d, str))

    # Scan for Python source modules
    modules: list[str] = []
    for py_file in path.rglob("*.py"):
        rel = py_file.relative_to(path)
        if ".venv" not in str(rel) and "node_modules" not in str(rel):
            modules.append(str(rel))

    return ProjectInfo(
        name=path.name,
        path=str(path),
        licenses=licenses or ["UNKNOWN"],
        dependencies=dependencies,
        dev_dependencies=dev_dependencies,
        modules=modules,
    )
