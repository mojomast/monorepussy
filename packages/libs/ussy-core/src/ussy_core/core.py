"""Core utilities for config discovery, logging, paths, and versions."""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path
from typing import Final

_LOG_FMT: Final[str] = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FMT: Final[str] = "%Y-%m-%d %H:%M:%S"

_CONFIG_CANDIDATES: Final[tuple[str, ...]] = (
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "package.json",
    "Cargo.toml",
)


def find_config_file(
    start: Path | str | None = None, filenames: tuple[str, ...] | None = None
) -> Path | None:
    """Search upward from *start* for the first matching config file.

    Args:
        start: Directory to begin searching (default: current working directory).
        filenames: Tuple of filenames to look for (default: common Python configs).

    Returns:
        Absolute path to the first found file, or ``None`` if not found.
    """
    if start is None:
        start = Path.cwd()
    else:
        start = Path(start).resolve()

    targets = filenames if filenames is not None else _CONFIG_CANDIDATES

    for directory in [start, *start.parents]:
        for name in targets:
            candidate = directory / name
            if candidate.is_file():
                return candidate

    return None


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a logger with a consistent stream handler and formatter.

    Args:
        name: Logger name (typically ``__name__``).
        level: Logging level for the handler.

    Returns:
        Configured :class:`logging.Logger`.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(_LOG_FMT, datefmt=_DATE_FMT))
        logger.addHandler(handler)

    return logger


def get_project_root(
    marker: str | tuple[str, ...] | None = None, start: Path | str | None = None
) -> Path | None:
    """Walk upward from *start* looking for a directory containing *marker*.

    Args:
        marker: Filename(s) that indicate a project root. Defaults to
            ``("pyproject.toml", ".git")``.
        start: Directory to begin searching (default: current working directory).

    Returns:
        Absolute path to the project root, or ``None`` if not found.
    """
    if start is None:
        start = Path.cwd()
    else:
        start = Path(start).resolve()

    if marker is None:
        marker = ("pyproject.toml", ".git")
    elif isinstance(marker, str):
        marker = (marker,)

    for directory in [start, *start.parents]:
        for name in marker:
            if (directory / name).exists():
                return directory

    return None


def safe_path(
    *parts: str | Path, base: Path | str | None = None, must_exist: bool = False
) -> Path:
    """Build an absolute path under *base* and optionally assert existence.

    Args:
        *parts: Path segments to join.
        base: Root directory (default: current working directory).
        must_exist: Raise ``FileNotFoundError`` if the resulting path does not exist.

    Returns:
        Resolved absolute :class:`Path`.

    Raises:
        FileNotFoundError: If *must_exist* is ``True`` and the path is missing.
    """
    if base is None:
        base = Path.cwd()
    else:
        base = Path(base).resolve()

    result = (base / Path(*parts)).resolve()

    # Prevent directory traversal above base for relative inputs
    try:
        result.relative_to(base)
    except ValueError:
        raise ValueError(f"Path {result} escapes base directory {base}") from None

    if must_exist and not result.exists():
        raise FileNotFoundError(result)

    return result


def version_tuple(version: str) -> tuple[int, ...]:
    """Parse a PEP 440-ish version string into a tuple of integers.

    Non-numeric segments (e.g. ``a1``, ``rc2``) are dropped.

    Args:
        version: Version string such as ``"1.2.3"`` or ``"2.0a1"``.

    Returns:
        Tuple of integer components.
    """
    parts = re.split(r"[.-]", version)
    numeric: list[int] = []
    for part in parts:
        # Extract all digit sequences from each part
        for m in re.finditer(r"(\d+)", part):
            numeric.append(int(m.group(1)))
    return tuple(numeric)
