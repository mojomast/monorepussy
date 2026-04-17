"""Parse lockfiles to extract dependency information."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class Dependency:
    """A single dependency extracted from a lockfile."""

    def __init__(self, name: str, version: str, source: str = "unknown"):
        self.name = name
        self.version = version
        self.source = source

    def __repr__(self) -> str:
        return f"Dependency({self.name}@{self.version})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Dependency):
            return NotImplemented
        return self.name == other.name and self.version == other.version

    def __hash__(self) -> int:
        return hash((self.name, self.version))


class LockfileParser:
    """Parse various lockfile formats to extract dependencies."""

    def parse(self, path: str) -> List[Dependency]:
        """Auto-detect lockfile format and parse it."""
        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"Lockfile not found: {path}")

        name = file_path.name.lower()

        if name == "package-lock.json":
            return self.parse_npm_lockfile(path)
        elif name == "yarn.lock":
            return self.parse_yarn_lockfile(path)
        elif name == "pipfile.lock":
            return self.parse_pipfile_lock(path)
        elif name == "poetry.lock":
            return self.parse_poetry_lock(path)
        elif name in ("requirements.txt", "requirements-dev.txt"):
            return self.parse_requirements_txt(path)
        else:
            # Try to detect format by content
            return self._detect_and_parse(path)

    def _detect_and_parse(self, path: str) -> List[Dependency]:
        """Detect lockfile format by examining content."""
        with open(path, "r") as f:
            content = f.read(500)

        if content.strip().startswith("{"):
            return self.parse_npm_lockfile(path)
        else:
            return self.parse_requirements_txt(path)

    def parse_npm_lockfile(self, path: str) -> List[Dependency]:
        """Parse package-lock.json format."""
        with open(path, "r") as f:
            data = json.load(f)

        deps = []

        # npm lockfile v2/v3 format
        packages = data.get("packages", {})
        for pkg_path, info in packages.items():
            if not pkg_path:  # Root package
                continue
            # Extract name from path like "node_modules/lodash"
            parts = pkg_path.split("node_modules/")
            if len(parts) > 1:
                name = parts[-1]
                version = info.get("version", "")
                if version:
                    deps.append(Dependency(name, version, "npm"))

        # Fallback: dependencies section (v1 format)
        if not deps:
            dependencies = data.get("dependencies", {})
            for name, info in dependencies.items():
                version = info.get("version", "")
                if version:
                    deps.append(Dependency(name, version, "npm"))

        return deps

    def parse_yarn_lockfile(self, path: str) -> List[Dependency]:
        """Parse yarn.lock format (simplified parser)."""
        deps = []
        with open(path, "r") as f:
            content = f.read()

        # Yarn lockfile is a pseudo-YAML format
        # Simplified regex-based parser
        pattern = r'^"?(@?[^@\s]+)@[^:]+:\n  version "([^"]+)"'
        for match in re.finditer(pattern, content, re.MULTILINE):
            name = match.group(1).strip('"')
            version = match.group(2)
            deps.append(Dependency(name, version, "yarn"))

        return deps

    def parse_requirements_txt(self, path: str) -> List[Dependency]:
        """Parse requirements.txt format."""
        deps = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#") or line.startswith("-"):
                    continue

                # Parse package==version or package>=version
                match = re.match(
                    r"^([A-Za-z0-9_-]+)\s*[=~><!]+\s*([0-9][0-9A-Za-z.*-]*)",
                    line,
                )
                if match:
                    name = match.group(1)
                    version = match.group(2)
                    deps.append(Dependency(name, version, "pip"))

        return deps

    def parse_pipfile_lock(self, path: str) -> List[Dependency]:
        """Parse Pipfile.lock format."""
        with open(path, "r") as f:
            data = json.load(f)

        deps = []
        for section in ("default", "develop"):
            for name, info in data.get(section, {}).items():
                version = ""
                if isinstance(info, dict):
                    version = info.get("version", "").lstrip("==")
                deps.append(Dependency(name, version, "pip"))

        return deps

    def parse_poetry_lock(self, path: str) -> List[Dependency]:
        """Parse poetry.lock format (TOML-like)."""
        deps = []
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore
            except ImportError:
                # Fallback: simple regex parser
                return self._parse_poetry_lock_regex(path)

        with open(path, "rb") as f:
            data = tomllib.load(f)

        for pkg in data.get("package", []):
            name = pkg.get("name", "")
            version = pkg.get("version", "")
            if name and version:
                deps.append(Dependency(name, version, "pip"))

        return deps

    def _parse_poetry_lock_regex(self, path: str) -> List[Dependency]:
        """Fallback regex-based parser for poetry.lock."""
        deps = []
        with open(path, "r") as f:
            content = f.read()

        # Match [[package]] blocks
        pattern = r'\[\[package\]\]\s*\nname\s*=\s*"([^"]+)"\s*\nversion\s*=\s*"([^"]+)"'
        for match in re.finditer(pattern, content):
            deps.append(Dependency(match.group(1), match.group(2), "pip"))

        return deps
