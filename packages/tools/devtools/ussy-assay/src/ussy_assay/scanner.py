"""File and directory scanner for Python source files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator


def _resolve_paths(path: str | Path) -> list[Path]:
    """Resolve a path (file or directory) into a list of Python file Paths.

    If *path* is a file, return it (if it's a .py file).
    If *path* is a directory, recursively find all .py files inside.
    """
    p = Path(path)
    if p.is_file():
        if p.suffix == ".py":
            return [p]
        return []
    if p.is_dir():
        return sorted(_walk_py_files(p))
    return []


def _walk_py_files(directory: Path) -> Generator[Path, None, None]:
    """Yield all .py files under *directory*, skipping hidden/venv dirs."""
    skip_dirs = {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        "site-packages",
    }
    for root, dirs, files in os.walk(directory):
        # Prune skipped directories in-place
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        for fname in sorted(files):
            if fname.endswith(".py"):
                yield Path(root) / fname


def read_source(file_path: Path) -> str:
    """Read source code from a file, returning empty string on error."""
    try:
        return file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
