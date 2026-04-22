"""Ussyverse core utilities: config discovery, logging, paths, versions."""

__version__ = "0.1.0"

from ussy_core.core import (
    find_config_file,
    get_logger,
    get_project_root,
    safe_path,
    version_tuple,
)

__all__ = [
    "__version__",
    "find_config_file",
    "get_logger",
    "get_project_root",
    "safe_path",
    "version_tuple",
]
