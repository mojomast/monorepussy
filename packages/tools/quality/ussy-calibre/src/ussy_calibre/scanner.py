"""Project scanner — discovers source and test files, computes complexity."""

from __future__ import annotations

import os
from typing import Optional

from ussy_calibre.models import (
    FunctionInfo,
    ModuleInfo,
    ProjectScan,
    band_for_complexity,
)
from ussy_calibre.utils import (
    classify_test_function,
    cyclomatic_complexity,
    functions_from_source,
    is_test_file,
)


class ProjectScanner:
    """Scans a Python project to collect structural and complexity data."""

    def __init__(self, root: str) -> None:
        self.root = os.path.abspath(root)

    def scan(self) -> ProjectScan:
        """Perform a full project scan."""
        source_modules: list[ModuleInfo] = []
        test_modules: list[ModuleInfo] = []

        for dirpath, _dirnames, filenames in os.walk(self.root):
            # Skip hidden and common non-source directories
            rel = os.path.relpath(dirpath, self.root)
            parts = rel.split(os.sep)
            if any(p.startswith(".") for p in parts):
                continue
            if any(p in ("__pycache__", "node_modules", ".git", ".tox", ".mypy_cache") for p in parts):
                continue

            for fname in sorted(filenames):
                if not fname.endswith(".py"):
                    continue
                filepath = os.path.join(dirpath, fname)
                is_test = is_test_file(fname)
                module = self._scan_file(filepath, is_test)
                if is_test:
                    test_modules.append(module)
                else:
                    source_modules.append(module)

        return ProjectScan(
            root=self.root,
            source_modules=source_modules,
            test_modules=test_modules,
        )

    def _scan_file(self, filepath: str, is_test: bool) -> ModuleInfo:
        """Scan a single Python file."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
        except OSError:
            return ModuleInfo(filepath=filepath)

        func_infos = functions_from_source(source, filepath)
        functions: list[FunctionInfo] = []
        for fi in func_infos:
            test_type = ""
            if is_test:
                test_type = classify_test_function(fi["name"])
            functions.append(
                FunctionInfo(
                    name=fi["name"],
                    filepath=filepath,
                    lineno=fi["lineno"],
                    cyclomatic_complexity=fi["complexity"],
                    is_test=is_test,
                    test_type=test_type,
                )
            )
        return ModuleInfo(filepath=filepath, functions=functions)


def scan_project(root: str) -> ProjectScan:
    """Convenience function to scan a project."""
    return ProjectScanner(root).scan()
